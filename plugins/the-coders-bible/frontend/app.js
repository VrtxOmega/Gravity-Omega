/**
 * The Coder's Bible — Frontend v2.0
 * Tabbed UI: Search | Analyze | Browse
 * Command Palette (Ctrl+K), animated counters, particle canvas
 */

const API = '';

function escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

const DOMAIN_ICONS = {
    Python:'🐍',JavaScript:'⚡',TypeScript:'🔷',Rust:'⚙️',Go:'🔹',
    Ruby:'💎',PHP:'🐘',Java:'☕',Bash:'🖥️',PowerShell:'🟦',
    SQL:'🗄️',Docker:'🐳',Kubernetes:'☸️',Nginx:'🌐',systemd:'🔧',
    Git:'📂',Ansible:'🅰️',Terraform:'🏗️',Linux:'🐧',CSS:'🎨',
    HTML:'📄',YAML:'📋',JSON:'📦','C#':'🟢',Kotlin:'🟣',
    'C/C++':'🔩',Swift:'🦅','Node.js':'🟩',MySQL:'🐬',PostgreSQL:'🐘',Other:'📁'
};
const TIER_COLORS = {
    Official:'linear-gradient(135deg,#22c55e,#16a34a)',
    Man:'linear-gradient(135deg,#3b82f6,#2563eb)',
    Derived:'linear-gradient(135deg,#a855f7,#7c3aed)',
    'Tier A (Official)':'linear-gradient(135deg,#22c55e,#16a34a)',
    'Tier B (Man Pages)':'linear-gradient(135deg,#3b82f6,#2563eb)',
    'Tier C (Derived)':'linear-gradient(135deg,#a855f7,#7c3aed)',
    'Tier C (Derived/Community)':'linear-gradient(135deg,#a855f7,#7c3aed)'
};

let statsData = null;
let searchDebounce = null;

// ─── Init ───
document.addEventListener('DOMContentLoaded', () => {
    initParticles();
    initTabs();
    initSearch();
    initAnalyze();
    initCommandPalette();
    loadStats();
});

// ─── Particle Canvas ───
function initParticles() {
    const c = document.getElementById('particle-canvas');
    if (!c) return;
    const ctx = c.getContext('2d');
    let particles = [];
    function resize() { c.width = window.innerWidth; c.height = window.innerHeight; }
    resize();
    window.addEventListener('resize', resize);
    for (let i = 0; i < 60; i++) {
        particles.push({
            x: Math.random()*c.width, y: Math.random()*c.height,
            vx: (Math.random()-0.5)*0.3, vy: (Math.random()-0.5)*0.3,
            r: Math.random()*1.5+0.5, a: Math.random()*0.5+0.1
        });
    }
    function draw() {
        ctx.clearRect(0,0,c.width,c.height);
        particles.forEach(p => {
            p.x += p.vx; p.y += p.vy;
            if (p.x<0) p.x=c.width; if (p.x>c.width) p.x=0;
            if (p.y<0) p.y=c.height; if (p.y>c.height) p.y=0;
            ctx.beginPath();
            ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
            ctx.fillStyle = `rgba(212,175,55,${p.a})`;
            ctx.fill();
        });
        // Draw connections
        for (let i=0;i<particles.length;i++) {
            for (let j=i+1;j<particles.length;j++) {
                const dx=particles[i].x-particles[j].x, dy=particles[i].y-particles[j].y;
                const d=Math.sqrt(dx*dx+dy*dy);
                if (d<120) {
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x,particles[i].y);
                    ctx.lineTo(particles[j].x,particles[j].y);
                    ctx.strokeStyle=`rgba(212,175,55,${0.08*(1-d/120)})`;
                    ctx.stroke();
                }
            }
        }
        requestAnimationFrame(draw);
    }
    draw();
}

// ─── Tab System ───
function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });
}

