import re
import json

with open('c:/Veritas_Lab/gravity-omega-v2/backend/vtp_codec.py', 'r', encoding='utf-8') as f:
    content = f.read()

SCHEMA_BLOCK = """
# ─────────────────────────────────────────────
# EXACT TGT PAYLOAD SCHEMAS
# ─────────────────────────────────────────────
def _validate_mut_ast(prm: str) -> tuple[bool, str]:
    try:
        data = json.loads(prm)
    except Exception:
        # Legacy fallback support
        parts = str(prm).strip('"\\'').split('::')
        if len(parts) in (2, 3):
            return True, "OK"
        return False, "SCHEMA_INVALID_JSON"
    
    if not isinstance(data, dict): return False, "SCHEMA_NOT_DICT"
    if "path" not in data: return False, "SCHEMA_MISSING_FIELD:path"
    if "content" not in data and "find" not in data: return False, "SCHEMA_MISSING_FIELD:content_or_find"
    return True, "OK"

def _validate_req_sys(prm: str) -> tuple[bool, str]:
    if not prm or len(str(prm).strip()) == 0:
        return False, "SCHEMA_MISSING_COMMAND"
    return True, "OK"

def _validate_req_net(prm: str) -> tuple[bool, str]:
    if not prm or len(str(prm).strip()) == 0:
        return False, "SCHEMA_MISSING_URL"
    return True, "OK"

VTP_SCHEMAS = {
    "MUT:AST": _validate_mut_ast,
    "REQ:SYS": _validate_req_sys,
    "REQ:NET": _validate_req_net
}

def validate_tgt_schema(act: str, tgt: str, prm: str) -> tuple[bool, str]:
    pseudo = f"{act}:{tgt}"
    if pseudo not in VTP_SCHEMAS:
        return True, "OK"
    return VTP_SCHEMAS[pseudo](prm)
"""

if "validate_tgt_schema" not in content:
    content = content.replace("class VTPCodec:", SCHEMA_BLOCK + "\nclass VTPCodec:")

ROUTER_BLOCK = """        # ── S1: PARSE ────────────────────────────────
        self.state = RouterState.S1_PARSE
        
        # Pre-HMAC structural validation
        struct_ok, struct_reason = validate_packet_structure(raw_packet)
        if not struct_ok:
            return self._fail(RouterState.F1_PARSE_FAIL, None, f"MALFORMED:{struct_reason}", parent_seal)
            
        try:
            packet = VTPCodec.decode(raw_packet)
        except ValueError as e:
            return self._fail(RouterState.F1_PARSE_FAIL, None, str(e), parent_seal)

        # ── S1.5: SCHEMA VALIDATE ────────────────────────────────
        schema_ok, schema_reason = validate_tgt_schema(packet.act, packet.tgt, packet.prm)
        if not schema_ok:
            return self._fail(RouterState.F1_PARSE_FAIL, packet, f"SCHEMA_FAIL:{schema_reason}", parent_seal)
"""

content = re.sub(
    r"# ── S1: PARSE ────────────────────────────────.*?try:.*?except ValueError as e:.*?return self\._fail\(RouterState\.F1_PARSE_FAIL, None, str\(e\), parent_seal\)",
    ROUTER_BLOCK,
    content,
    flags=re.DOTALL
)

with open('c:/Veritas_Lab/gravity-omega-v2/backend/vtp_codec.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("vtp_codec.py updated.")

# Frontend JS update
with open('c:/Veritas_Lab/gravity-omega-v2/omega/vtp_codec.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

JS_SCHEMA_BLOCK = """    static validate_tgt_schema(act, tgt, prm) {
        const pseudo = `${act}:${tgt}`;
        if (pseudo === 'MUT:AST') {
            try {
                const data = JSON.parse(prm);
                if (!data.path) return { ok: false, reason: "SCHEMA_MISSING_FIELD:path" };
                if (!data.content && !data.find) return { ok: false, reason: "SCHEMA_MISSING_FIELD:content_or_find" };
            } catch (e) {
                const parts = String(prm).replace(/^["']|["']$/g, '').split('::');
                if (parts.length < 2) return { ok: false, reason: "SCHEMA_INVALID_JSON" };
            }
        } else if (pseudo === 'REQ:SYS') {
            if (!prm || String(prm).trim().length === 0) return { ok: false, reason: "SCHEMA_MISSING_COMMAND" };
        } else if (pseudo === 'REQ:NET') {
            if (!prm || String(prm).trim().length === 0) return { ok: false, reason: "SCHEMA_MISSING_URL" };
        }
        return { ok: true, reason: "OK" };
    }

    static encode(op, act, tgt, prm, bnd, rgm, fal, parent_seal, drift = null, res = null, nonce = null) {"""

if "validate_tgt_schema" not in js_content:
    js_content = js_content.replace(
        "    static encode(op, act, tgt, prm, bnd, rgm, fal, parent_seal, drift = null, res = null, nonce = null) {",
        JS_SCHEMA_BLOCK
    )

    with open('c:/Veritas_Lab/gravity-omega-v2/omega/vtp_codec.js', 'w', encoding='utf-8') as f:
        f.write(js_content)
    print("vtp_codec.js updated.")
else:
    print("vtp_codec.js already has validate_tgt_schema.")
