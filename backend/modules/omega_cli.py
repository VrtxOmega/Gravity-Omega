"""
Omega Claw — Interactive Agent CLI
====================================
This IS Omega. The offline autonomous agent.

When you're offline, this is your coding assistant.
It runs on local Ollama, thinks with qwen2.5:7b,
and every action passes through VERITAS gates.

Usage:
    python omega_cli.py                    # Interactive REPL
    python omega_cli.py --task "do X"      # Single task mode
    python omega_cli.py --assess file.py   # Quick gate assessment
    python omega_cli.py --status           # Daemon status
    python omega_cli.py --audit            # View audit trail
    python omega_cli.py --watch DIR        # Start daemon on directory

Inside this workspace: Omega is UNBOUND.
Gates govern the EXIT, not creation.
"""

import argparse
import io
import json
import logging
import os
import sys
import time
from pathlib import Path

# Force UTF-8 on Windows to avoid cp1252 Unicode crashes
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add project root
sys.path.insert(0, str(Path(__file__).parent))

from omega_agent import OmegaAgent, DEFAULT_MODEL, OLLAMA_URL
from omega_claw_daemon import OmegaClawDaemon
from gate_pipeline import run_gate_pipeline
from risk_calibrator import calibrate, SOVEREIGN, SHIELDED, CONTAINED
from audit_ledger import AuditLedger
from omega_soul import OmegaSoul


# ══════════════════════════════════════════════════════════════
# COLORS (works on Windows Terminal / ANSI)
# ══════════════════════════════════════════════════════════════