function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    const btn = document.querySelector(`.tab-btn[data-tab="${tab}"]`);
    const panel = document.getElementById(`tab-${tab}`);
    if (btn) btn.classList.add('active');
    if (panel) panel.classList.add('active');
    if (tab === 'search') document.getElementById('search-input')?.focus();
    if (tab === 'analyze') document.getElementById('snippet-input')?.focus();
    if (tab === 'browse' && statsData) renderDomains(statsData.domains);
}

// ─── Search Tab ───
let currentSearchQuery = '';
let selectedResultIdx = -1;

function initSearch() {
    const input = document.getElementById('search-input');
    if (!input) return;
    input.addEventListener('input', () => {
        clearTimeout(searchDebounce);
        searchDebounce = setTimeout(() => doSearch(input.value), 400);
    });
    input.addEventListener('keydown', e => {
        if (e.key === 'Enter') { clearTimeout(searchDebounce); doSearch(input.value); }
        // Keyboard navigation for search results
        const cards = document.querySelectorAll('.search-result-card');
        if (cards.length === 0) return;
        if (e.key === 'ArrowDown') { e.preventDefault(); navigateResults(cards, 1); }
        if (e.key === 'ArrowUp') { e.preventDefault(); navigateResults(cards, -1); }
        if (e.key === 'Escape') { selectedResultIdx = -1; cards.forEach(c => c.classList.remove('result-selected')); input.focus(); }
    });
}

function navigateResults(cards, dir) {
    cards.forEach(c => c.classList.remove('result-selected'));
    selectedResultIdx = Math.max(-1, Math.min(cards.length - 1, selectedResultIdx + dir));
    if (selectedResultIdx >= 0) {
        cards[selectedResultIdx].classList.add('result-selected');
        cards[selectedResultIdx].scrollIntoView({ behavior:'smooth', block:'nearest' });
    }
}

async function doSearch(query) {
    const q = query.trim();
    currentSearchQuery = q;
    selectedResultIdx = -1;
    const container = document.getElementById('search-results');
    const countEl = document.getElementById('search-result-count');
    if (!q) { container.innerHTML = ''; countEl.textContent = ''; return; }
    container.innerHTML = '<div class="search-loading"><div class="loading-spinner"></div> Searching...</div>';
    try {
        const res = await fetch(`${API}/api/search?q=${encodeURIComponent(q)}&limit=20`);
        const data = await res.json();
        countEl.textContent = `${data.count} results`;
        if (!data.results || data.results.length === 0) {
            container.innerHTML = '<div class="search-empty">No fragments found. Try different keywords.</div>';
            return;
        }
        const insightHtml = generateInsight(q, data.results, data.count);
        const resultsHtml = data.results.map(r => renderSearchResult(r, q)).join('');
        container.innerHTML = insightHtml + resultsHtml;
    } catch(e) {
        container.innerHTML = '<div class="search-empty">Search failed — is the backend running on port 5090?</div>';
    }
}

