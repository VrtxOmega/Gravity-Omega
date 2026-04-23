import os
import sys

target_file = 'c:/Veritas_Lab/gravity-omega-v2/backend/vtp_codec.py'

with open(target_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Add MCP client import at the top
import_statement = "from mcp_client import get_mcp_client\nimport tempfile"
if 'from mcp_client import get_mcp_client' not in content:
    content = content.replace("from datetime import datetime", f"{import_statement}\nfrom datetime import datetime")

# We will locate the ZERO-LLM FAST PATH section and inject the 9-Gate pipeline just before it
fast_path_marker = "# ── ZERO-LLM FAST PATH ────────────────────────"

mcp_injection = """        # ── VERITAS Ω 9-GATE PIPELINE (MCP Orchestration) ──
        # Gates 3-8: EVIDENCE -> MATH -> COST -> INCENTIVE -> IRREVERSIBILITY -> ADVERSARY
        if packet.act == "MUT" and packet.tgt in ("AST", "PY"):
            # Elevate irreversibility thresholds if altering python code
            mcp = get_mcp_client()
            
            prm_data = {}
            try:
                prm_data = json.loads(packet.prm)
            except Exception:
                pass
                
            path = prm_data.get('path') if isinstance(prm_data, dict) else None
            new_content = prm_data.get('content') if isinstance(prm_data, dict) else None
            
            if path and new_content and path.endswith('.py'):
                # Write to temp file for assessing
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py', encoding='utf-8') as tmp_f:
                    tmp_f.write(new_content)
                    tmp_path = tmp_f.name
                
                try:
                    assessment = mcp.assess_file_sync(tmp_path, mode="veritas")
                    verdict = assessment.get("verdict", "INCONCLUSIVE")
                    
                    if verdict in ("VIOLATION", "MODEL_BOUND", "INCONCLUSIVE"):
                        os.unlink(tmp_path)
                        return self._fail(RouterState.F2_NAEF_FAIL, packet, f"VERITAS_GATE_FAIL:{verdict}", parent_seal)
                        
                    # Also log to ledger that MCP assessed it
                    self.ledger.append("MCP_ASSESS", packet, f"verdict={verdict}", RouterState.S2_NAEF)
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
        
        # ── S9: TRACE/SEAL ───────────────────────────
        # Handled at execution completion by appending TRACE_CHAIN to ledger mapping PolicyHash.
        
"""

if '# ── VERITAS Ω 9-GATE PIPELINE (MCP Orchestration) ──' not in content:
    content = content.replace(fast_path_marker, mcp_injection + fast_path_marker)
    
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Injected VERITAS MCP orchestration into vtp_codec.py")
else:
    print("Already injected.")
