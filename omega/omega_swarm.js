'use strict';

const crypto = require('crypto');
const os = require('os');

class WorkerNode {
    constructor(id, task, parentAgent) {
        this.id = id;
        this.task = task;
        this.parentAgent = parentAgent;
        this.status = 'PENDING';
        this.prefix = `[SUB-${this.id}]`;
        // Create an isolated subAgent instance
        // Assuming OmegaAgent is loaded via require in parent context and passed, or initialized.
    }

    async execute(OmegaAgentClass) {
        this.status = 'RUNNING';
        let resultMessage = '';
        
        try {
            const subAgent = new OmegaAgentClass({
                intent: this.task,
                is_sub_agent: true
            });
            
            // Proxy emissions back to parent
            subAgent._emitProgress = (evt) => {
                const prefixedMsg = evt.label ? `${this.prefix} ${evt.label}` : evt.label;
                this.parentAgent._emitProgress({ ...evt, label: prefixedMsg });
            };

            const subResult = await subAgent.processRequest(this.task);
            
            resultMessage = subResult.message || JSON.stringify(subResult);
            this.status = 'COMPLETED';

        } catch (error) {
            this.status = 'FAILED';
            resultMessage = `CRASH: ${error.message}`;
            this.parentAgent._emitProgress({ label: `${this.prefix} Crash: ${error.message}`, phase: 'error' });
        }

        return { id: this.id, task: this.task, status: this.status, result: resultMessage };
    }
}

class SwarmManager {
    constructor(parentAgent, maxConcurrent = 3) {
        this.parentAgent = parentAgent;
        this.maxConcurrent = maxConcurrent;
        this.activeWorkers = new Map();
        this.queue = [];
    }

    async checkVramCapacity() {
        // Mocking VRAM constraint or returning PS memory utilization.
        // In local node processes, we can check OS free memory.
        const freeMemGB = os.freemem() / (1024 ** 3);
        // If system free memory drops below 4GB, or if Ollama is actively saturated.
        if (freeMemGB < 4.0) {
            return false;
        }
        return true;
    }

    async spawn(task, OmegaAgentClass) {
        const id = crypto.randomBytes(2).toString('hex');
        const worker = new WorkerNode(id, task, this.parentAgent);
        
        this.parentAgent._emitProgress({ label: `[SWARM] Received task routing for ${worker.prefix}...`, phase: 'tool' });

        if (this.activeWorkers.size >= this.maxConcurrent) {
            this.parentAgent._emitProgress({ label: `[SWARM] Concurrency limit hit. Queuing ${worker.prefix}...`, phase: 'tool' });
            return new Promise((resolve) => {
                this.queue.push({ worker, OmegaAgentClass, resolve });
            });
        }

        const vramOk = await this.checkVramCapacity();
        if (!vramOk) {
            this.parentAgent._emitProgress({ label: `[SWARM] VRAM constraint! Queuing ${worker.prefix}...`, phase: 'tool' });
            return new Promise((resolve) => {
                this.queue.push({ worker, OmegaAgentClass, resolve });
            });
        }

        return this._runWorker(worker, OmegaAgentClass);
    }

    async _runWorker(worker, OmegaAgentClass) {
        this.activeWorkers.set(worker.id, worker);
        const result = await worker.execute(OmegaAgentClass);
        this.activeWorkers.delete(worker.id);

        setImmediate(() => this._processQueue());
        return result;
    }

    async _processQueue() {
        if (this.queue.length === 0 || this.activeWorkers.size >= this.maxConcurrent) {
            return;
        }

        const vramOk = await this.checkVramCapacity();
        if (!vramOk) return;

        const next = this.queue.shift();
        const result = await this._runWorker(next.worker, next.OmegaAgentClass);
        next.resolve(result);
    }
}

module.exports = { SwarmManager, WorkerNode };
