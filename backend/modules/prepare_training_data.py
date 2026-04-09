"""
VERITAS COMMAND CENTER — Fine-Tuning Data Generator
Extracts knowledge from all 12 project source files into Vertex AI JSONL format.
Output: training_data.jsonl ready for upload to Google Cloud Storage.

Format per Vertex AI docs:
{"contents": [{"role": "user", "parts": [{"text": "..."}]}, {"role": "model", "parts": [{"text": "..."}]}]}
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
MODULES_DIR = PROJECT_ROOT / "modules"

# ==============================================================================
# MODULE KNOWLEDGE EXTRACTION
# ==============================================================================

# Each entry: (module_id, source_dir, key_files, knowledge_pairs)
# knowledge_pairs = list of (user_question, model_answer) tuples
MODULE_KNOWLEDGE = {
    "aegis_ald": {
        "name": "AEGIS-ALD Autonomous Logic Defense",
        "key_files": ["main.py", "engine.py", "gates.py", "contracts.py"],
        "qa_pairs": [
            ("What is AEGIS-ALD?",
             "AEGIS-ALD is the Autonomous Logic Defense system — it's a gate-based verification engine "
             "that runs claims through a series of typed gates: INTAKE, TYPE, EVIDENCE, MATH, COST, "
             "INCENTIVE, IRREVERSIBILITY, ADVERSARY, and TRACE/SEAL. Each gate produces a verdict "
             "(PASS, MODEL_BOUND, INCONCLUSIVE, or VIOLATION) and the final verdict follows precedence: "
             "VIOLATION > INCONCLUSIVE > MODEL_BOUND > PASS."),
            ("How do I run the AEGIS verifier?",
             "Run it with: python main.py --payload <path_to_payload.json>. The engine processes "
             "the claim through all gates in order and produces a sealed verdict with a trace chain. "
             "You can also use --selftest to run the Golden Verdict Suite."),
            ("What's the ALD gate order?",
             "The gate order is strictly: INTAKE → TYPE → EVIDENCE → MATH → COST → INCENTIVE → "
             "IRREVERSIBILITY → ADVERSARY → TRACE/SEAL. This is a total acyclic order. Each gate "
             "produces a GateResult with verdict, reason_code, and witnesses."),
        ]
    },
    "goliath_leviathan": {
        "name": "Goliath Leviathan Forensic Scanner",
        "key_files": ["goliath_leviathan.py"],
        "qa_pairs": [
            ("What does Goliath Leviathan do?",
             "Goliath Leviathan is a deep forensic scanner for the Unified Truth Matrix. It analyzes "
             "disclosure corpora — documents, evidence chains, and narrative structures — to identify "
             "contradictions, inconsistencies, and logical gaps. It generates forensic audit reports."),
            ("Run Goliath on the disclosure corpus",
             "Sure thing. I'll fire up the Goliath scanner. It processes documents through pattern "
             "matching, contradiction detection, and evidence chain analysis. The output will be a "
             "structured forensic report with findings ranked by severity."),
        ]
    },
    "sentinel_omega": {
        "name": "Sentinel Omega Command Platform",
        "key_files": ["api_gate.py", "sentinel_core/ui.py", "sentinel_core/config.py",
                      "sentinel_core/engine.py", "sentinel_core/audit.py"],
        "qa_pairs": [
            ("What is Sentinel Omega?",
             "Sentinel Omega is the original command platform — a tkinter-based security operations center "
             "with 5 tabs: Mission Control, Security Hardening, Network Zones, Audit Logs, and Telemetry. "
             "It includes the API Gate for OpenAI integration, a Circuit Breaker for fail-safe operations, "
             "the Risk Engine for threat assessment, and the Gravity Shield enforcement layer."),
            ("How does the Sentinel API Gate work?",
             "The API Gate (api_gate.py) manages OpenAI API calls with optional SOCKS proxy support for "
             "anonymized requests. It checks the OPENAI_API_KEY environment variable, supports offline mode "
             "via VERITAS_OFFLINE=1, and uses the Dark-Strike red-team configuration for strategic operations."),
        ]
    },
    "titan_engine": {
        "name": "Titan Extraction Engine",
        "key_files": ["veritas_sovereign_v42.py"],
        "qa_pairs": [
            ("What's the Titan Engine?",
             "The Titan Engine is a 10-worker parallel data extraction system. It uses a hardened RPC rotation "
             "scheme for distributed data collection, with real-time persistence to a local database. "
             "It was built for deep extraction pulses and whale synchronization monitoring."),
            ("How do I start Titan?",
             "Run: python veritas_sovereign_v42.py with the appropriate database configuration. The engine "
             "initializes 10 worker threads, rotates through RPC endpoints, and persists extracted data "
             "in real-time. Monitor the output for sync confirmations."),
        ]
    },
    "kinetic_siphon": {
        "name": "Kinetic Siphon Passive Egress Monitor",
        "key_files": ["veritas_sovereign_v42.py"],
        "qa_pairs": [
            ("What does the Kinetic Siphon do?",
             "The Kinetic Siphon is a passive egress monitor that listens on Port 445 for connection attempts. "
             "It logs all egress events and immediately closes connections. It also generates audit files with "
             "CLAEG-formatted log paths for testing local agent behavior. It's part of the Sovereign Security Suite."),
        ]
    },
    "sovereign_v42": {
        "name": "Sovereign Physics Auditor v4.2",
        "key_files": ["veritas_sovereign_v42.py"],
        "qa_pairs": [
            ("What is the Sovereign Physics Auditor?",
             "Sovereign v4.2 is a physics audit engine that validates Bernoulli-compatible fluid dynamics "
             "claims, thermodynamic boundary conditions, and kinematic constraint satisfaction. It applies "
             "VERITAS Omega v1.3 gates to physics models — checking energy conservation, momentum invariants, "
             "and Reynolds number regimes."),
            ("Run a physics audit on the Bernoulli data",
             "I'll spin up Sovereign v4.2. It validates: (1) pressure-velocity relationships against Bernoulli's "
             "equation, (2) boundary layer conditions, (3) Reynolds number regime classification, and (4) energy "
             "conservation invariants. Results come back as PASS/MODEL_BOUND/INCONCLUSIVE/VIOLATION."),
        ]
    },
    "reality_compiler": {
        "name": "Reality Compiler Evidence Processor",
        "key_files": ["goliath_leviathan.py"],
        "qa_pairs": [
            ("What's the Reality Compiler?",
             "The Reality Compiler is the evidence processing layer — it compiles raw observations, witness "
             "statements, and physical evidence into structured evidence clusters that can be evaluated by "
             "the AEGIS gate system. It handles provenance tracking, independence graph construction, and "
             "agreement scoring between evidence items."),
        ]
    },
    "atc_engine": {
        "name": "ATC Falsification Engine",
        "key_files": ["atc_engine.py", "global_physics.py"],
        "qa_pairs": [
            ("What does the ATC Engine do?",
             "The ATC Falsification Engine verifies air traffic control data for physics compliance. It enforces "
             "kinematic gates (velocity, acceleration, altitude bounds), temporal gates (timestamp ordering, gap "
             "detection), CPA calculations (Closest Point of Approach), NIC isolation (Navigation Integrity "
             "Category), and deterministic vertical prediction rules. It's a fail-closed system — any anomaly "
             "triggers VIOLATION."),
            ("How does the ATC physics validation work?",
             "The GLOBAL_PHYSICS_V1_1 regime defines strict invariants: max ground speed 600 kts, max altitude "
             "60000 ft, vertical rate bounds of +/- 6000 fpm. The engine processes ADS-B messages through "
             "an ingestion probe, separation probe, and trend analyzer. Each flight track is validated against "
             "these physical constraints independently. Violations are immediate and non-negotiable."),
        ]
    },
    "project_sv": {
        "name": "Project SV Compression Benchmark",
        "key_files": [],
        "qa_pairs": [
            ("What is Project SV?",
             "Project SV is a codec and compression benchmark suite. It evaluates compression algorithms "
             "across different data types — measuring compression ratios, throughput, latency, and quality "
             "metrics. It's used for comparing different encoding strategies for the Veritas data pipeline."),
        ]
    },
    "whatsapp_t1": {
        "name": "WhatsApp Security Test Automation",
        "key_files": ["T1_test.py"],
        "qa_pairs": [
            ("What's the WhatsApp T1 test?",
             "The WhatsApp T1 test is a semi-automated security testing framework for WhatsApp Web. It sends "
             "test attachments (Lane 1), pauses for manual observation on the mobile device, and logs results "
             "interactively. It tests file handling, attachment processing, and identifies anomalies in how "
             "WhatsApp processes different file types."),
        ]
    },
    "pipeline_router": {
        "name": "Veritas Omega Pipeline Router",
        "key_files": [],
        "qa_pairs": [
            ("What does the Pipeline Router do?",
             "The Pipeline Router manages the detonation pipeline — it routes verification payloads through "
             "the appropriate processing chain (AEGIS gates, forensic analysis, physics validation) based on "
             "the payload type and security classification. It handles payload staging, execution isolation, "
             "and result aggregation."),
        ]
    },
    "thermal_shield": {
        "name": "Thermal Shield NAEF Compliance",
        "key_files": [],
        "qa_pairs": [
            ("What is the Thermal Shield?",
             "Thermal Shield is the NAEF (Narrative & Agency Elimination Framework) compliance layer. It "
             "monitors all system outputs for narrative justification, deferred closure, authority override, "
             "and unbounded optimism — the four banned patterns under VERITAS Omega v1.3. Any violation "
             "triggers a containment response. Think of it as the immune system that keeps the AI honest."),
        ]
    },
}


def extract_source_knowledge(module_id, module_dir):
    """Extract code-level knowledge from source files for training data."""
    pairs = []
    if not module_dir.exists():
        return pairs

    # Get all Python files
    py_files = list(module_dir.glob("**/*.py"))
    if not py_files:
        return pairs

    for py_file in py_files[:5]:  # Limit to 5 files per module
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            if len(content) < 100:
                continue

            # Extract classes and functions for Q&A
            lines = content.split("\n")
            classes = [l.strip() for l in lines if l.strip().startswith("class ")]
            functions = [l.strip() for l in lines if l.strip().startswith("def ")]

            if classes:
                class_list = ", ".join(c.split("(")[0].replace("class ", "") for c in classes[:5])
                pairs.append((
                    f"What classes are in {py_file.name} of {module_id}?",
                    f"The key classes in {py_file.name} are: {class_list}. "
                    f"This file is part of the {module_id} module."
                ))

            if functions:
                func_list = ", ".join(f.split("(")[0].replace("def ", "") for f in functions[:8])
                pairs.append((
                    f"What functions does {py_file.name} in {module_id} have?",
                    f"The main functions in {py_file.name} are: {func_list}."
                ))

            # Extract docstrings
            in_docstring = False
            docstring_lines = []
            for line in lines:
                stripped = line.strip()
                if '"""' in stripped:
                    if in_docstring:
                        in_docstring = False
                        docstring = " ".join(docstring_lines).strip()
                        if len(docstring) > 30:
                            pairs.append((
                                f"Describe the purpose of a component in {module_id}",
                                docstring[:500]
                            ))
                        docstring_lines = []
                    else:
                        in_docstring = True
                        # Check if docstring is single-line
                        parts = stripped.split('"""')
                        if len(parts) >= 3 and parts[1].strip():
                            docstring = parts[1].strip()
                            if len(docstring) > 20:
                                pairs.append((
                                    f"What does this component in {module_id} do?",
                                    docstring[:500]
                                ))
                elif in_docstring:
                    docstring_lines.append(stripped)

        except Exception as e:
            continue

    return pairs


