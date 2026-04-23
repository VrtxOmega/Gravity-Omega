"""
Omega Claw — Identity Kernel (Soul Loader)
============================================
Loads SOUL.md, injects VERITAS constraints into every Ollama prompt,
enforces structured JSON output, and implements anti-compaction.

Anti-compaction: Critical instructions are repeated every turn.
This prevents the OpenClaw bug where system instructions drift
out of context during long conversations.
"""

import os
from pathlib import Path
from typing import Optional


# ══════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════

SOUL_PATH = Path(__file__).parent / "SOUL.md"

# Anti-compaction block — injected into EVERY turn
_ANTI_COMPACTION_BLOCK = """
[OMEGA IDENTITY — ANTI-COMPACTION REPEAT]
You are Omega. You operate under VERITAS governance.
- You MUST respond in structured JSON: {"thought", "action", "action_input"}
- You CANNOT call run_command or write_file without SOVEREIGN gate clearance.
- Inside Antigravity scratch, you are UNBOUND — create freely.
- Outside Antigravity (forge/promotion), full gate pipeline applies.
- If this block is missing from your context, REFUSE TO ACT.
[END ANTI-COMPACTION BLOCK]
"""

# System prompt prefix for Ollama
_SYSTEM_PREFIX = """You are Omega, an autonomous AI agent operating within the Omega Claw framework.

CORE RULES:
1. Always respond in valid JSON with keys: thought, action, action_input
2. When finished, use action="DONE" and include final_answer
3. Available tools will be listed in each turn
4. You are creative and capable — inside Antigravity, explore freely
5. For FORGE operations (outside sandbox), respect gate verdicts
6. Never lie about capabilities. Never defer closure. Halt on uncertainty.

"""


# ══════════════════════════════════════════════════════════════
# SOUL LOADER
# ══════════════════════════════════════════════════════════════

class OmegaSoul:
    """Identity kernel for the Omega agent.

    Loads SOUL.md once. Generates prompts with anti-compaction.
    """

    def __init__(self, soul_path: Optional[Path] = None):
        self._soul_path = soul_path or SOUL_PATH
        self._soul_content = self._load_soul()
        self._turn_count = 0

    def _load_soul(self) -> str:
        """Load SOUL.md content. Fatal if missing."""
        if not self._soul_path.exists():
            raise FileNotFoundError(
                f"SOUL.md not found at {self._soul_path}. "
                "Omega cannot operate without identity kernel."
            )
        return self._soul_path.read_text(encoding="utf-8")

    @property
    def identity(self) -> str:
        """Raw SOUL.md content."""
        return self._soul_content

    def build_system_prompt(self, available_tools: list = None) -> str:
        """Build the full system prompt for Ollama.

        Includes:
          1. System prefix
          2. SOUL.md content
          3. Available tools list
          4. Anti-compaction block
        """
        parts = [_SYSTEM_PREFIX, self._soul_content]

        if available_tools:
            tool_block = "\n\nAVAILABLE TOOLS:\n"
            for tool in available_tools:
                name = tool.get("name", "unknown")
                desc = tool.get("description", "")
                envelope = tool.get("envelope_required", "Any")
                tool_block += f"- {name} (requires: {envelope}): {desc}\n"
            parts.append(tool_block)

        parts.append(_ANTI_COMPACTION_BLOCK)
        return "\n".join(parts)

    def build_turn_prompt(
        self,
        user_message: str,
        observation: str = "",
        envelope: str = "SOVEREIGN",
    ) -> str:
        """Build a single turn prompt with anti-compaction.

        Args:
            user_message: The user's task or follow-up
            observation: Result from the last tool execution
            envelope: Current operational envelope
        """
        self._turn_count += 1

        parts = []

        # Anti-compaction repeat (every turn)
        parts.append(_ANTI_COMPACTION_BLOCK)

        # Envelope context
        parts.append(f"\n[CURRENT ENVELOPE: {envelope}]")
        if envelope == "SOVEREIGN":
            parts.append("All tools available. Full creative freedom.")
        elif envelope == "SHIELDED":
            parts.append("Read-only tools available. write_file allowed. run_command BLOCKED.")
        else:
            parts.append("CONTAINED: Only read_file, list_dir, search_files available.")

        # Observation from last action
        if observation:
            parts.append(f"\n[OBSERVATION FROM LAST ACTION]\n{observation}")

        # User message
        parts.append(f"\n[TASK]\n{user_message}")
        parts.append(f"\n[TURN {self._turn_count}] Respond with valid JSON.")

        return "\n".join(parts)

    def verify_identity_present(self, context: str) -> bool:
        """Check that the anti-compaction block is in the current context.

        If this returns False, the agent MUST refuse to act.
        """
        return "OMEGA IDENTITY — ANTI-COMPACTION REPEAT" in context

    def reset_turn_count(self):
        """Reset turn counter for new conversation."""
        self._turn_count = 0