// ─── Quick Insight Generator ───
function generateInsight(query, results, totalCount) {
    // Analyze sources to extract domain names
    const domainCounts = {};
    const tierCounts = {};
    results.forEach(r => {
        const src = r.source || 'unknown';
        const domain = extractDomainFromSource(src);
        domainCounts[domain] = (domainCounts[domain] || 0) + 1;
        const tier = normalizeTier(r.tier || 'Derived');
        tierCounts[tier] = (tierCounts[tier] || 0) + 1;
    });

    // Sort domains by count
    const sortedDomains = Object.entries(domainCounts).sort((a,b) => b[1] - a[1]);
    const topDomain = sortedDomains[0];
    const domainCount = sortedDomains.length;

    // Build tier description
    const tierDescriptions = [];
    if (tierCounts['Official']) tierDescriptions.push(`${tierCounts['Official']} from official documentation`);
    if (tierCounts['Reference']) tierDescriptions.push(`${tierCounts['Reference']} from reference material`);
    if (tierCounts['Community']) tierDescriptions.push(`${tierCounts['Community']} community-sourced`);

    // Build the "what it's about" phrase
    const keywords = query.split(/\s+/).filter(w => w.length > 1);
    const topicPhrase = keywords.length > 0 ? `<strong>${escapeHtml(keywords.join(' '))}</strong>` : 'your query';

    // Detect content type patterns from first few results
    const contentHints = detectContentPatterns(results.slice(0, 5));

    // Assemble the insight sentence
    let insightText = `Found <strong>${results.length}</strong> fragment${results.length !== 1 ? 's' : ''} related to ${topicPhrase}`;
    if (totalCount > results.length) {
        insightText += ` (${totalCount} total matches)`;
    }
    insightText += '. ';

    // Domain coverage
    if (domainCount === 1) {
        insightText += `All results come from <strong>${escapeHtml(topDomain[0])}</strong>. `;
    } else {
        const domainList = sortedDomains.slice(0, 3).map(d => `<strong>${escapeHtml(d[0])}</strong>`).join(', ');
        const moreCount = domainCount > 3 ? ` and ${domainCount - 3} more` : '';
        insightText += `Results span ${domainCount} domains — ${domainList}${moreCount} — with the strongest coverage in <strong>${escapeHtml(topDomain[0])}</strong>. `;
    }

    // Tier quality
    if (tierDescriptions.length > 0) {
        insightText += `Sources include ${tierDescriptions.join(', ')}. `;
    }

    // Content hints
    if (contentHints.length > 0) {
        insightText += `These fragments cover ${contentHints.join(', ')}.`;
    }

    // Domain icon for visual flair
    const topIcon = DOMAIN_ICONS[topDomain[0]] || '📖';

    return `<div class="search-insight">
        <div class="insight-icon">${topIcon}</div>
        <div class="insight-body">
            <div class="insight-title">Quick Insight</div>
            <div class="insight-text">${insightText}</div>
        </div>
    </div>`;
}

function extractDomainFromSource(source) {
    const s = source.toLowerCase();
    // Match known domain patterns from source strings
    const domainMap = {
        'python': 'Python', 'django': 'Python', 'flask': 'Python', 'pip': 'Python',
        'javascript': 'JavaScript', 'node': 'JavaScript', 'npm': 'JavaScript', 'react': 'JavaScript', 'vue': 'JavaScript',
        'typescript': 'TypeScript', 'angular': 'TypeScript',
        'rust': 'Rust', 'cargo': 'Rust',
        'go': 'Go', 'golang': 'Go',
        'ruby': 'Ruby', 'rails': 'Ruby', 'gem': 'Ruby',
        'php': 'PHP', 'laravel': 'PHP', 'composer': 'PHP',
        'java': 'Java', 'maven': 'Java', 'gradle': 'Java', 'spring': 'Java',
        'bash': 'Bash', 'shell': 'Bash', 'zsh': 'Bash', 'sh ': 'Bash',
        'powershell': 'PowerShell', 'pwsh': 'PowerShell',
        'sql': 'SQL', 'mysql': 'MySQL', 'postgres': 'PostgreSQL', 'sqlite': 'SQL',
        'docker': 'Docker', 'dockerfile': 'Docker', 'compose': 'Docker',
        'kubernetes': 'Kubernetes', 'kubectl': 'Kubernetes', 'k8s': 'Kubernetes', 'helm': 'Kubernetes',
        'nginx': 'Nginx', 'apache': 'Nginx',
        'systemd': 'systemd', 'journalctl': 'systemd',
        'git': 'Git', 'github': 'Git',
        'ansible': 'Ansible', 'playbook': 'Ansible',
        'terraform': 'Terraform', 'hcl': 'Terraform',
        'linux': 'Linux', 'ubuntu': 'Linux', 'centos': 'Linux', 'debian': 'Linux',
        'css': 'CSS', 'sass': 'CSS', 'scss': 'CSS',
        'html': 'HTML', 'dom': 'HTML',
        'yaml': 'YAML', 'yml': 'YAML',
        'json': 'JSON',
        'csharp': 'C#', 'dotnet': 'C#', '.net': 'C#',
        'kotlin': 'Kotlin', 'android': 'Kotlin',
        'swift': 'Swift', 'ios': 'Swift', 'xcode': 'Swift',
        'c++': 'C/C++', 'cpp': 'C/C++', 'cmake': 'C/C++', 'gcc': 'C/C++', 'clang': 'C/C++',
    };
    for (const [pattern, domain] of Object.entries(domainMap)) {
        if (s.includes(pattern)) return domain;
    }
    return 'General';
}

