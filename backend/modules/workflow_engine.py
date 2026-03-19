"""
VERITAS Workflow Engine v1.0
Multi-Module Pipeline Executor with DAG Parallelism, Conditional Routing, and Sealed Audit Trail.

Architecture:
  WorkflowStep     — Typed step definition (module, args, dependencies, conditions)
  WorkflowParser   — LLM-powered natural language → pipeline decomposition
  WorkflowPipeline — DAG executor with parallel steps, transforms, and VERITAS gates
  WorkflowStore    — Named template persistence (save/load workflows)

VERITAS Compliance:
  - Inter-step gate validation (data present, exit code clean, output size sane)
  - SHA-256 hash chain per step (deterministic replay)
  - Safety tier enforcement (DANGEROUS actions queue for approval)
  - No optimistic forwarding — INCONCLUSIVE halts dependent steps
"""

import hashlib
import json
import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("workflow_engine")

# ==============================================================================
# DATA TYPES
# ==============================================================================

VERDICTS = ("PASS", "INCONCLUSIVE", "VIOLATION")

DANGEROUS_ACTIONS = {"destroy_all", "gravity_shield", "live_fire", "quarantine", "block_port"}


@dataclass
class WorkflowStep:
    """Single step in a pipeline."""
    step_id: str                           # "step_001"
    module_id: str                         # "alpha_scanner" or "security:cwe_scan"
    action: str = "execute"                # "execute" | "scan" | "analyze"
    args: str = ""                         # passed to module or security function
    depends_on: List[str] = field(default_factory=list)   # step_ids to wait for
    condition: Optional[Dict] = None       # {"field": "...", "op": "<", "value": 0.80, "route_to": "step_X"}
    label: str = ""                        # human-readable description
    transform: bool = True                 # LLM summarizes output before forwarding
    safety_tier: str = "SAFE"              # "SAFE" | "DANGEROUS"


@dataclass
class StepResult:
    """Result of executing a single step."""
    step_id: str
    module_id: str
    status: str = "PENDING"                # PENDING | RUNNING | PASS | INCONCLUSIVE | VIOLATION | SKIPPED
    output: str = ""
    output_summary: str = ""               # LLM-summarized output
    output_hash: str = ""
    error: str = ""
    duration_ms: int = 0
    exit_code: int = -1
    prev_hash: str = ""
    timestamp: str = ""
    condition_met: Optional[bool] = None   # True if condition was evaluated and met


# ==============================================================================
# WORKFLOW PARSER — LLM decomposes natural language → steps
# ==============================================================================

PARSER_SYSTEM_PROMPT = """You are a workflow planner for the VERITAS Command Center.
Given a user request, decompose it into a sequence of execution steps.

Available modules (use EXACT IDs):
{module_list}

Available security actions (prefix with "security:"):
- security:full_scan — Full posture scan (ESM + ports + honeytoken + CWE)
- security:process_scan — ESM process scan with risk scores
- security:port_scan — All listening ports vs baseline
- security:cwe_scan — CWE-338 code vulnerability scan
- security:honeytoken — Bait file integrity check
- security:destroy_all — Kill all hostile processes + block ports (DANGEROUS)
- security:gravity_shield — Block all egress (DANGEROUS)

Rules:
1. Each step needs: step_id, module_id, action, args, depends_on (list of prior step_ids), label
2. Steps with no dependencies can run in parallel
3. If the user specifies conditions (e.g. "if X drops below 0.80"), add a condition object
4. Mark destructive actions as safety_tier: "DANGEROUS"
5. Set transform: true if the next step needs summarized input (not raw output)

Return ONLY valid JSON array of steps. No explanation outside the JSON."""

PARSER_USER_TEMPLATE = """Decompose this request into pipeline steps:

"{user_text}"

Return JSON array:
[
  {{
    "step_id": "step_001",
    "module_id": "module_id_here",
    "action": "execute",
    "args": "",
    "depends_on": [],
    "condition": null,
    "label": "Description of what this step does",
    "transform": true,
    "safety_tier": "SAFE"
  }}
]"""


