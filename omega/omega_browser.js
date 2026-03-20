/**
 * OMEGA BROWSER v4.1 â€” Puppeteer Automation
 *
 * GATED tool for browser automation:
 *   - Navigate, click, type, screenshot
 *   - Multi-step task execution
 *   - Visible mode (non-headless) with screenshots for audit
 */
'use strict';

const path = require('path');
const fs = require('fs');

class OmegaBrowser {
    constructor({ screenshotDir }) {
        this._browser = null;
        this._page = null;
        this._screenshotDir = screenshotDir || path.join(__dirname, '..', 'screenshots');
        if (!fs.existsSync(this._screenshotDir)) {
            fs.mkdirSync(this._screenshotDir, { recursive: true });
        }
    }

    async _ensureBrowser() {
        if (this._browser && this._page) return;
        try {
            const puppeteer = require('puppeteer');
            this._browser = await puppeteer.launch({
                headless: false,
                defaultViewport: { width: 1280, height: 900 },
                args: ['--no-sandbox', '--disable-setuid-sandbox'],
            });
            this._page = await this._browser.newPage();
            this._page.setDefaultNavigationTimeout(30000);
        } catch (err) {
            throw new Error(`Failed to launch browser: ${err.message}`);
        }
    }

    async navigate(url) {
        await this._ensureBrowser();
        await this._page.goto(url, { waitUntil: 'networkidle2' });
        const title = await this._page.title();
        return { url, title, success: true };
    }

    async click(selector) {
        await this._ensureBrowser();
        await this._page.click(selector);
        return { selector, clicked: true };
    }

    async type(selector, text) {
        await this._ensureBrowser();
        await this._page.click(selector);
        await this._page.type(selector, text);
        return { selector, typed: text.length };
    }

    async screenshot(name) {
        await this._ensureBrowser();
        const filename = `${name || 'screenshot'}_${Date.now()}.png`;
        const filepath = path.join(this._screenshotDir, filename);
        await this._page.screenshot({ path: filepath, fullPage: true });
        return { path: filepath, filename };
    }

    async getText(selector) {
        await this._ensureBrowser();
        const text = await this._page.$eval(selector, el => el.textContent);
        return { selector, text: text.trim() };
    }

    async evaluate(code) {
        await this._ensureBrowser();
        const result = await this._page.evaluate(code);
        return { result };
    }

    async executeTask(steps) {
        const results = [];
        for (const step of steps) {
            try {
                let result;
                switch (step.action) {
                    case 'navigate': result = await this.navigate(step.url); break;
                    case 'click':    result = await this.click(step.selector); break;
                    case 'type':     result = await this.type(step.selector, step.text); break;
                    case 'screenshot': result = await this.screenshot(step.name); break;
                    case 'getText':  result = await this.getText(step.selector); break;
                    case 'evaluate': result = await this.evaluate(step.code); break;
                    case 'wait':     await new Promise(r => setTimeout(r, step.ms || 1000)); result = { waited: step.ms || 1000 }; break;
                    default: result = { error: `Unknown action: ${step.action}` };
                }
                results.push({ step: step.action, ...result });
            } catch (err) {
                results.push({ step: step.action, error: err.message });
                if (step.stopOnError !== false) break;
            }
        }
        // Take final screenshot for audit
        try {
            const audit = await this.screenshot('task_audit');
            results.push({ step: 'audit_screenshot', ...audit });
        } catch { }
        return results;
    }

    async close() {
        if (this._browser) {
            await this._browser.close();
            this._browser = null;
            this._page = null;
        }
    }
}

module.exports = { OmegaBrowser };
