/**
 * OMEGA IPC v4.1 â€” Typed Module Communication Layer
 *
 * Routes module execution through the Python backend bridge.
 * UUID-traced calls with LangChain-inspired structured responses.
 */
'use strict';

const crypto = require('crypto');

class AgentAction {
    constructor(tool, toolInput, log) {
        this.tool = tool;
        this.toolInput = toolInput;
        this.log = log || '';
        this.id = crypto.randomUUID();
    }
    toJSON() {
        return { type: 'AgentAction', id: this.id, tool: this.tool, toolInput: this.toolInput, log: this.log };
    }
}

class AgentFinish {
    constructor(returnValues, log) {
        this.returnValues = returnValues;
        this.log = log || '';
    }
    toJSON() {
        return { type: 'AgentFinish', returnValues: this.returnValues, log: this.log };
    }
}

class ModuleResult {
    constructor({ moduleId, success, data, error, duration }) {
        this.moduleId = moduleId;
        this.success = success;
        this.data = data;
        this.error = error;
        this.duration = duration;
        this.timestamp = new Date().toISOString();
    }
    toJSON() {
        return {
            type: 'ModuleResult', moduleId: this.moduleId,
            success: this.success, data: this.data, error: this.error,
            duration: this.duration, timestamp: this.timestamp,
        };
    }
}

class OmegaIPC {
    constructor(bridge) {
        this.bridge = bridge;
        this._callLog = [];
        this._maxLog = 200;
    }

    async executeModule(moduleId, args = {}) {
        const traceId = crypto.randomUUID();
        const startTime = Date.now();

        this._log('EXECUTE', moduleId, traceId, args);

        try {
            const response = await this.bridge.post(`/api/modules/${moduleId}/run`, {
                args,
                trace_id: traceId,
            });

            const duration = Date.now() - startTime;
            const result = new ModuleResult({
                moduleId, success: true, data: response, duration,
            });

            this._log('RESULT', moduleId, traceId, { success: true, duration });
            return result;
        } catch (err) {
            const duration = Date.now() - startTime;
            const result = new ModuleResult({
                moduleId, success: false, error: err.message, duration,
            });

            this._log('ERROR', moduleId, traceId, { error: err.message, duration });
            return result;
        }
    }

    async describeModule(moduleId) {
        try {
            const response = await this.bridge.get(`/api/modules/${moduleId}/describe`);
            return new ModuleResult({ moduleId, success: true, data: response });
        } catch (err) {
            return new ModuleResult({ moduleId, success: false, error: err.message });
        }
    }

    getCallLog(n = 50) {
        return this._callLog.slice(-n);
    }

    _log(action, moduleId, traceId, data) {
        this._callLog.push({
            action, moduleId, traceId, data,
            ts: new Date().toISOString(),
        });
        if (this._callLog.length > this._maxLog) {
            this._callLog = this._callLog.slice(-this._maxLog);
        }
    }
}

module.exports = { OmegaIPC, AgentAction, AgentFinish, ModuleResult };
