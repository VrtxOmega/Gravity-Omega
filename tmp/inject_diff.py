import sys
import re

with open('c:/Veritas_Lab/gravity-omega-v2/backend/web_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add import
if 'from modules.state_monitor import snapshot_state, diff_state' not in content:
    content = content.replace(
        'from omega_bypass_trap import BypassTrap',
        'from omega_bypass_trap import BypassTrap\nfrom modules.state_monitor import snapshot_state, diff_state'
    )

# Find _vtp_direct_executor body
import_hook = """def _vtp_direct_executor(packet: vtp_codec.VTPPacket) -> str:
    \"\"\"Fast-path deterministic execution without LLM overhead.\"\"\"
    
    # Post-Execution State Diffing (Priority 7) Hook
    track_state = False
    expected_mods = set()
    scope = os.getcwd()
    before_state = {}
    
    if packet.act in ("MUT", "REQ") and packet.tgt in ("AST", "SYS", "PY", "JS", "CSS", "JSON", "MD", "TXT"):
        track_state = True
        before_state = snapshot_state(scope)
        # Try to extract the expected file to be modified implicitly
        try:
            if packet.tgt != "SYS":
                prm_data = json.loads(packet.prm)
                if prm_data.get("path"):
                    expected_mods.add(str(prm_data["path"]))
        except Exception:
            parts = str(packet.prm).strip('"\\'').split("::")
            if len(parts) >= 2 and packet.tgt != "SYS":
                expected_mods.add(parts[0])

    try:
"""

if '# Post-Execution State Diffing (Priority 7) Hook' not in content:
    content = content.replace(
        'def _vtp_direct_executor(packet: vtp_codec.VTPPacket) -> str:\n    """Fast-path deterministic execution without LLM overhead."""',
        import_hook
    )

    # Now we need to append the finally block.
    # WAIT! Instead of wrapping the whole function and breaking Returns, we can define a wrapper function.
    pass

# Better approach: We can rename _vtp_direct_executor to _vtp_direct_executor_inner
# and define a new _vtp_direct_executor that wraps it!

if 'def _vtp_direct_executor_inner' not in content:
    content = content.replace('def _vtp_direct_executor(packet: vtp_codec.VTPPacket) -> str:', 'def _vtp_direct_executor_inner(packet: vtp_codec.VTPPacket) -> str:')

    wrapper = """def _vtp_direct_executor(packet: vtp_codec.VTPPacket) -> str:
    \"\"\"Fast-path deterministic execution wrapped with State Anomaly Detection.\"\"\"
    track_state = packet.act in ("MUT", "REQ") and packet.tgt in ("AST", "SYS", "PY", "JS", "CSS", "JSON", "MD", "TXT")
    scope = os.getcwd()
    before_state = {}
    expected_mods = set()

    if track_state:
        before_state = snapshot_state(scope)
        try:
            if packet.tgt != "SYS":
                prm_data = json.loads(packet.prm)
                if prm_data.get("path"):
                    expected_mods.add(os.path.normpath(str(prm_data["path"])))
        except Exception:
            parts = str(packet.prm).strip('"\\'').split("::")
            if len(parts) >= 2 and packet.tgt != "SYS":
                expected_mods.add(os.path.normpath(parts[0]))

    result = _vtp_direct_executor_inner(packet)
    
    if track_state:
        after_state = snapshot_state(scope)
        anomalies = diff_state(before_state, after_state, expected_mods)
        if anomalies:
            log.warning(f"STATE_ANOMALY DETECTED: {len(anomalies)} files modified outside target. {str(anomalies)[:500]}")
            # If using VERITAS SEAL, we append a forensic note here to vtp packet or ledger
            # The ledger is passed in VTPRouter, handled separately. We just log for now to raise visibility.
            
    return result

def _vtp_direct_executor_inner(packet: vtp_codec.VTPPacket) -> str:"""

    content = content.replace('def _vtp_direct_executor_inner(packet: vtp_codec.VTPPacket) -> str:\n    """Fast-path deterministic execution without LLM overhead."""', wrapper)

    with open('c:/Veritas_Lab/gravity-omega-v2/backend/web_server.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Wrapped _vtp_direct_executor successfully.")
else:
    print("Already wrapped.")