function normalizeTier(tier) {
    const t = (tier || '').trim();
    if (t === 'A' || t.includes('Official') || t.includes('Tier A')) return 'Official';
    if (t === 'B' || t.includes('Man') || t.includes('Tier B')) return 'Reference';
    return 'Community';
}

function detectContentPatterns(results) {
    const hints = new Set();
    results.forEach(r => {
        const c = (r.content || '').toLowerCase();
        if (c.includes('syntax') || c.includes('example') || c.includes('usage')) hints.add('syntax & usage examples');
        if (c.includes('error') || c.includes('exception') || c.includes('warning')) hints.add('error handling');
        if (c.includes('install') || c.includes('setup') || c.includes('config')) hints.add('setup & configuration');
        if (c.includes('function') || c.includes('method') || c.includes('class')) hints.add('API reference');
        if (c.includes('best practice') || c.includes('recommend') || c.includes('tip')) hints.add('best practices');
        if (c.includes('security') || c.includes('auth') || c.includes('permission')) hints.add('security patterns');
        if (c.includes('performance') || c.includes('optimize') || c.includes('cache')) hints.add('performance tuning');
        if (c.includes('debug') || c.includes('troubleshoot') || c.includes('fix')) hints.add('troubleshooting');
    });
    return Array.from(hints).slice(0, 3);
}

function renderSearchResult(r, query) {
    const tier = r.tier || 'Derived';
    const bg = TIER_COLORS[tier] || TIER_COLORS.Derived;
    let content = escapeHtml(r.content || '').substring(0, 300);
    const source = escapeHtml(r.source || 'unknown');
    // Highlight matching keywords
    if (query) {
        const words = query.split(/\s+/).filter(w => w.length > 1);
        words.forEach(word => {
            const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const re = new RegExp(`(${escaped})`, 'gi');
            content = content.replace(re, '<mark>$1</mark>');
        });
    }
    return `<div class="search-result-card" tabindex="0">
        <div class="search-result-header">
            <span class="search-result-source">${source}</span>
            <span class="search-result-tier" style="background:${bg};color:#fff">${tier}</span>
        </div>
        <div class="search-result-body">${content}</div>
    </div>`;
}

// ─── Analyze Tab ───
function initAnalyze() {
    const textarea = document.getElementById('snippet-input');
    const btn = document.getElementById('btn-analyze');
    const btnClear = document.getElementById('btn-clear');
    const charCount = document.getElementById('char-count');
    if (!textarea || !btn) return;

    textarea.addEventListener('input', () => {
        const len = textarea.value.length;
        charCount.textContent = `${len.toLocaleString()} / 10,000`;
        btn.disabled = len === 0;
        btnClear.style.display = len > 0 ? 'inline-flex' : 'none';
    });

    btn.addEventListener('click', () => analyzeSnippet(textarea.value));
    textarea.addEventListener('keydown', e => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') analyzeSnippet(textarea.value);
    });
    btnClear.addEventListener('click', () => {
        textarea.value = '';
        textarea.dispatchEvent(new Event('input'));
        document.getElementById('results-section').style.display = 'none';
    });

    // Example chips
    document.querySelectorAll('.example-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            textarea.value = chip.dataset.snippet;
            textarea.dispatchEvent(new Event('input'));
            analyzeSnippet(chip.dataset.snippet);
        });
    });
}