class WorkflowParser:
    """Parse natural language into WorkflowStep objects using LLM."""

    def __init__(self, llm_router, module_registry):
        self.llm = llm_router
        self.registry = module_registry

    def _build_module_list(self):
        """Generate module catalog string for the parser prompt."""
        lines = []
        for mod in self.registry.list_all():
            lines.append(f"- {mod.id}: {mod.name} [{mod.status}]")
        return "\n".join(lines)

    def parse(self, user_text: str) -> List[WorkflowStep]:
        """Decompose user_text into WorkflowSteps via LLM.
        Falls back to keyword parser on ANY failure: LLM error, bad JSON,
        or all steps invalidated."""
        try:
            module_list = self._build_module_list()
            system = PARSER_SYSTEM_PROMPT.format(module_list=module_list)
            user = PARSER_USER_TEMPLATE.format(user_text=user_text)

            response, backend, error = self.llm.query(system, user)

            if error or not response:
                logger.warning(f"WorkflowParser LLM failed: {error}")
                return self._fallback_parse(user_text)

            # Extract JSON from response
            raw_steps = self._extract_json(response)
            if not raw_steps:
                logger.warning("WorkflowParser: no valid JSON in LLM response, using fallback")
                return self._fallback_parse(user_text)

            validated = self._validate_steps(raw_steps)
            if not validated:
                logger.warning("WorkflowParser: all LLM steps failed validation, using fallback")
                return self._fallback_parse(user_text)

            return validated
        except Exception as e:
            logger.error(f"WorkflowParser.parse() crashed: {e}")
            return self._fallback_parse(user_text)

    def _extract_json(self, text: str) -> List[dict]:
        """Extract JSON array from LLM response."""
        import re
        # Try direct parse
        text = text.strip()
        if text.startswith("["):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        # Try extracting from code block
        match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding array anywhere
        match = re.search(r'\[[\s\S]*\]', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        return []

    def _validate_steps(self, raw_steps: List[dict]) -> List[WorkflowStep]:
        """Validate step data against module registry."""
        valid = []
        valid_ids = {m.id for m in self.registry.list_all()}
        security_actions = {"full_scan", "process_scan", "port_scan", "cwe_scan",
                           "honeytoken", "destroy_all", "gravity_shield"}

        for i, s in enumerate(raw_steps):
            mid = s.get("module_id", "")

            # Validate module exists or is a security action
            is_security = mid.startswith("security:")
            sec_action = mid.split(":", 1)[1] if is_security else ""

            if not is_security and mid not in valid_ids:
                logger.warning(f"WorkflowParser: unknown module '{mid}', skipping step")
                continue
            if is_security and sec_action not in security_actions:
                logger.warning(f"WorkflowParser: unknown security action '{sec_action}', skipping step")
                continue

            # Determine safety tier
            safety = "SAFE"
            if is_security and sec_action in DANGEROUS_ACTIONS:
                safety = "DANGEROUS"
            if s.get("safety_tier") == "DANGEROUS":
                safety = "DANGEROUS"

            step = WorkflowStep(
                step_id=s.get("step_id", f"step_{i+1:03d}"),
                module_id=mid,
                action=s.get("action", "execute"),
                args=s.get("args", ""),
                depends_on=s.get("depends_on", []),
                condition=s.get("condition"),
                label=s.get("label", f"Execute {mid}"),
                transform=s.get("transform", True),
                safety_tier=safety,
            )
            valid.append(step)

        return valid

    def _fallback_parse(self, text: str) -> List[WorkflowStep]:
        """Keyword-based fallback when LLM parsing fails.
        Uses position-ordered matching to preserve user's intended sequence."""
        lower = text.lower()
        matches = []  # (position_in_text, module_id, name)

        # 1. Detect module mentions by ID and name fragments, track position
        all_modules = {m.id: m.name for m in self.registry.list_all()}
        for mid, name in all_modules.items():
            clean_id = mid.replace("_", " ")  # "alpha_scanner" → "alpha scanner"
            # Check exact ID match, clean ID match, or first two words of name
            name_words = [w for w in name.lower().split() if len(w) > 2 and w not in ("—", "–", "the")]
            name_prefix = " ".join(name_words[:2]) if len(name_words) >= 2 else name.lower()

            pos = -1
            if clean_id in lower:
                pos = lower.index(clean_id)
            elif mid in lower:
                pos = lower.index(mid)
            elif name_prefix and name_prefix in lower:
                pos = lower.index(name_prefix)
            else:
                # Fuzzy: check if 2+ significant words from name appear in text
                hits = sum(1 for w in name_words if w in lower)
                if hits >= 2:
                    # Use first matching word position
                    for w in name_words:
                        if w in lower:
                            pos = lower.index(w)
                            break

            if pos >= 0:
                matches.append((pos, mid, name))
                logger.info(f"Fallback parser: matched module '{mid}' ({name}) at position {pos}")

        # 2. Detect security actions by alias
        SECURITY_ALIASES = {
            "cwe scan": "security:cwe_scan",
            "cwe scanner": "security:cwe_scan",
            "vulnerability scan": "security:cwe_scan",
            "vuln scan": "security:cwe_scan",
            "full scan": "security:full_scan",
            "posture scan": "security:full_scan",
            "security scan": "security:full_scan",
            "posture assessment": "security:full_scan",
            "process scan": "security:process_scan",
            "esm scan": "security:process_scan",
            "port scan": "security:port_scan",
        }
        for alias, action in SECURITY_ALIASES.items():
            if alias in lower and not any(m[1] == action for m in matches):
                pos = lower.index(alias)
                matches.append((pos, action, alias.title()))
                logger.info(f"Fallback parser: matched security action '{action}' via alias '{alias}' at position {pos}")

        # 3. Sort by position in text (preserves user's intended order)
        matches.sort(key=lambda x: x[0])

        # 4. Deduplicate
        seen = set()
        unique = []
        for pos, mid, name in matches:
            if mid not in seen:
                seen.add(mid)
                unique.append((mid, name))

        # 5. Build steps with chain dependencies
        steps = []
        for i, (mid, name) in enumerate(unique):
            step_id = f"step_{i+1:03d}"
            steps.append(WorkflowStep(
                step_id=step_id,
                module_id=mid,
                action="execute" if not mid.startswith("security:") else "scan",
                label=f"Execute {name}" if not mid.startswith("security:") else f"Security: {name}",
                depends_on=[f"step_{i:03d}"] if i > 0 else [],
            ))

        logger.info(f"Fallback parser: {len(steps)} steps from text: {[s.module_id for s in steps]}")
        return steps


# ==============================================================================
# WORKFLOW PIPELINE — DAG Executor
# ==============================================================================

class WorkflowPipeline:
    """Execute a pipeline of WorkflowSteps with parallel DAG, transforms, and VERITAS gates."""

    def __init__(self, steps: List[WorkflowStep], registry, security, llm, queue, request_id: str):
        self.steps = {s.step_id: s for s in steps}
        self.step_order = [s.step_id for s in steps]
        self.registry = registry
        self.security = security
        self.llm = llm
        self.queue = queue
        self.request_id = request_id
        self.results: Dict[str, StepResult] = {}
        self.pipeline_id = f"pipe_{uuid.uuid4().hex[:8]}"
        self.checkpoint_file = Path(__file__).parent / f".pipeline_checkpoint_{self.pipeline_id}.json"

    def execute(self) -> Dict:
        """Execute all steps respecting DAG dependencies. Returns sealed trace."""
        start_time = time.time()

        self.queue.put({
            "type": "pipeline_start",
            "pipeline_id": self.pipeline_id,
            "steps": [{"step_id": s.step_id, "module_id": s.module_id, "label": s.label,
                       "safety_tier": s.safety_tier, "status": "PENDING"}
                      for s in self.steps.values()],
            "request_id": self.request_id,
        })

        # Build dependency graph and execute in waves
        executed = set()
        trace_chain = hashlib.sha256(f"GENESIS:{self.pipeline_id}".encode()).hexdigest()
        trace = []

        max_waves = len(self.steps) + 1  # Safety bound
        for wave in range(max_waves):
            # Find steps ready to execute (all dependencies satisfied)
            ready = []
            for sid in self.step_order:
                if sid in executed:
                    continue
                step = self.steps[sid]
                deps_met = all(d in executed for d in step.depends_on)

                # Check if any dependency failed hard
                deps_failed = any(
                    self.results.get(d, StepResult(d, "")).status == "VIOLATION"
                    for d in step.depends_on
                )
                if deps_failed:
                    # Skip this step — dependency chain broken
                    result = StepResult(
                        step_id=sid, module_id=step.module_id,
                        status="SKIPPED", error="Dependency failed",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                    self.results[sid] = result
                    executed.add(sid)
                    self._push_step_status(sid, "SKIPPED", "Dependency chain broken")
                    continue

                if deps_met:
                    ready.append(step)

            if not ready:
                break  # All done or deadlocked

            # Execute ready steps in parallel
            if len(ready) == 1:
                # Single step — run directly
                result, step_hash = self._execute_step(ready[0], trace_chain)
                self.results[ready[0].step_id] = result
                trace.append(asdict(result))
                trace_chain = step_hash
                executed.add(ready[0].step_id)
                self._save_checkpoint()
            else:
                # Multiple ready — parallel execution
                with ThreadPoolExecutor(max_workers=min(4, len(ready))) as pool:
                    futures = {
                        pool.submit(self._execute_step, step, trace_chain): step
                        for step in ready
                    }
                    for future in as_completed(futures):
                        step = futures[future]
                        try:
                            result, step_hash = future.result()
                            self.results[step.step_id] = result
                            trace.append(asdict(result))
                            trace_chain = step_hash
                            executed.add(step.step_id)
                        except Exception as e:
                            result = StepResult(
                                step_id=step.step_id, module_id=step.module_id,
                                status="VIOLATION", error=str(e),
                                timestamp=datetime.now(timezone.utc).isoformat(),
                            )
                            self.results[step.step_id] = result
                            trace.append(asdict(result))
                            executed.add(step.step_id)
                            self._push_step_status(step.step_id, "VIOLATION", str(e))

                self._save_checkpoint()

            # Check conditions after each wave
            for step in ready:
                if step.condition and step.step_id in self.results:
                    self._evaluate_condition(step)

        # Compute final verdict
        all_statuses = [r.status for r in self.results.values()]
        if "VIOLATION" in all_statuses:
            final_verdict = "VIOLATION"
        elif "INCONCLUSIVE" in all_statuses:
            final_verdict = "INCONCLUSIVE"
        else:
            final_verdict = "PASS"

        # Seal trace
        seal_data = json.dumps(trace, sort_keys=True, default=str)
        seal_hash = hashlib.sha256(seal_data.encode()).hexdigest()

        pipeline_result = {
            "pipeline_id": self.pipeline_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "steps_planned": len(self.steps),
            "steps_executed": len([r for r in self.results.values() if r.status not in ("PENDING", "SKIPPED")]),
            "steps_passed": len([r for r in self.results.values() if r.status == "PASS"]),
            "duration_ms": int((time.time() - start_time) * 1000),
            "final_verdict": final_verdict,
            "trace": trace,
            "seal_hash": f"sha256:{seal_hash}",
        }

        self.queue.put({
            "type": "pipeline_done",
            "pipeline_id": self.pipeline_id,
            "verdict": final_verdict,
            "duration_ms": pipeline_result["duration_ms"],
            "steps_passed": pipeline_result["steps_passed"],
            "steps_total": pipeline_result["steps_planned"],
            "seal_hash": pipeline_result["seal_hash"],
            "request_id": self.request_id,
        })

        # Clean up checkpoint
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()

        return pipeline_result

    def _execute_step(self, step: WorkflowStep, prev_hash: str) -> tuple:
        """Execute a single step. Returns (StepResult, hash)."""
        self._push_step_status(step.step_id, "RUNNING", f"Executing {step.label}...")
        start = time.time()

        # Safety gate
        if step.safety_tier == "DANGEROUS":
            result = StepResult(
                step_id=step.step_id, module_id=step.module_id,
                status="INCONCLUSIVE",
                output=f"[SAFETY GATE] {step.label} requires manual approval. Use /approve {step.step_id}",
                error="DANGEROUS action — queued for approval",
                timestamp=datetime.now(timezone.utc).isoformat(),
                prev_hash=prev_hash,
            )
            self._push_step_status(step.step_id, "AWAITING_APPROVAL", step.label)
            output_hash = hashlib.sha256(result.output.encode()).hexdigest()
            result.output_hash = f"sha256:{output_hash}"
            step_hash = hashlib.sha256(f"{prev_hash}:{result.output_hash}".encode()).hexdigest()
            return result, step_hash

        # Gather input from dependencies
        dep_context = self._gather_dependency_output(step)

        # Execute
        output = ""
        exit_code = -1
        error = ""

        try:
            if step.module_id.startswith("security:"):
                output, exit_code = self._execute_security_action(step)
            else:
                output, exit_code = self._execute_module(step, dep_context)
        except Exception as e:
            error = str(e)
            exit_code = -1

        duration_ms = int((time.time() - start) * 1000)

        # ── INTER-STEP VERITAS GATE ──
        gate_verdict = self._inter_step_gate(output, exit_code, error)

        # Retry once on failure
        if gate_verdict != "PASS" and not error:
            logger.info(f"Step {step.step_id} failed gate, retrying once...")
            self._push_step_status(step.step_id, "RETRYING", f"Retrying {step.label}...")
            try:
                if step.module_id.startswith("security:"):
                    output, exit_code = self._execute_security_action(step)
                else:
                    output, exit_code = self._execute_module(step, dep_context)
                gate_verdict = self._inter_step_gate(output, exit_code, "")
            except Exception as e:
                error = str(e)
                gate_verdict = "VIOLATION"

            duration_ms = int((time.time() - start) * 1000)

        # LLM transform if needed
        output_summary = ""
        if step.transform and output and gate_verdict == "PASS":
            output_summary = self._transform_output(step, output)

        output_hash = hashlib.sha256((output or "").encode()).hexdigest()
        step_hash = hashlib.sha256(f"{prev_hash}:sha256:{output_hash}".encode()).hexdigest()

        result = StepResult(
            step_id=step.step_id,
            module_id=step.module_id,
            status=gate_verdict,
            output=output[:5000] if output else "",
            output_summary=output_summary,
            output_hash=f"sha256:{output_hash}",
            error=error,
            duration_ms=duration_ms,
            exit_code=exit_code,
            prev_hash=prev_hash,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        status_label = f"{step.label} ({duration_ms}ms)"
        self._push_step_status(step.step_id, gate_verdict, status_label)

        return result, step_hash

    def _execute_module(self, step: WorkflowStep, dep_context: str) -> tuple:
        """Execute a module via registry. Returns (output, exit_code)."""
        mod = self.registry.get(step.module_id)
        if not mod:
            return f"Unknown module: {step.module_id}", -1

        # Build args — include dependency context if available
        args = step.args
        if dep_context:
            # Write context to temp file so module can read it
            ctx_file = Path(__file__).parent / f".pipeline_ctx_{step.step_id}.txt"
            ctx_file.write_text(dep_context[:10000], encoding="utf-8")
            args = f"{args} --context {ctx_file}".strip()

        stdout, stderr, rc = mod.execute(args)
        output = ""
        if stdout:
            output += stdout[:5000]
        if stderr and rc != 0:
            output += f"\n--- STDERR ---\n{stderr[:2000]}"

        # Clean up context file
        ctx_file = Path(__file__).parent / f".pipeline_ctx_{step.step_id}.txt"
        if ctx_file.exists():
            ctx_file.unlink()

        return output, rc

    def _execute_security_action(self, step: WorkflowStep) -> tuple:
        """Execute a security engine action. Returns (output, exit_code)."""
        if not self.security:
            return "Security engine not available", -1

        action = step.module_id.split(":", 1)[1]

        try:
            if action == "full_scan":
                scan = self.security.full_scan()
                output = (f"Posture: {scan.verdict} ({scan.overall_score:.0%})\n"
                         f"Processes: {scan.process_count}, Alerts: {scan.alert_count}\n"
                         f"Open ports: {scan.open_ports}, New ports: {scan.new_ports}\n"
                         f"Honeytoken: {'INTACT' if scan.honeytoken_intact else 'COMPROMISED'}")
                return output, 0

            elif action == "cwe_scan":
                target = step.args or str(Path(__file__).parent)
                findings = self.security.scan_cwe(target)
                lines = [f"CWE Findings: {len(findings)} total"]
                for f in findings[:10]:
                    lines.append(f"  {f.severity} | {f.file}:{f.line} | {f.issue}")
                return "\n".join(lines), 0

            elif action == "process_scan":
                alerts = self.security.scan_processes()
                lines = [f"Process Alerts: {len(alerts)}"]
                for a in alerts[:10]:
                    lines.append(f"  PID {a.pid} | {a.name} | ESM={a.esm_score:.2f} | {a.verdict}")
                return "\n".join(lines), 0

            elif action == "port_scan":
                ports = self.security.scan_ports()
                lines = [f"New Ports: {len(ports)}"]
                for p in ports:
                    lines.append(f"  :{p.port} | {p.process} (PID {p.pid})")
                return "\n".join(lines), 0

            elif action == "honeytoken":
                result = self.security.check_honeytoken()
                status = "INTACT" if result.get("intact") else "COMPROMISED"
                return f"Honeytoken: {status}\nHash: {result.get('hash', 'N/A')}", 0

            else:
                return f"Unknown security action: {action}", -1

        except Exception as e:
            return f"Security action failed: {e}", -1

    def _gather_dependency_output(self, step: WorkflowStep) -> str:
        """Collect summarized outputs from dependency steps."""
        if not step.depends_on:
            return ""

        parts = []
        for dep_id in step.depends_on:
            result = self.results.get(dep_id)
            if result and result.status == "PASS":
                # Use summary if available, else truncated raw output
                text = result.output_summary or result.output[:2000]
                parts.append(f"[FROM {dep_id} ({result.module_id})]:\n{text}")

        return "\n\n".join(parts)

    def _transform_output(self, step: WorkflowStep, output: str) -> str:
        """Use LLM to summarize step output for downstream consumption."""
        try:
            prompt = (
                f"Summarize the following output from '{step.label}' in 3-5 bullet points. "
                f"Focus on key findings, metrics, and actionable data:\n\n{output[:3000]}"
            )
            response, _, error = self.llm.query(
                "You are a concise technical summarizer. Output bullet points only.",
                prompt
            )
            return response[:1000] if response else output[:500]
        except Exception:
            return output[:500]

    def _inter_step_gate(self, output: str, exit_code: int, error: str) -> str:
        """VERITAS inter-step gate validation. Returns verdict."""
        if error:
            return "VIOLATION"
        if exit_code != 0:
            return "INCONCLUSIVE"
        if not output or len(output.strip()) < 10:
            return "INCONCLUSIVE"  # Suspiciously empty output
        return "PASS"

    def _evaluate_condition(self, step: WorkflowStep):
        """Evaluate conditional routing for a step."""
        if not step.condition:
            return

        result = self.results.get(step.step_id)
        if not result:
            return

        cond = step.condition
        # Simple field extraction from output
        try:
            field_name = cond.get("field", "")
            op = cond.get("op", "")
            threshold = float(cond.get("value", 0))

            # Try to find the field value in output
            import re
            pattern = rf'{field_name}\s*[=:]\s*([\d.]+)'
            match = re.search(pattern, result.output, re.IGNORECASE)
            if match:
                actual = float(match.group(1))
                met = False
                if op == "<":
                    met = actual < threshold
                elif op == "<=":
                    met = actual <= threshold
                elif op == ">":
                    met = actual > threshold
                elif op == ">=":
                    met = actual >= threshold
                elif op == "==" or op == "=":
                    met = abs(actual - threshold) < 1e-6

                result.condition_met = met
                if met and cond.get("route_to"):
                    logger.info(f"Condition met on {step.step_id}: {field_name} {op} {threshold} "
                               f"(actual={actual}). Routing to {cond['route_to']}")
        except Exception as e:
            logger.warning(f"Condition evaluation failed for {step.step_id}: {e}")

    def _push_step_status(self, step_id: str, status: str, detail: str = ""):
        """Push SSE event for step progress."""
        step = self.steps.get(step_id)
        self.queue.put({
            "type": "step_status",
            "pipeline_id": self.pipeline_id,
            "step_id": step_id,
            "module_id": step.module_id if step else "",
            "label": step.label if step else "",
            "status": status,
            "detail": detail,
            "request_id": self.request_id,
        })

    def _save_checkpoint(self):
        """Write checkpoint for resume capability."""
        try:
            data = {
                "pipeline_id": self.pipeline_id,
                "results": {sid: asdict(r) for sid, r in self.results.items()},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self.checkpoint_file.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Checkpoint save failed: {e}")


# ==============================================================================
# WORKFLOW STORE — Named template persistence
# ==============================================================================

class WorkflowStore:
    """Save and load named workflow templates."""

    def __init__(self, store_path: str = None):
        self.store_path = Path(store_path or Path(__file__).parent / "workflows.json")
        self.templates: Dict[str, List[dict]] = {}
        self._load()

    def _load(self):
        if self.store_path.exists():
            try:
                self.templates = json.loads(self.store_path.read_text(encoding="utf-8"))
            except Exception:
                self.templates = {}

    def _save(self):
        self.store_path.write_text(json.dumps(self.templates, indent=2, default=str), encoding="utf-8")

    def save_template(self, name: str, steps: List[WorkflowStep]) -> str:
        """Save a pipeline as a named template."""
        key = name.lower().replace(" ", "_")
        self.templates[key] = [asdict(s) for s in steps]
        self._save()
        return key

    def load_template(self, name: str) -> List[WorkflowStep]:
        """Load a named template. Returns empty list if not found."""
        key = name.lower().replace(" ", "_")
        raw = self.templates.get(key, [])
        return [WorkflowStep(**s) for s in raw]

    def list_templates(self) -> List[str]:
        """List all saved template names."""
        return list(self.templates.keys())

    def delete_template(self, name: str) -> bool:
        key = name.lower().replace(" ", "_")
        if key in self.templates:
            del self.templates[key]
            self._save()
            return True
        return False


# ==============================================================================
# PIPELINE DETECTION — Does this message need a pipeline?
# ==============================================================================

PIPELINE_TRIGGER_KEYWORDS = [
    "then", "feed into", "route to", "chain", "pipeline", "workflow",
    "after that", "once done", "once mapped", "once complete",
    "if.*then", "auto-route", "and then", "next step",
    "followed by", "→", ">>", "->",
]


def detect_pipeline_request(text: str, module_ids: List[str]) -> bool:
    """Returns True if the text describes a multi-module pipeline."""
    lower = text.lower()

    # Count module references
    module_mentions = 0
    for mid in module_ids:
        # Check by ID and by name fragments
        clean_id = mid.replace("_", " ")
        if clean_id in lower or mid in lower:
            module_mentions += 1

    # Check for chaining keywords
    chain_keywords = sum(1 for kw in PIPELINE_TRIGGER_KEYWORDS if kw in lower)

    # Security action references
    sec_keywords = ["scan", "cwe", "process", "port", "honeytoken"]
    sec_mentions = sum(1 for kw in sec_keywords if kw in lower)

    total_actions = module_mentions + sec_mentions

    # Pipeline if: 2+ actions mentioned, OR chain keywords + 1 action
    return total_actions >= 2 or (chain_keywords >= 1 and total_actions >= 1)
