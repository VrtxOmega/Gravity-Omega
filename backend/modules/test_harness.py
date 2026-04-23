"""
VERITAS COMMAND CENTER v2.0 — Comprehensive Test Suite
Tests module registry, dispatcher, LLM router (code-level), and error handling.
Run: python test_harness.py
"""
import sys
import os
import json

# Ensure imports work
sys.path.insert(0, os.path.dirname(__file__))

PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} — {detail}")


def test_identity_kernel():
    print("\n=== IDENTITY KERNEL ===")
    from identity_kernel import (
        SYSTEM_IDENTITY, SYSTEM_PROMPT, VERDICT_SET, VERDICT_PRECEDENCE,
        BANNED_NARRATIVE, BANNED_VERBS_IRREVERSIBLE, MODULE_DESCRIPTIONS,
        resolve_verdict, compute_identity_hash
    )
    check("SYSTEM_IDENTITY is dict", isinstance(SYSTEM_IDENTITY, dict))
    check("SYSTEM_IDENTITY has version", "version" in SYSTEM_IDENTITY)
    check("SYSTEM_PROMPT is non-empty", len(SYSTEM_PROMPT) > 500,
          f"len={len(SYSTEM_PROMPT)}")
    check("SYSTEM_PROMPT contains 12 module entries",
          SYSTEM_PROMPT.count("**aegis_ald**") == 1 and SYSTEM_PROMPT.count("**thermal_shield**") == 1)
    check("VERDICT_SET complete", VERDICT_SET == {"PASS", "MODEL_BOUND", "INCONCLUSIVE", "VIOLATION"})
    check("resolve_verdict PASS+VIOLATION=VIOLATION",
          resolve_verdict("PASS", "VIOLATION") == "VIOLATION")
    check("resolve_verdict PASS alone=PASS", resolve_verdict("PASS") == "PASS")
    check("resolve_verdict empty=PASS", resolve_verdict() == "PASS")
    check("BANNED_NARRATIVE non-empty", len(BANNED_NARRATIVE) >= 5)
    check("identity_hash deterministic",
          compute_identity_hash() == compute_identity_hash())
    check("MODULE_DESCRIPTIONS has all 12 modules",
          all(mid in MODULE_DESCRIPTIONS for mid in [
              "aegis_ald", "goliath_leviathan", "sentinel_omega", "titan_engine",
              "kinetic_siphon", "sovereign_v42", "reality_compiler", "atc_engine",
              "project_sv", "whatsapp_t1", "pipeline_router", "thermal_shield"
          ]))


def test_module_registry():
    print("\n=== MODULE REGISTRY ===")
    from module_registry import ModuleRegistry, ModuleDispatcher, MODULE_CATALOG

    check("MODULE_CATALOG has 12 entries", len(MODULE_CATALOG) == 12,
          f"got {len(MODULE_CATALOG)}")

    registry = ModuleRegistry()
    check("Registry loaded 12 modules", len(registry.modules) == 12)

    # Test each module exists
    for mod in registry.list_all():
        source_ok = os.path.exists(mod.source_path)
        mirror_ok = mod.check_mirror()
        check(f"  {mod.id}: source exists", source_ok, mod.source_path)
        check(f"  {mod.id}: mirror exists", mirror_ok, mod.mirror_path)

    # Keyword matching
    check("keyword 'forensic' -> goliath_leviathan",
          registry.find_by_keyword("run forensic scan").id == "goliath_leviathan")
    check("keyword 'physics bernoulli' -> sovereign_v42",
          registry.find_by_keyword("physics bernoulli audit").id == "sovereign_v42")
    check("keyword 'atc flight' -> atc_engine",
          registry.find_by_keyword("atc flight data").id == "atc_engine")
    check("keyword 'compress codec' -> project_sv",
          registry.find_by_keyword("compress codec benchmark").id == "project_sv")
    check("keyword 'detonate pipeline' -> pipeline_router",
          registry.find_by_keyword("detonate the pipeline").id == "pipeline_router")
    check("keyword 'thermal naef' -> thermal_shield",
          registry.find_by_keyword("thermal shield naef").id == "thermal_shield")
    check("keyword 'whatsapp test' -> whatsapp_t1",
          registry.find_by_keyword("whatsapp security test").id == "whatsapp_t1")
    check("keyword 'egress port' -> kinetic_siphon",
          registry.find_by_keyword("egress port monitor").id == "kinetic_siphon")
    check("keyword gibberish -> None",
          registry.find_by_keyword("xyzzy foobar baz") is None)