async function analyzeSnippet(snippet) {
    if (!snippet.trim()) return;
    const loading = document.getElementById('loading-indicator');
    const results = document.getElementById('results-section');
    loading.style.display = 'flex';
    results.style.display = 'none';

    try {
        const res = await fetch(`${API}/api/analyze`, {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({snippet})
        });
        const data = await res.json();
        loading.style.display = 'none';
        results.style.display = 'block';
        renderAnalysis(data);
    } catch(e) {
        loading.style.display = 'none';
        results.style.display = 'block';
        document.getElementById('bible-results').innerHTML = '<div class="search-empty">Analysis failed — is the backend running?</div>';
    }
}

function renderAnalysis(data) {
    // Quick Understanding — one-line plain-English summary
    const quContainer = document.getElementById('quick-understanding');
    if (quContainer && data.quick_understanding) {
        quContainer.style.display = 'block';
        quContainer.innerHTML = `<div class="qu-panel">
            <span class="qu-icon">⚡</span>
            <span class="qu-text">${escapeHtml(data.quick_understanding)}</span>
        </div>`;
    } else if (quContainer) {
        quContainer.style.display = 'none';
    }

    // Language Detection
    const lang = data.language || {};
    const badge = document.getElementById('lang-badge');
    badge.style.borderColor = lang.color || '#C9A84C';
    badge.style.boxShadow = `0 0 30px ${lang.color || '#C9A84C'}33`;
    document.getElementById('lang-name').textContent = lang.language || 'Unknown';
    document.getElementById('lang-confidence').textContent = `${Math.round((lang.confidence||0)*100)}%`;
    document.getElementById('lang-reasoning').textContent = lang.reasoning || '';
    document.getElementById('input-preview').innerHTML = `<code>${escapeHtml(data.input||'')}</code>`;

    const alts = (lang.alternatives||[]).map(a =>
        `<span class="alt-badge">${a.language} ${Math.round(a.confidence*100)}%</span>`
    ).join('');
    document.getElementById('alternatives').innerHTML = alts;

    // Breakdown
    const bd = data.breakdown || [];
    const bdCard = document.getElementById('breakdown-card');
    if (bd.length > 0) {
        bdCard.style.display = 'block';
        document.getElementById('breakdown-body').innerHTML = bd.map(b =>
            `<div class="breakdown-line"><code>${escapeHtml(b.code)}</code><span class="breakdown-concept">${b.concept}</span></div>`
        ).join('');
    } else { bdCard.style.display = 'none'; }

    // Safety
    const safety = data.safety || {};
    const safetyBody = document.getElementById('safety-body');
    const safetyIcon = document.getElementById('safety-icon');
    if (safety.level === 'DESTRUCTIVE') {
        safetyIcon.textContent = '🔴';
        safetyBody.innerHTML = safety.warnings.map(w =>
            `<div class="safety-warning danger">${w.message}</div>`
        ).join('');
    } else if (safety.level === 'SAFE') {
        safetyIcon.textContent = '🟢';
        safetyBody.innerHTML = `<div class="safety-ok">✅ ${(safety.safe_notes||[]).join(', ')}</div>`;
    } else {
        safetyIcon.textContent = '🟡';
        safetyBody.innerHTML = `<div class="safety-caution">⚠️ ${(safety.safe_notes||[]).join(', ')}</div>`;
    }

    // Keywords
    const kw = data.keywords || [];
    document.getElementById('keywords-body').innerHTML = kw.map(k =>
        `<span class="keyword-pill">${escapeHtml(k)}</span>`
    ).join('');

    // Bible Results
    const br = data.results || [];
    document.getElementById('result-count').textContent = `${br.length} references`;
    document.getElementById('bible-results').innerHTML = br.length > 0
        ? br.map(r => renderSearchResult(r)).join('')
        : '<div class="search-empty">No Bible references found for this snippet.</div>';
}

