import fs from "node:fs/promises";
import http from "node:http";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";

const root = path.resolve(import.meta.dirname, "..");
const defaultUrl = "http://127.0.0.1:4174/web/index.html";
const targetUrl = process.env.GRAVITY_OMEGA_QA_URL || defaultUrl;
const chromeBin = process.env.CHROME_BIN || "google-chrome";

function requestJson(url) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, (res) => {
      let body = "";
      res.setEncoding("utf8");
      res.on("data", (chunk) => {
        body += chunk;
      });
      res.on("end", () => {
        if (res.statusCode < 200 || res.statusCode >= 300) {
          reject(new Error(`GET ${url} failed with ${res.statusCode}: ${body.slice(0, 200)}`));
          return;
        }
        try {
          resolve(JSON.parse(body));
        } catch (error) {
          reject(new Error(`GET ${url} returned invalid JSON: ${error.message}`));
        }
      });
    });
    req.on("error", reject);
    req.setTimeout(8000, () => {
      req.destroy(new Error(`GET ${url} timed out`));
    });
  });
}

function findFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      const port = typeof address === "object" && address ? address.port : 0;
      server.close(() => resolve(port));
    });
    server.on("error", reject);
  });
}

async function waitForDevtools(port) {
  const started = Date.now();
  let lastError = null;
  while (Date.now() - started < 30000) {
    try {
      return await requestJson(`http://127.0.0.1:${port}/json/version`);
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, 200));
    }
  }
  throw new Error(`Chrome DevTools did not become ready: ${lastError?.message ?? "unknown error"}`);
}

function waitForChildExit(child, timeoutMs = 3000) {
  if (!child || child.exitCode !== null || child.signalCode) {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      child.kill("SIGKILL");
      resolve();
    }, timeoutMs);
    child.once("exit", () => {
      clearTimeout(timer);
      resolve();
    });
  });
}

async function makeCdpClient(webSocketDebuggerUrl) {
  const ws = new WebSocket(webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve, { once: true });
    ws.addEventListener("error", reject, { once: true });
  });

  let id = 0;
  const pending = new Map();
  const events = [];
  ws.addEventListener("message", (message) => {
    const packet = JSON.parse(message.data);
    if (packet.id && pending.has(packet.id)) {
      const { resolve, reject } = pending.get(packet.id);
      pending.delete(packet.id);
      if (packet.error) {
        reject(new Error(`${packet.error.message}: ${packet.error.data ?? ""}`));
      } else {
        resolve(packet.result ?? {});
      }
      return;
    }
    if (packet.method) {
      events.push(packet);
    }
  });

  const send = (method, params = {}, timeoutMs = 60000) => {
    const messageId = ++id;
    ws.send(JSON.stringify({ id: messageId, method, params }));
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        if (pending.has(messageId)) {
          pending.delete(messageId);
          reject(new Error(`CDP ${method} timed out`));
        }
      }, timeoutMs);
      pending.set(messageId, {
        resolve: (value) => {
          clearTimeout(timeout);
          resolve(value);
        },
        reject: (error) => {
          clearTimeout(timeout);
          reject(error);
        },
      });
    });
  };

  return {
    events,
    close: () => ws.close(),
    send,
  };
}

async function evaluate(cdp, expression, options = {}) {
  const result = await cdp.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
    ...options,
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text || "Runtime.evaluate exception");
  }
  return result.result?.value;
}

