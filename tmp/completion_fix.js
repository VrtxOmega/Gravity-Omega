const fs = require('fs');
let content = fs.readFileSync('c:/Veritas_Lab/gravity-omega-v2/omega/omega_agent.js', 'utf8');

// The helper method to be inserted after _geminiGenerate
const regexMethod = /    async _geminiGenerate\(messages\) \{/;
const replacementMethod = `    /**
     * v4.3.29: Priority 4 - Explicit Completion Detection
     */
    async _checkCompletion(objective, llmResponse) {
        if (!this._stepLog || this._stepLog.length === 0) return 'COMPLETE';
        
        try {
            const summary = this._stepLog.map(s => \`- [\${s.tool}] \${String(s.args || '').substring(0, 80)}\`).join('\\n');
            const prompt = [
                { role: 'system', content: 'You are an Overseer evaluating if an agent has completely resolved an objective.\\nReturn exactly ONE WORD: COMPLETE, INCOMPLETE, or BLOCKED.' },
                { role: 'user', content: \`OBJECTIVE:\\n\${objective}\\n\\nTOOLS USED:\\n\${summary}\\n\\nAGENT RESPONSE:\\n\${llmResponse}\\n\\nHas the agent fully satisfied the objective? Answer exactly COMPLETE, INCOMPLETE, or BLOCKED.\` }
            ];

            console.log('[OVERSEER] Verifying explicit completion...');
            this._emitProgress({ phase: 'thinking', label: 'Verifying Completion...' });
            
            const result = await this._geminiGenerate(prompt);
            const upper = (result || '').toUpperCase().trim();
            console.log('[OVERSEER] Verdict:', upper);
            if (upper.includes('INCOMPLETE')) return 'INCOMPLETE';
            if (upper.includes('BLOCKED')) return 'BLOCKED';
            return 'COMPLETE';
        } catch (err) {
            console.error('[OVERSEER] checkCompletion failed:', err.message);
            return 'COMPLETE'; 
        }
    }

    async _geminiGenerate(messages) {`;

content = content.replace(regexMethod, replacementMethod);

const regexLoop1 = /                    this\._exitReason = 'TASK_COMPLETE';\n                    const cleanMsg = this\._sanitizeForChat\(parsed\.content\);\n                    finalResponse = \{ type: 'chat', message: cleanMsg, steps: this\._stepLog\.length, stepLog: this\._stepLog, exitReason: 'TASK_COMPLETE' \};\n                    break;/;

const replacementLoop1 = `                    // v4.3: Priority 4 - Explicit Completion Detection
                    const completionState = await this._checkCompletion(text, parsed.content);
                    if (completionState === 'INCOMPLETE' && iteration < 15) {
                        console.log('[OVERSEER] Task evaluated as INCOMPLETE. Forcing continuation.');
                        messages.push({ role: 'assistant', content: llmResponse });
                        messages.push({ role: 'user', content: '[OVERSEER CHECK FAILED]: Your task is INCOMPLETE according to the supervisor. You have not fully resolved the objective.\\nReview your progress and continue executing missing tool steps via VTP blocks. Do not explain, just execute.' });
                        continue;
                    } else if (completionState === 'BLOCKED') {
                        console.log('[OVERSEER] Task evaluated as BLOCKED. Halting.');
                        this._exitReason = 'BLOCKED_BY_ENVIRONMENT';
                        const cleanMsg = this._sanitizeForChat(parsed.content);
                        finalResponse = { type: 'chat', message: cleanMsg + "\\n\\n**STATUS: BLOCKED** - Task suspended for user input.", steps: this._stepLog.length, stepLog: this._stepLog, exitReason: 'BLOCKED' };
                        break;
                    }

                    this._exitReason = 'TASK_COMPLETE';
                    const cleanMsg2 = this._sanitizeForChat(parsed.content);
                    finalResponse = { type: 'chat', message: cleanMsg2, steps: this._stepLog.length, stepLog: this._stepLog, exitReason: 'TASK_COMPLETE' };
                    break;`;

content = content.replace(regexLoop1, replacementLoop1);


const regexLoop2 = /                    finalResponse = \{ type: 'chat', message: this\._sanitizeForChat\(parsed\.content\), steps: this\._stepLog\.length, stepLog: this\._stepLog, exitReason: 'TASK_COMPLETE' \};\n                    break;/;

const replacementLoop2 = `                    // v4.3: Priority 4 - Explicit Completion Detection
                    const completionStateC = await this._checkCompletion(messages[0] ? messages[0].content : 'Unknown Task', parsed.content);
                    if (completionStateC === 'INCOMPLETE' && iteration < 15) {
                        console.log('[OVERSEER] Task evaluated as INCOMPLETE. Forcing continuation.');
                        messages.push({ role: 'assistant', content: llmResponse });
                        messages.push({ role: 'user', content: '[OVERSEER CHECK FAILED]: Your task is INCOMPLETE according to the supervisor. You have not fully resolved the objective.\\nReview your progress and continue executing missing tool steps via VTP blocks. Do not explain, just execute.' });
                        continue;
                    } else if (completionStateC === 'BLOCKED') {
                        console.log('[OVERSEER] Task evaluated as BLOCKED. Halting.');
                        this._exitReason = 'BLOCKED_BY_ENVIRONMENT';
                        finalResponse = { type: 'chat', message: this._sanitizeForChat(parsed.content) + "\\n\\n**STATUS: BLOCKED** - Task suspended for user input.", steps: this._stepLog.length, stepLog: this._stepLog, exitReason: 'BLOCKED' };
                        break;
                    }

                    finalResponse = { type: 'chat', message: this._sanitizeForChat(parsed.content), steps: this._stepLog.length, stepLog: this._stepLog, exitReason: 'TASK_COMPLETE' };
                    break;`;

content = content.replace(regexLoop2, replacementLoop2);

fs.writeFileSync('c:/Veritas_Lab/gravity-omega-v2/omega/omega_agent.js', content, 'utf8');
console.log('Explicit completion logic successfully written.');