// ─── Command Palette ───
function initCommandPalette() {
    const palette = document.getElementById('cmd-palette');
    const trigger = document.getElementById('cmd-trigger');
    const input = document.getElementById('cmd-input');
    const overlay = palette?.querySelector('.cmd-overlay');

    trigger?.addEventListener('click', () => openPalette());
    overlay?.addEventListener('click', () => closePalette());

    document.addEventListener('keydown', e => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); openPalette(); }
        if (e.key === 'Escape' && palette?.style.display !== 'none') closePalette();
    });

    input?.addEventListener('input', () => {
        clearTimeout(searchDebounce);
        searchDebounce = setTimeout(() => doCmdSearch(input.value), 350);
    });
}

function openPalette() {
    const p = document.getElementById('cmd-palette');
    p.style.display = 'flex';
    document.getElementById('cmd-input').value = '';
    document.getElementById('cmd-input').focus();
    document.getElementById('cmd-results').innerHTML = '<div class="cmd-empty">Type to search 67,000+ code fragments</div>';
}

function closePalette() {
    document.getElementById('cmd-palette').style.display = 'none';
}

async function doCmdSearch(query) {
    const q = query.trim();
    const container = document.getElementById('cmd-results');
    if (!q) { container.innerHTML = '<div class="cmd-empty">Type to search 67,000+ code fragments</div>'; return; }
    try {
        const res = await fetch(`${API}/api/search?q=${encodeURIComponent(q)}&limit=8`);
        const data = await res.json();
        if (!data.results || data.results.length === 0) {
            container.innerHTML = '<div class="cmd-empty">No results found</div>';
            return;
        }
        container.innerHTML = data.results.map(r =>
            `<div class="cmd-result-item">
                <span class="cmd-result-source">${escapeHtml(r.source||'')}</span>
                <span class="cmd-result-content">${escapeHtml((r.content||'').substring(0,120))}</span>
            </div>`
        ).join('');
    } catch(e) {
        container.innerHTML = '<div class="cmd-empty">Search unavailable</div>';
    }
}

// ─── Load Stats & Domains ───
async function loadStats() {
    try {
        const res = await fetch(`${API}/api/stats`);
        statsData = await res.json();
        const total = statsData.total_fragments || 0;
        const domains = statsData.domains || [];
        const domainCount = domains.length;

        // Animated counters
        animateCounter('stat-total', total);
        animateCounter('stat-domains', domainCount);
        animateCounter('hero-frag-count', total);
        animateCounter('hero-domain-count', domainCount);

        document.getElementById('stats-count').textContent = total.toLocaleString();
        document.getElementById('browse-count').textContent = domainCount;

        renderDomains(domains);
    } catch(e) {
        document.getElementById('stats-count').textContent = 'offline';
    }
}

function animateCounter(id, target) {
    const el = document.getElementById(id);
    if (!el) return;
    const duration = 1500;
    const start = performance.now();
    function step(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.floor(target * eased).toLocaleString();
        if (progress < 1) requestAnimationFrame(step);
        else el.textContent = target.toLocaleString();
    }
    requestAnimationFrame(step);
}

function renderDomains(domains) {
    const grid = document.getElementById('domains-grid');
    if (!grid || !domains || !Array.isArray(domains)) return;
    const sorted = [...domains].sort((a,b) => b.count - a.count);
    const maxCount = sorted[0]?.count || 1;
    grid.innerHTML = sorted.map(d => {
        const icon = DOMAIN_ICONS[d.name] || '📁';
        const pct = Math.round((d.count/maxCount)*100);
        const color = d.color || '#C9A84C';
        return `<div class="domain-card" title="${d.name}: ${d.count.toLocaleString()} fragments" style="--domain-color:${color}">
            <div class="domain-icon">${icon}</div>
            <div class="domain-info">
                <span class="domain-name">${d.name}</span>
                <span class="domain-count">${d.count.toLocaleString()}</span>
            </div>
            <div class="domain-bar-track">
                <div class="domain-bar-fill" style="width:${pct}%;background:${color}"></div>
            </div>
        </div>`;
    }).join('');
}

// ─── Helpers ───
function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}