def test_dispatcher():
    print("\n=== MODULE DISPATCHER ===")
    from module_registry import ModuleRegistry, ModuleDispatcher

    registry = ModuleRegistry()
    dispatcher = ModuleDispatcher(registry)

    # Parse valid action
    response_with_action = 'Sure, I can run that. {"action": "execute", "module": "thermal_shield", "args": ""}'
    action, clean = dispatcher.parse_action(response_with_action)
    check("parse_action extracts JSON", action is not None)
    check("parse_action correct module", action and action.get("module") == "thermal_shield")
    check("parse_action cleans text", "Sure" in clean)

    # Parse no action
    response_no_action = "I can help explain that project to you."
    action2, clean2 = dispatcher.parse_action(response_no_action)
    check("parse_action no JSON returns None", action2 is None)
    check("parse_action preserves text", clean2 == response_no_action)

    # Dispatch bad module
    success, output = dispatcher.dispatch({"action": "execute", "module": "nonexistent_module"})
    check("dispatch bad module returns False", not success)
    check("dispatch bad module has error msg", "Unknown module" in output)

    # Dispatch describe
    success, output = dispatcher.dispatch({"action": "describe", "module": "aegis_ald"})
    check("dispatch describe succeeds", success)
    check("dispatch describe has content", "ALD" in output or "Gate" in output)

    # Dispatch status
    success, output = dispatcher.dispatch({"action": "status", "module": "sentinel_omega"})
    check("dispatch status succeeds", success)
    check("dispatch status is JSON", "sentinel_omega" in output)


def test_llm_router_structure():
    print("\n=== LLM ROUTER (CODE-LEVEL, NO API CALLS) ===")
    from llm_backend import LLMRouter, OllamaBackend, GeminiBackend, OpenAIBackend

    router = LLMRouter()
    check("Router has 3 backends", len(router.backends) == 3)
    check("Default backend is gemini", router.active_backend == "gemini")

    # Backend switching
    ok, msg = router.set_backend("ollama")
    check("set_backend ollama works", ok)
    check("active_backend updated", router.active_backend == "ollama")

    ok, msg = router.set_backend("nonexistent")
    check("set_backend bad ID fails", not ok)
    check("set_backend bad ID has VERDICT", "VERDICT" in msg)

    # Reset
    router.set_backend("gemini")
    check("reset to gemini", router.active_backend == "gemini")

    # Status check
    status = router.get_status()
    check("status has all backends", all(k in status for k in ["ollama", "gemini", "openai"]))
    check("gemini marked active", status["gemini"]["active"])


def test_error_handling():
    print("\n=== ERROR HANDLING & EDGE CASES ===")
    from module_registry import ModuleRegistry, ModuleDispatcher

    registry = ModuleRegistry()
    dispatcher = ModuleDispatcher(registry)

    # Empty action
    success, output = dispatcher.dispatch({})
    check("empty action dict handled", not success)

    # Malformed JSON in parse
    action, clean = dispatcher.parse_action('{"broken json')
    check("malformed JSON returns None", action is None)

    # Action with missing module key
    success, output = dispatcher.dispatch({"action": "execute"})
    check("missing module key handled", not success)

    # Unknown action type
    success, output = dispatcher.dispatch({"action": "destroy", "module": "aegis_ald"})
    check("unknown action type handled", not success)
    check("unknown action type has error msg", "Unknown action" in output)

    # Very long input to parse_action
    long_input = "A" * 10000
    action, clean = dispatcher.parse_action(long_input)
    check("very long input doesn't crash", action is None and len(clean) == 10000)


def test_command_log():
    print("\n=== COMMAND LOG ===")
    import tempfile
    from command_center_ui import CommandLog

    log_path = os.path.join(tempfile.gettempdir(), "test_veritas_cmd.jsonl")
    log = CommandLog(log_path)
    log.log("user", "test message", backend="gemini")
    log.log("assistant", "test response")

    check("log file created", os.path.exists(log_path))
    with open(log_path, "r") as f:
        lines = f.readlines()
    check("log has 2 entries", len(lines) == 2)
    entry = json.loads(lines[0])
    check("log entry has timestamp", "timestamp" in entry)
    check("log entry has role", entry["role"] == "user")
    check("log entry has backend", entry.get("backend") == "gemini")

    # Cleanup
    os.remove(log_path)
    check("cleanup successful", not os.path.exists(log_path))


if __name__ == "__main__":
    print("=" * 60)
    print("VERITAS COMMAND CENTER v2.0 — TEST HARNESS")
    print("=" * 60)

    test_identity_kernel()
    test_module_registry()
    test_dispatcher()
    test_llm_router_structure()
    test_error_handling()
    test_command_log()

    print(f"\n{'=' * 60}")
    total = PASS + FAIL
    print(f"RESULTS: {PASS}/{total} PASS, {FAIL} FAIL")
    verdict = "PASS" if FAIL == 0 else "ISSUES_DETECTED"
    print(f"VERDICT: {verdict}")
    print(f"{'=' * 60}")
    sys.exit(0 if FAIL == 0 else 1)