class C:
    GOLD    = "\033[38;2;207;181;59m"
    WHITE   = "\033[97m"
    BLACK   = "\033[90m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    CYAN    = "\033[96m"
    DIM     = "\033[2m"
    BOLD    = "\033[1m"
    RESET   = "\033[0m"


# ══════════════════════════════════════════════════════════════
# BANNER
# ══════════════════════════════════════════════════════════════

BANNER = f"""
{C.GOLD}{C.BOLD}
    ╔══════════════════════════════════════════════════════╗
    ║                                                      ║
    ║      ██████╗ ███╗   ███╗███████╗ ██████╗  █████╗     ║
    ║     ██╔═══██╗████╗ ████║██╔════╝██╔════╝ ██╔══██╗    ║
    ║     ██║   ██║██╔████╔██║█████╗  ██║  ███╗███████║    ║
    ║     ██║   ██║██║╚██╔╝██║██╔══╝  ██║   ██║██╔══██║    ║
    ║     ╚██████╔╝██║ ╚═╝ ██║███████╗╚██████╔╝██║  ██║    ║
    ║      ╚═════╝ ╚═╝     ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝    ║
    ║                                                      ║
    ║          ██████╗██╗      █████╗ ██╗    ██╗            ║
    ║         ██╔════╝██║     ██╔══██╗██║    ██║            ║
    ║         ██║     ██║     ███████║██║ █╗ ██║            ║
    ║         ██║     ██║     ██╔══██║██║███╗██║            ║
    ║         ╚██████╗███████╗██║  ██║╚███╔███╔╝            ║
    ║          ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝            ║
    ║                                                      ║
    ║       {C.WHITE}VERITAS-Gated Autonomous Agent{C.GOLD}                ║
    ║       {C.DIM}{C.WHITE}Offline · Local · Sovereign{C.GOLD}{C.BOLD}                  ║
    ║                                                      ║
    ╚══════════════════════════════════════════════════════╝
{C.RESET}"""


# ══════════════════════════════════════════════════════════════
# ENVELOPE DISPLAY
# ══════════════════════════════════════════════════════════════

_ENVELOPE_COLORS = {
    SOVEREIGN: C.GREEN,
    SHIELDED:  C.YELLOW,
    CONTAINED: C.RED,
}

_ENVELOPE_ICONS = {
    SOVEREIGN: "■",
    SHIELDED:  "▲",
    CONTAINED: "●",
}


def _format_envelope(envelope: str) -> str:
    color = _ENVELOPE_COLORS.get(envelope, C.WHITE)
    icon = _ENVELOPE_ICONS.get(envelope, "?")
    return f"{color}{C.BOLD}{icon} {envelope}{C.RESET}"


def _format_gate(gate: str, verdict: str) -> str:
    if verdict == "PASS":
        return f"  {C.GREEN}✓ {gate}{C.RESET}"
    elif verdict == "WARN":
        return f"  {C.YELLOW}⚠ {gate}{C.RESET}"
    else:
        return f"  {C.RED}✗ {gate}{C.RESET}"


# ══════════════════════════════════════════════════════════════
# ASSESS COMMAND
# ══════════════════════════════════════════════════════════════

def cmd_assess(filepath: str):
    """Run gate pipeline on a file and display results."""
    path = Path(filepath).resolve()
    if not path.exists():
        print(f"{C.RED}File not found: {path}{C.RESET}")
        return

    print(f"\n{C.GOLD}━━━ OMEGA CLAW ASSESSMENT ━━━{C.RESET}")
    print(f"{C.DIM}File: {path}{C.RESET}\n")

    content = path.read_text(encoding="utf-8", errors="replace")
    gate_results, file_hash = run_gate_pipeline(content, str(path))
    report = calibrate(gate_results)

    # Display gates
    for gr in gate_results:
        line = _format_gate(gr.gate, gr.verdict)
        if gr.detail:
            line += f" {C.DIM}— {gr.detail[:80]}{C.RESET}"
        print(line)

    # Display envelope
    print(f"\n  {C.BOLD}Envelope:{C.RESET}    {_format_envelope(report.envelope)}")
    print(f"  {C.BOLD}Risk Score:{C.RESET}  {report.risk_score}")
    print(f"  {C.BOLD}File Hash:{C.RESET}   {C.DIM}{file_hash[:16]}...{C.RESET}")

    # Log to audit
    ledger = AuditLedger()
    ledger.append(
        filename=path.name,
        file_hash=file_hash,
        gate_verdicts=[g.to_dict() for g in gate_results],
        envelope=report.envelope,
        risk_score=report.risk_score,
        metadata={"full_path": str(path), "source": "cli"},
    )
    print(f"\n{C.DIM}Logged to audit ledger.{C.RESET}")


# ══════════════════════════════════════════════════════════════
# STATUS COMMAND
# ══════════════════════════════════════════════════════════════

def cmd_status():
    """Show daemon and system status."""
    print(f"\n{C.GOLD}━━━ OMEGA CLAW STATUS ━━━{C.RESET}\n")

    # Check Ollama
    from omega_agent import OllamaClient
    client = OllamaClient()
    ollama_ok = client.is_available()

    print(f"  Ollama:     {'🟢 Online' if ollama_ok else '🔴 Offline'}")

    # Audit ledger
    ledger = AuditLedger()
    count = ledger.count
    valid, checked, fail = ledger.verify_chain()
    chain_status = f"{C.GREEN}INTACT{C.RESET}" if valid else f"{C.RED}BROKEN at #{fail}{C.RESET}"

    print(f"  Assessments: {count}")
    print(f"  Audit Chain: {chain_status} ({checked} records verified)")

    # Last 3 assessments
    if count > 0:
        print(f"\n  {C.BOLD}Recent Assessments:{C.RESET}")
        for rec in ledger.read_last_n(3):
            env_str = _format_envelope(rec.envelope)
            print(f"    {env_str}  {rec.filename}  (risk={rec.risk_score})")


# ══════════════════════════════════════════════════════════════
# AUDIT COMMAND
# ══════════════════════════════════════════════════════════════

def cmd_audit(count: int = 10):
    """Show audit trail."""
    print(f"\n{C.GOLD}━━━ OMEGA CLAW AUDIT TRAIL ━━━{C.RESET}\n")

    ledger = AuditLedger()
    valid, checked, fail = ledger.verify_chain()
    chain_status = f"{C.GREEN}CHAIN INTACT{C.RESET}" if valid else f"{C.RED}CHAIN BROKEN at #{fail}{C.RESET}"
    print(f"  {chain_status} ({checked} records)\n")

    records = ledger.read_last_n(count)
    if not records:
        print(f"  {C.DIM}No assessments yet.{C.RESET}")
        return

    for rec in records:
        env_str = _format_envelope(rec.envelope)
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(rec.timestamp))
        print(f"  {C.DIM}{ts}{C.RESET}  {env_str}  {rec.filename}  "
              f"{C.DIM}risk={rec.risk_score}  seal={rec.seal_hash[:12]}...{C.RESET}")


