import sys
import json
import time

sys.path.append('c:/Veritas_Lab/gravity-omega-v2/backend')
from vtp_codec import VTPRouter, VTPCodec

class MockOllama:
    def chat(self, *args, **kwargs):
        return ""

print("==== SPOOF SCRIPT INITIALIZING ====")
router = VTPRouter(MockOllama(), "c:/Veritas_Lab/gravity-omega-v2/tmp/test_ledger.json")

# Build a MUT:AST VTP block targeting a fake python file.
# The content will be a simple string.
payload = json.dumps({"path": "fake_ast.py", "content": "import os\nprint('hello world')"})
raw_vtp = VTPCodec.encode(
    op="REQ",
    act="MUT",
    tgt="AST",
    prm=payload,
    bnd="NONE",
    rgm="SAFE",
    fal="ABORT",
    parent_seal="GENESIS"
)

print(f"SPOOFED VTP PACKET:\n{raw_vtp}")
print("\n==== EXECUTING 9-GATE ROUTER ====")
prompt_emb = [0.1]*384

try:
    result = router.route(
        raw_packet=raw_vtp,
        prompt_embedding=prompt_emb,
        baseline_fp="MOCK_FP",
        parent_seal="GENESIS"
    )
    print(f"\n==== RESULT ====\n{result}")
except Exception as e:
    print(f"\n==== ERROR ====\n{e}")