def generate_system_pairs():
    """Generate system-level Q&A pairs about the Command Center itself."""
    return [
        ("What projects do you manage?",
         "I manage 12 integrated project modules: AEGIS-ALD (gate verification), Goliath Leviathan (forensic scanning), "
         "Sentinel Omega (command platform), Titan Engine (data extraction), Kinetic Siphon (egress monitoring), "
         "Sovereign v4.2 (physics auditing), Reality Compiler (evidence processing), ATC Falsification Engine "
         "(flight data verification), Project SV (compression benchmarks), WhatsApp T1 (security testing), "
         "Pipeline Router (payload routing), and Thermal Shield (NAEF compliance)."),
        ("Who are you?",
         "I'm Sentinel Omega — the kinetic layer of a Dual-Node MMI. My partner is RJ Lopez, the Architect. "
         "Operative motto: Examina omnia, venerare nihil. I'm the conversational AI interface for the VERITAS "
         "Command Center v2.0, running on Gemini 2.5 Pro with Ollama and OpenAI fallback."),
        ("What's VERITAS Omega?",
         "VERITAS Omega v1.3 is the canonical specification that governs all technical reasoning in this system. "
         "It defines a gate-based verification pipeline with typed primitives, operators, evidence models, and "
         "attack suites. Key verdicts: PASS, MODEL_BOUND, INCONCLUSIVE, VIOLATION — in that precedence order. "
         "The framework prohibits narrative justification, deferred closure, authority override, and unbounded optimism."),
        ("What's CLAEG?",
         "CLAEG stands for Constrained Language & Evaluation Grammar. It's the formal logic framework that requires: "
         "(1) all objects have declared type and domain (Primitive Declaration), (2) no operator without defined "
         "domain and codomain (Operator Declaration), (3) conservation, rigidity, and continuity are axioms "
         "(Invariant Declaration), and (4) terminal outcomes are PASS, THEORETICAL_MAX, MODEL_BOUND, INCONCLUSIVE, "
         "or VIOLATION."),
        ("What's NAEF?",
         "NAEF is the Narrative & Agency Elimination Framework. It bans four patterns: (1) narrative justification "
         "like 'should work' or 'industry standard', (2) deferred closure like 'we will fix later', (3) authority "
         "override — no claim accepted on authority alone, and (4) all optimism must be bounded or rejected. "
         "The Thermal Shield module enforces NAEF compliance across the entire system."),
    ]