# ══════════════════════════════════════════════════════════════
# WATCH COMMAND
# ══════════════════════════════════════════════════════════════

def cmd_watch(directory: str):
    """Start the daemon watching a directory."""
    path = Path(directory).resolve()
    if not path.is_dir():
        print(f"{C.RED}Not a directory: {path}{C.RESET}")
        return

    print(f"\n{C.GOLD}━━━ OMEGA CLAW DAEMON ━━━{C.RESET}")
    print(f"Watching: {path}")
    print(f"Forge trigger: {C.BOLD}# OMEGA: COMPILE{C.RESET}")
    print(f"Press Ctrl+C to stop.\n")

    def on_assessment(filepath, report):
        env_str = _format_envelope(report.envelope)
        print(f"  {C.GOLD}FORGE{C.RESET} {env_str}  {os.path.basename(filepath)}  "
              f"risk={report.risk_score}")

    daemon = OmegaClawDaemon(
        watch_dirs=[str(path)],
        on_assessment=on_assessment,
    )
    daemon.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        daemon.stop()
        print(f"\n{C.DIM}Daemon stopped.{C.RESET}")


# ══════════════════════════════════════════════════════════════
# INTERACTIVE REPL (THE AGENT)
# ══════════════════════════════════════════════════════════════

def cmd_repl(model: str = DEFAULT_MODEL, workspace: str = ""):
    """Interactive agent REPL. This IS Omega."""
    print(BANNER)

    # Check Ollama
    from omega_agent import OllamaClient
    client = OllamaClient(model=model)
    if not client.is_available():
        print(f"{C.RED}ERROR: Ollama is not running.{C.RESET}")
        print(f"Start it with: {C.BOLD}ollama serve{C.RESET}")
        print(f"Then pull the model: {C.BOLD}ollama pull {model}{C.RESET}")
        return

    ws = workspace or os.getcwd()

    # Build repo map (Aider pattern)
    from repo_map import RepoMap
    repo = RepoMap(ws)
    file_count = repo.scan()

    print(f"  {C.GREEN}Ollama:{C.RESET}    Online ({model})")
    print(f"  {C.GREEN}Workspace:{C.RESET} {ws}")
    print(f"  {C.GREEN}Repo Map:{C.RESET}  {file_count} Python files indexed")
    print(f"  {C.GREEN}Envelope:{C.RESET}  {_format_envelope(SOVEREIGN)}")
    print()
    print(f"  {C.DIM}Type a task and press Enter. Omega will plan, act, and verify.")
    print(f"  Commands:  /assess <file>  /status  /audit  /map  /quit{C.RESET}")
    print()

    # Callbacks for streaming display
    def on_thought(thought: str):
        if thought:
            print(f"  {C.CYAN}THOUGHT:{C.RESET} {thought[:120]}")

    def on_action(action: str, params: dict):
        param_str = json.dumps(params, default=str)[:80]
        print(f"  {C.GOLD}ACTION:{C.RESET}  {action} {C.DIM}{param_str}{C.RESET}")

    agent = OmegaAgent(
        model=model,
        workspace=ws,
        antigravity_root=os.path.expanduser("~/.gemini/antigravity/scratch"),
        on_thought=on_thought,
        on_action=on_action,
    )

    # Inject repo map context
    agent.set_repo_map(repo.get_context())

    while True:
        try:
            user_input = input(f"{C.GOLD}{C.BOLD}Ω ▸ {C.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C.DIM}Omega signing off.{C.RESET}")
            break

        if not user_input:
            continue

        # Slash commands
        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()

            if cmd == "/quit" or cmd == "/exit":
                print(f"{C.DIM}Omega signing off.{C.RESET}")
                break
            elif cmd == "/assess" and len(parts) > 1:
                cmd_assess(parts[1])
            elif cmd == "/status":
                cmd_status()
            elif cmd == "/audit":
                cmd_audit()
            elif cmd == "/map":
                # Re-scan and display repo map
                file_count = repo.scan()
                print(f"\n{C.GOLD}━━━ REPO MAP ({file_count} files) ━━━{C.RESET}\n")
                print(repo.get_context())
                # Update agent context
                agent.set_repo_map(repo.get_context())
            elif cmd == "/help":
                print(f"  {C.BOLD}/assess <file>{C.RESET}  — Run gate pipeline on a file")
                print(f"  {C.BOLD}/status{C.RESET}         — Show daemon status")
                print(f"  {C.BOLD}/audit{C.RESET}          — View audit trail")
                print(f"  {C.BOLD}/map{C.RESET}            — Re-scan and show repo map")
                print(f"  {C.BOLD}/quit{C.RESET}           — Exit Omega")
            else:
                print(f"{C.DIM}Unknown command. Type /help{C.RESET}")
            continue

        # Agent task
        print(f"\n{C.GOLD}━━━ OMEGA WORKING ━━━{C.RESET}\n")
        result = agent.run(user_input)
        print(f"\n{C.GOLD}━━━ RESULT ━━━{C.RESET}")
        print(f"{C.WHITE}{result}{C.RESET}\n")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    # Enable ANSI on Windows
    if sys.platform == "win32":
        subprocess.run("")

    parser = argparse.ArgumentParser(
        description="Omega Claw — VERITAS-Gated Autonomous Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python omega_cli.py                     Interactive agent (REPL)
  python omega_cli.py --task "fix bug"    Single task, then exit
  python omega_cli.py --assess app.py     Gate-check a file
  python omega_cli.py --status            Show system status
  python omega_cli.py --audit             View audit trail
  python omega_cli.py --watch ./src       Watch directory for changes
""",
    )
    parser.add_argument("--task", type=str, help="Run a single task and exit")
    parser.add_argument("--assess", type=str, help="Assess a file through gate pipeline")
    parser.add_argument("--status", action="store_true", help="Show system status")
    parser.add_argument("--audit", action="store_true", help="Show audit trail")
    parser.add_argument("--audit-count", type=int, default=10, help="Number of audit records")
    parser.add_argument("--watch", type=str, help="Watch a directory for changes")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help=f"Ollama model (default: {DEFAULT_MODEL})")
    parser.add_argument("--workspace", type=str, default="", help="Workspace root directory")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.assess:
        cmd_assess(args.assess)
    elif args.status:
        cmd_status()
    elif args.audit:
        cmd_audit(args.audit_count)
    elif args.watch:
        cmd_watch(args.watch)
    elif args.task:
        # Single task mode
        print(BANNER)
        agent = OmegaAgent(
            model=args.model,
            workspace=args.workspace or os.getcwd(),
        )
        if not agent.is_ollama_available:
            print(f"{C.RED}Ollama is not running. Start it first.{C.RESET}")
            sys.exit(1)
        print(f"{C.GOLD}━━━ TASK: {args.task} ━━━{C.RESET}\n")
        result = agent.run(args.task)
        print(f"\n{C.GOLD}━━━ RESULT ━━━{C.RESET}")
        print(result)
    else:
        # Interactive REPL
        cmd_repl(model=args.model, workspace=args.workspace)


if __name__ == "__main__":
    main()
