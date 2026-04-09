/**
 * GRAVITY OMEGA — Conversation Store
 * 
 * Flat JSON file store for persistent chat threads.
 * Each thread = one {uuid}.json file + metadata in _index.json.
 * Writes use atomic rename (write .tmp → rename) to prevent corruption.
 * 
 * Storage: %APPDATA%/gravity-omega/conversations/
 */
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { app } = require('electron');

const MAX_THREADS = 100;
const MAX_THREAD_SIZE_BYTES = 500 * 1024; // 500KB per thread file

class ConversationStore {
    constructor() {
        this._dir = path.join(app.getPath('userData'), 'conversations');
        this._indexPath = path.join(this._dir, '_index.json');
        this._ensureDir();
    }

    _ensureDir() {
        if (!fs.existsSync(this._dir)) {
            fs.mkdirSync(this._dir, { recursive: true });
        }
        if (!fs.existsSync(this._indexPath)) {
            this._writeAtomic(this._indexPath, []);
        }
    }

    /** Atomic write: write to .tmp then rename */
    _writeAtomic(filePath, data) {
        const tmp = filePath + '.tmp';
        fs.writeFileSync(tmp, JSON.stringify(data, null, 2), 'utf-8');
        fs.renameSync(tmp, filePath);
    }

    _readJSON(filePath) {
        try {
            return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
        } catch {
            return null;
        }
    }

    _threadPath(id) {
        return path.join(this._dir, `${id}.json`);
    }

    _loadIndex() {
        return this._readJSON(this._indexPath) || [];
    }

    _saveIndex(index) {
        this._writeAtomic(this._indexPath, index);
    }

    /** Create a new thread. Returns { id, title, createdAt }. */
    createThread(title = 'New Conversation') {
        const index = this._loadIndex();

        // Enforce max threads — warn and delete oldest
        if (index.length >= MAX_THREADS) {
            const oldest = index[index.length - 1];
            this.deleteThread(oldest.id);
            console.warn(`[ConversationStore] Max threads (${MAX_THREADS}) reached. Deleted oldest: ${oldest.title}`);
        }

        const id = crypto.randomUUID();
        const now = new Date().toISOString();
        const entry = {
            id,
            title,
            createdAt: now,
            updatedAt: now,
            messageCount: 0,
            preview: ''
        };

        const threadData = { id, title, createdAt: now, messages: [] };
        this._writeAtomic(this._threadPath(id), threadData);

        index.unshift(entry);
        this._saveIndex(index);

        return { id, title, createdAt: now };
    }

    /** List all threads (sorted by updatedAt desc). */
    listThreads() {
        const index = this._loadIndex();
        return index.sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
    }

    /** Load a full thread with messages. */
    loadThread(id) {
        const data = this._readJSON(this._threadPath(id));
        if (!data) return null;
        return data;
    }

    /** Append a message to a thread. Enforces 500KB size cap on stepLogs. */
    appendMessage(threadId, msg) {
        const filePath = this._threadPath(threadId);
        const data = this._readJSON(filePath);
        if (!data) throw new Error(`Thread ${threadId} not found`);

        const message = {
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp || new Date().toISOString(),
        };
        if (msg.stepLog) message.stepLog = msg.stepLog;
        if (msg.steps) message.steps = msg.steps;

        data.messages.push(message);

        // Enforce 500KB size cap — trim stepLogs from oldest messages first
        let serialized = JSON.stringify(data);
        while (Buffer.byteLength(serialized, 'utf-8') > MAX_THREAD_SIZE_BYTES && data.messages.length > 2) {
            for (const m of data.messages) {
                if (m.stepLog) {
                    delete m.stepLog;
                    delete m.steps;
                    break; // Remove one at a time, re-check size
                }
            }
            serialized = JSON.stringify(data);
            // If no more stepLogs to trim, stop
            if (!data.messages.some(m => m.stepLog)) break;
        }

        this._writeAtomic(filePath, data);

        // Update index
        const index = this._loadIndex();
        const entry = index.find(e => e.id === threadId);
        if (entry) {
            entry.updatedAt = message.timestamp;
            entry.messageCount = data.messages.length;
            entry.preview = (msg.role === 'user' ? msg.content : entry.preview || '').substring(0, 80);

            // Auto-title from first user message
            if (entry.title === 'New Conversation' && msg.role === 'user') {
                entry.title = msg.content.substring(0, 50).replace(/\n/g, ' ');
                data.title = entry.title;
                this._writeAtomic(filePath, data);
            }
        }
        this._saveIndex(index);
    }

    /** Rename a thread. */
    renameThread(id, title) {
        const index = this._loadIndex();
        const entry = index.find(e => e.id === id);
        if (entry) {
            entry.title = title;
            this._saveIndex(index);
        }
        const data = this._readJSON(this._threadPath(id));
        if (data) {
            data.title = title;
            this._writeAtomic(this._threadPath(id), data);
        }
    }

    /** Delete a thread. */
    deleteThread(id) {
        const filePath = this._threadPath(id);
        try { fs.unlinkSync(filePath); } catch {}
        try { fs.unlinkSync(filePath + '.tmp'); } catch {}

        const index = this._loadIndex();
        const filtered = index.filter(e => e.id !== id);
        this._saveIndex(filtered);
    }
}

module.exports = { ConversationStore };