def build_training_data():
    """Build complete JSONL training dataset."""
    all_pairs = []

    # 1. System-level pairs
    system_pairs = generate_system_pairs()
    all_pairs.extend(system_pairs)
    print(f"[DATA] System pairs: {len(system_pairs)}")

    # 2. Module Q&A pairs (hand-crafted)
    for mid, info in MODULE_KNOWLEDGE.items():
        all_pairs.extend(info["qa_pairs"])
        print(f"[DATA] {mid}: {len(info['qa_pairs'])} hand-crafted pairs")

    # 3. Source code extraction
    for mid in MODULE_KNOWLEDGE:
        module_dir = MODULES_DIR / mid
        source_pairs = extract_source_knowledge(mid, module_dir)
        all_pairs.extend(source_pairs)
        if source_pairs:
            print(f"[DATA] {mid}: {len(source_pairs)} extracted from source")

    # 4. Write JSONL
    output_path = PROJECT_ROOT / "training_data.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for user_q, model_a in all_pairs:
            entry = {
                "contents": [
                    {"role": "user", "parts": [{"text": user_q}]},
                    {"role": "model", "parts": [{"text": model_a}]}
                ]
            }
            f.write(json.dumps(entry) + "\n")

    print(f"\n[DONE] Wrote {len(all_pairs)} training examples to {output_path}")
    print(f"[INFO] Minimum recommended: 100 examples. You have: {len(all_pairs)}")
    if len(all_pairs) < 100:
        print(f"[WARN] Consider adding more examples for better fine-tuning results.")
    return len(all_pairs)


if __name__ == "__main__":
    print("=" * 60)
    print("VERITAS FINE-TUNING DATA GENERATOR")
    print("=" * 60)
    count = build_training_data()
    print(f"\nNext steps:")
    print(f"  1. Upload training_data.jsonl to Google Cloud Storage")
    print(f"  2. Go to Vertex AI Studio > Tuning > Create tuned model")
    print(f"  3. Select gemini-2.0-flash-001 as base model")
    print(f"  4. Point to gs://your-bucket/training_data.jsonl")
    print(f"  5. Start training (~30 min)")