async function main() {
  const port = await findFreePort();
  const userDataDir = path.join(os.tmpdir(), `gravity-omega-qa-chrome-${Date.now()}`);
  const chrome = spawn(chromeBin, [
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-breakpad",
    "--disable-crash-reporter",
    "--disable-crashpad",
    `--remote-debugging-address=127.0.0.1`,
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${userDataDir}`,
    "--window-size=1440,1000",
    "about:blank",
  ], {
    stdio: ["ignore", "ignore", "pipe"],
  });

  let stderr = "";
  chrome.stderr.setEncoding("utf8");
  chrome.stderr.on("data", (chunk) => {
    stderr += chunk;
  });

  let cdp;
  try {
    await waitForDevtools(port);
    const pages = await requestJson(`http://127.0.0.1:${port}/json/list`);
    const page = pages.find((candidate) => candidate.type === "page") ?? pages[0];
    if (!page?.webSocketDebuggerUrl) {
      throw new Error("Chrome did not expose a page debugger target.");
    }
    cdp = await makeCdpClient(page.webSocketDebuggerUrl);
    await cdp.send("Runtime.enable");
    await cdp.send("Log.enable");
    await cdp.send("Page.enable");
    await cdp.send("Page.navigate", { url: targetUrl });
    await new Promise((resolve) => setTimeout(resolve, 2500));
    const staleGeneratedEditorSession = JSON.stringify({
      activeFilePath: "Omega Agent Work.md",
      updatedAt: "2026-05-28T00:00:00.000Z",
      tabs: [
        {
          path: "Omega Agent Work.md",
          content: "# Omega Agent Work\n\nstale generated QA session",
          dirty: true,
          untitled: false,
        },
        {
          path: "web/omega-draft-202605280000.md",
          content: "# Omega Draft 202605280000\n\nstale generated draft",
          dirty: true,
          untitled: true,
        },
      ],
    });
    await evaluate(cdp, `localStorage.setItem("gravity-omega.editor-session.v5", ${JSON.stringify(staleGeneratedEditorSession)})`);
    await cdp.send("Page.reload", { ignoreCache: true });
    await new Promise((resolve) => setTimeout(resolve, 2500));

    const qaResult = await evaluate(cdp, `(${workbenchQa.toString()})()`);
    const screenshot = await cdp.send("Page.captureScreenshot", { format: "png", fromSurface: true });
    const screenshotPath = path.join(os.tmpdir(), "gravity-omega-workbench-qa.png");
    await fs.writeFile(screenshotPath, Buffer.from(screenshot.data, "base64"));

    const browserEvents = cdp.events
      .filter((event) => ["Runtime.exceptionThrown", "Log.entryAdded"].includes(event.method))
      .map((event) => ({
        method: event.method,
        text: event.params?.exceptionDetails?.text || event.params?.entry?.text || "",
        level: event.params?.entry?.level || "",
      }))
      .filter((event) => event.level !== "verbose");

    const report = {
      url: targetUrl,
      root,
      screenshot: screenshotPath,
      chromeStderrTail: stderr.split("\n").slice(-12).join("\n"),
      browserEvents,
      ...qaResult,
    };
    console.log(JSON.stringify(report, null, 2));

    if (report.failures.length > 0 || browserEvents.some((event) => event.method === "Runtime.exceptionThrown" || event.level === "error")) {
      process.exitCode = 1;
    }
  } finally {
    cdp?.close();
    chrome.kill("SIGTERM");
    await waitForChildExit(chrome);
    await fs.rm(userDataDir, { recursive: true, force: true }).catch(() => {});
  }
}

async function workbenchQa() {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const failures = [];
  const passes = [];
  const interactions = [];
  const longPrompt = [
    "QA stress prompt:",
    "Verify Gravity Omega can accept a long dictated request without freezing.",
    "Codex Lead should plan, delegate to Hermes/Kimi where useful, preserve Omega Agent Work evidence, render useful main surfaces, and avoid claiming unsafe gates are enabled.",
    "The response should be brief in chat and detailed in the Monaco work artifact.",
    "This is a synthetic static-browser QA prompt, not a live execution request.",
  ].join(" ").repeat(10);

  const visible = (element) => {
    if (!element) return false;
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return !element.hidden && style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
  };
  const text = (selector) => document.querySelector(selector)?.textContent?.replace(/\s+/g, " ").trim() ?? "";
  const activeBottom = () => document.querySelector(".omega-bottom-view.active")?.dataset.bottomContent ?? "";
  const activePanel = () => document.querySelector(".omega-side-panel.active")?.dataset.panelContent ?? "";
  const sidebarCollapsed = () => document.querySelector("#omega-product-shell")?.classList.contains("omega-sidebar-collapsed");
  const click = async (selector, label) => {
    const matches = Array.from(document.querySelectorAll(selector)).filter(visible);
    if (matches.length !== 1) {
      failures.push(`${label}: expected 1 visible match for ${selector}, found ${matches.length}`);
      return false;
    }
    matches[0].click();
    interactions.push(label);
    await sleep(180);
    return true;
  };
  const closePalette = async () => {
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await sleep(80);
  };
  const ensurePanel = async (panel) => {
    if (activePanel() === panel && !sidebarCollapsed() && visible(document.querySelector(`.omega-side-panel[data-panel-content="${panel}"]`))) {
      return true;
    }
    return click(`.omega-activity-btn[data-product-panel="${panel}"]`, `activity:${panel}`);
  };
  const assert = (condition, message) => {
    if (condition) {
      passes.push(message);
    } else {
      failures.push(message);
    }
  };

  window.__gravityOmegaQaUnhandled = [];
  window.addEventListener("error", (event) => {
    window.__gravityOmegaQaUnhandled.push(`error:${event.message}`);
  });
  window.addEventListener("unhandledrejection", (event) => {
    window.__gravityOmegaQaUnhandled.push(`rejection:${event.reason?.message ?? event.reason}`);
  });

  await sleep(500);
  assert(visible(document.querySelector("#omega-product-shell")), "product shell is visible");
  assert(visible(document.querySelector("#omega-activity-bar")), "left activity rail is visible");
  assert(visible(document.querySelector("#omega-chat-panel-product")), "chat rail is visible");
  assert(visible(document.querySelector("#omega-monaco-frame")), "main Monaco frame is visible");
  assert(text("#omega-editor-tabs").includes("Omega Scratch.md"), "Default launch starts on Omega Scratch.md");
  assert(!text("#omega-editor-tabs").includes("Omega Agent Work"), "Default launch does not restore stale Omega Agent Work tabs");
  assert(!text("#omega-editor-tabs").includes("omega-draft-202605280000"), "Default launch does not restore stale generated draft tabs");
  assert(
    text(".omega-editor-toolbar-status").includes("parked for recovery") || text("#omega-product-status-detail").includes("Ready"),
    "Generated startup session is either parked visibly or the workbench remains ready"
  );

  const panels = ["explorer", "search", "omega", "vault", "security", "tools", "media", "settings"];
  for (const panel of panels) {
    if (await ensurePanel(panel)) {
      assert(activePanel() === panel, `activity ${panel} changes sidebar active panel`);
      assert(visible(document.querySelector(`.omega-side-panel[data-panel-content="${panel}"]`)), `activity ${panel} reveals panel content`);
      assert(text("#omega-product-status-detail").length > 0, `activity ${panel} updates status detail`);
    }
  }

  const panelParents = {
    codex: "omega",
    hermes: "omega",
    mcp: "omega",
    "joint-ci": "omega",
    evidence: "vault",
    sswp: "vault",
    desktop: "security",
    "omega-computer": "security",
    shield: "security",
    browser: "media",
    media: "media",
    ocr: "media",
    modules: "media",
    providers: "settings",
    "ship-readiness": "settings",
  };

  for (const [action, parent] of Object.entries(panelParents)) {
    await ensurePanel(parent);
    if (await click(`button[data-panel-action="${action}"]`, `panel-action:${action}`)) {
      if (action === "omega-computer") {
        assert(visible(document.querySelector("#omega-computer-main-surface")), "Omega Computer opens the main control surface");
        assert(text("#omega-computer-main-surface").includes("Omega Computer"), "Omega Computer surface names itself");
        assert(document.querySelectorAll(".omega-computer-worker-card").length >= 8, "Omega Computer renders worker cards");
        assert(visible(document.querySelector(".omega-computer-stage-rail")), "Omega Computer renders the stage pipeline");
        assert(text("#omega-computer-main-surface").includes("Session Packet"), "Omega Computer shows session packet evidence");
        assert(text("#omega-computer-main-surface").includes("Evidence Required"), "Omega Computer shows selected-agent evidence detail");
        assert(text("#omega-computer-main-surface").includes("Blocked Actions"), "Omega Computer shows selected-agent blocked-action detail");
        assert(text("#omega-editor-tabs").includes("Omega Agent Work"), "Omega Computer opens the Monaco work packet tab");
      } else {
        const shell = document.querySelector(`.omega-panel-main-shell[data-panel-action-surface="${action}"]`);
        assert(visible(document.querySelector("#omega-panel-main-surface")), `${action} opens the shared main surface`);
        assert(visible(shell), `${action} renders its dedicated surface shell`);
        assert((shell?.querySelectorAll(".omega-panel-main-card").length ?? 0) > 0, `${action} renders useful cards`);
      }
      assert(text("#omega-product-status-detail").length > 0, `${action} updates status detail`);
    }
  }

  for (const view of ["terminal", "output", "artifact", "problems", "evidence"]) {
    if (await click(`button[data-bottom-view="${view}"]`, `bottom:${view}`)) {
      assert(activeBottom() === view, `bottom ${view} activates matching content`);
    }
  }

  const commandExpectations = {
    "menu-file": () => !document.querySelector("#omega-command-palette-product")?.hidden && text("#omega-product-status-detail").toLowerCase().includes("file"),
    "menu-edit": () => !document.querySelector("#omega-command-palette-product")?.hidden && text("#omega-product-status-detail").toLowerCase().includes("edit"),
    "menu-view": () => !document.querySelector("#omega-command-palette-product")?.hidden && text("#omega-product-status-detail").toLowerCase().includes("view"),
    "menu-terminal": () => !document.querySelector("#omega-command-palette-product")?.hidden && text("#omega-product-status-detail").toLowerCase().includes("terminal"),
    "menu-help": () => !document.querySelector("#omega-command-palette-product")?.hidden && text("#omega-product-status-detail").toLowerCase().includes("help"),
    "new-file": () => text("#omega-editor-tabs").includes("omega-draft"),
    search: () => activePanel() === "search",
    split: () => text("#omega-product-status-detail").toLowerCase().includes("split"),
    "artifact-preview": () => activeBottom() === "artifact",
    "sovereign-docs-preview": () => activeBottom() === "artifact" && document.querySelector("#omega-product-sovereign-docs-btn")?.classList.contains("active"),
    "omega-computer": () => visible(document.querySelector("#omega-computer-main-surface")),
  };

  for (const [command, expectation] of Object.entries(commandExpectations)) {
    if (command === "search") {
      await closePalette();
    }
    const button = Array.from(document.querySelectorAll(`[data-product-command="${command}"]`)).find(visible);
    if (!button) {
      failures.push(`command ${command}: no visible button`);
      continue;
    }
    button.click();
    interactions.push(`command:${command}`);
    await sleep(220);
    assert(expectation(), `command ${command} produces visible behavior`);
    if (command.startsWith("menu-")) {
      await closePalette();
    }
  }

  await ensurePanel("settings");
  for (const [command, expectation] of Object.entries({
    "layout-reset": () => text("#omega-product-status-detail").toLowerCase().includes("layout"),
    palette: () => !document.querySelector("#omega-command-palette-product")?.hidden,
    docs: () => text("#omega-product-status-detail").includes("README") || text("#omega-editor-tabs").includes("README"),
    about: () => text("#omega-product-status-detail").includes("Gravity Omega"),
  })) {
    const button = Array.from(document.querySelectorAll(`[data-product-command="${command}"]`)).find(visible);
    if (!button) {
      failures.push(`settings command ${command}: no visible button`);
      continue;
    }
    button.click();
    interactions.push(`settings-command:${command}`);
    await sleep(220);
    assert(expectation(), `settings command ${command} produces visible behavior`);
    if (command === "palette") await closePalette();
  }

  const chatInput = document.querySelector("#omega-chat-input-parity");
  if (chatInput) {
    chatInput.value = longPrompt;
    chatInput.dispatchEvent(new Event("input", { bubbles: true }));
    assert(chatInput.value.length > 3000, "chat input accepts long dictated prompt text");
    chatInput.value = "how did it go";
    chatInput.dispatchEvent(new Event("input", { bubbles: true }));
    if (await click("#omega-parity-send", "run-button:status-recap")) {
      assert(text("#omega-parity-chat-messages").includes("Latest Omega Computer recap"), "status follow-up posts latest run recap");
      assert(text("#omega-product-status-detail").toLowerCase().includes("recap"), "status follow-up updates status detail");
    }
    chatInput.value = "status";
    chatInput.dispatchEvent(new Event("input", { bubbles: true }));
    chatInput.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", ctrlKey: true, bubbles: true }));
    interactions.push("keyboard:ctrl-enter-status-recap");
    await sleep(220);
    assert(text("#omega-parity-chat-messages").includes("Latest Omega Computer recap"), "Ctrl+Enter posts latest run recap without launching a new run");
    assert(document.querySelector("#omega-parity-recover")?.disabled, "recover button stays disabled when no active run is present");
    chatInput.value = longPrompt;
    chatInput.dispatchEvent(new Event("input", { bubbles: true }));
  } else {
    failures.push("chat input is missing");
  }

  for (const mode of ["codex-lead", "evidence-compare"]) {
    if (await click(`button[data-agent-run-mode="${mode}"]`, `agent-mode:${mode}`)) {
      assert(document.querySelector(`button[data-agent-run-mode="${mode}"]`)?.classList.contains("active"), `agent mode ${mode} becomes active`);
    }
  }

  for (const buttonId of ["#omega-parity-send", "#omega-parity-codex-write", "#omega-parity-hermes", "#omega-parity-compare"]) {
    if (await click(buttonId, `run-button:${buttonId}`)) {
      assert(text("#omega-parity-composer-status").length > 0 || text("#omega-parity-chat-messages").length > 0, `${buttonId} gives visible composer/chat feedback`);
    }
  }

  const artifactButtons = ["#omega-artifact-preview-fit-product", "#omega-artifact-preview-tall-product", "#omega-artifact-preview-expand-product"];
  await click(`button[data-bottom-view="artifact"]`, "bottom:artifact:controls");
  for (const selector of artifactButtons) {
    if (await click(selector, `artifact-control:${selector}`)) {
      assert(text("#omega-product-status-detail").length > 0, `${selector} updates status`);
    }
  }
  if (!document.querySelector("#omega-artifact-preview-overlay")?.hidden) {
    await click("#omega-artifact-preview-overlay-close", "artifact-overlay-close");
    assert(document.querySelector("#omega-artifact-preview-overlay")?.hidden, "artifact overlay closes");
  }

  const bodyRect = document.body.getBoundingClientRect();
  const shellRect = document.querySelector("#omega-product-shell")?.getBoundingClientRect();
  assert(bodyRect.width > 1000 && bodyRect.height > 700, "desktop viewport size is valid");
  assert(shellRect && shellRect.width > 1000 && shellRect.height > 700, "workbench shell uses desktop viewport");
  assert(window.__gravityOmegaQaUnhandled.length === 0, `no unhandled browser errors: ${window.__gravityOmegaQaUnhandled.join("; ")}`);

  return {
    passes,
    failures,
    interactions,
    counts: {
      activityButtons: document.querySelectorAll(".omega-activity-btn[data-product-panel]").length,
      panelActions: document.querySelectorAll("button[data-panel-action]").length,
      productCommands: document.querySelectorAll("[data-product-command]").length,
      bottomTabs: document.querySelectorAll("button[data-bottom-view]").length,
      chatMessages: document.querySelectorAll(".omega-chat-message").length,
    },
    final: {
      activePanel: document.querySelector("#omega-sidebar")?.dataset.activePanel ?? "",
      activeBottom: activeBottom(),
      status: text("#omega-product-status-detail"),
      composerStatus: text("#omega-parity-composer-status"),
      activeTab: text(".omega-editor-tab.active"),
    },
  };
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
