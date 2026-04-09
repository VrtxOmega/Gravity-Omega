import sys
import re

target_file = 'c:/Veritas_Lab/gravity-omega-v2/omega/omega_agent.js'
with open(target_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Imports
if "const { SwarmManager }" not in content:
    content = content.replace(
        "const { ToolExecutor, TOOL_REGISTRY, SAFETY } = require('./omega_tools');",
        "const { ToolExecutor, TOOL_REGISTRY, SAFETY } = require('./omega_tools');\nconst { SwarmManager } = require('./omega_swarm');"
    )

# 2. Constructor
if "this.swarm = new" not in content:
    content = content.replace(
        "this._pendingProposals = new Map();",
        "this._pendingProposals = new Map();\n        this.swarm = new SwarmManager(this, 3);"
    )

# 3. spawnSubAgent replacement
# We know the function starts roughly around line 2781.
new_spawn = """    // ── Swarm Agents (Component 2) ────────────────────────────────────────────────
    async spawnSubAgent(task) {
        try {
            // omega_agent handles SwarmManager instantiation
            const swarmResult = await this.swarm.spawn(task, OmegaAgent);
            
            if (swarmResult.status !== 'COMPLETED') {
                return { error: `Sub-agent ${swarmResult.id} failed: ${swarmResult.result}` };
            }
            
            return {
                result: swarmResult.result,
                subId: swarmResult.id
            };
        } catch (e) {
            return { error: `Swarm spawn crashed: ${e.message}` };
        }
    }"""

# A simple string search for the block replacing everything from 'async spawnSubAgent(task) {' to the end of the method before 'async executeAllPending() {'
pattern = re.compile(r"    // ── 子 Agents ──.*?async spawnSubAgent\(task\) \{.*?    async executeAllPending\(\) \{", re.DOTALL)

if "swarm.spawn" not in content:
    content = pattern.sub(new_spawn + "\n\n    async executeAllPending() {", content)

with open(target_file, 'w', encoding='utf-8') as f:
    f.write(content)
print("omega_agent.js refactored for SwarmManager.")
