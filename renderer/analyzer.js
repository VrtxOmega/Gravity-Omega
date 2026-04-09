// Veritas Report Generator Logic

const SLABELS={fatal:'FATAL ERROR',warning:'WARNING',pass:'VERIFIED',note:'NOTE',info:'INFO'};
const TLABELS={1:'TIER I — VERIFIED',2:'TIER II — SUPPORTED',3:'TIER III — CANDIDATE'};

function esc(s){
  return String(s||'')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;')
    .replace(/\n/g,'<br>');
}

function itemHTML(item){
  const s=(item.status||'info').toLowerCase();
  return `<div class="r-item ${s}">
    <div class="r-item-hdr">
      <div class="r-item-lbl">${esc(item.label)}</div>
      <span class="r-sbadge ${s}">${SLABELS[s]||s.toUpperCase()}</span>
    </div>
    <div class="r-item-body">${esc(item.content)}
      ${item.note?`<div class="r-item-note">${esc(item.note)}</div>`:''}
      ${item.verdict?`<div class="r-verdict"><div class="r-vlbl">Verdict</div><div class="r-vtxt">${esc(item.verdict)}</div></div>`:''}
    </div>
  </div>`;
}

function findingHTML(f){
  const t=Math.min(Math.max(parseInt(f.tier)||1,1),3);
  return `<div class="r-finding t${t}">
    <div class="r-fhdr">
      <div class="r-fttl">${f.number?f.number+' — ':''} ${esc(f.title)}</div>
      <span class="r-tbadge t${t}">${TLABELS[t]}</span>
    </div>
    <div class="r-fbody">${esc(f.content)}
      ${(f.subitems||[]).length?`<div class="r-subs">${(f.subitems||[]).map(s=>`<div class="r-sub">${esc(s)}</div>`).join('')}</div>`:''}
    </div>
  </div>`;
}

window.buildHTML = function(d,fname){
  const meta=d._meta||{};
  const sections=(d.sections||[]).map(sec=>`
    <div class="r-section">
      <div class="r-sec-hdr">
        <div class="r-sec-num">Section ${esc(sec.number||'')}</div>
        <div class="r-sec-ttl">${esc(sec.title||'')}</div>
      </div>
      ${sec.intro?`<p class="r-intro">${esc(sec.intro)}</p>`:''}
      ${(sec.items||[]).map(itemHTML).join('')}
    </div>`).join('');

  const findings=(d.feasible_set||[]).map(findingHTML).join('');

  return `
  <div class="r-hero">
    <div class="r-omega">Ω</div>
    <div class="r-brand">Gravity Omega</div>
    <div class="r-rsub">Veritas Command Center — Analysis Report</div>
    <div class="r-meta">
      <div class="r-meta-row"><span class="r-meta-lbl">DOCUMENT</span><span class="r-meta-val">${esc(d.title)}</span></div>
      <div class="r-meta-row"><span class="r-meta-lbl">SUBTITLE</span><span class="r-meta-val">${esc(d.subtitle)}</span></div>
      <div class="r-meta-row"><span class="r-meta-lbl">SESSION</span><span class="r-meta-val">${esc(d.session_id)}</span></div>
      <div class="r-meta-row"><span class="r-meta-lbl">MODEL</span><span class="r-meta-val">${esc(meta.model||'')}</span></div>
      <div class="r-meta-row"><span class="r-meta-lbl">SOURCE</span><span class="r-meta-val">${esc(fname)}</span></div>
    </div>
  </div>
  <div class="r-content">
    <div class="r-syslog">Core Invariant Active: VERITAS does not determine truth. VERITAS determines what survives disciplined attempts at falsification under explicitly declared constraints.</div>
    ${sections}
    ${findings?`
    <div class="r-section">
      <div class="r-sec-hdr"><div class="r-sec-num">Feasible Set</div><div class="r-sec-ttl">Key Findings &amp; Conclusions</div></div>
      <div class="r-legend">
        <div class="r-legend-item"><div class="r-dot t1"></div><div><span class="r-lname t1">Tier I — Verified</span><span class="r-ldesc">Confirmed fact or direct evidence</span></div></div>
        <div class="r-legend-item"><div class="r-dot t2"></div><div><span class="r-lname t2">Tier II — Supported</span><span class="r-ldesc">Well-supported conclusion</span></div></div>
        <div class="r-legend-item"><div class="r-dot t3"></div><div><span class="r-lname t3">Tier III — Candidate</span><span class="r-ldesc">Inference or leading hypothesis</span></div></div>
      </div>
      ${findings}
    </div>`:''}
    <div class="r-seal">
      <div class="r-strace"><span>TRACE ID:</span> &nbsp; ${esc(d.trace_id||meta.trace||'Ω-1.0-REPORT')}</div>
      <div class="r-strace"><span>SOURCE:</span> &nbsp; ${esc(fname)}</div>
      <div class="r-witness">${esc(d.witness)}</div>
      <div class="r-sstatus">STATUS: SEALED — ${esc(d.trace_id||'Ω-1.0')} ✓</div>
    </div>
    <div class="r-footer"><span>Ω</span> &nbsp; Gravity Omega &nbsp;·&nbsp; Veritas Report Generator &nbsp;·&nbsp; <span>v1.0</span></div>
  </div>`;
};

// Listeners for UI
function initAnalyzerListeners() {
    document.getElementById('btn-toggle-markdown')?.addEventListener('click', () => {
        if (!window.state || !window.state.openFiles) return;
        const file = window.state.openFiles.get(window.state.activeFile);
        if (!file) return;
        file.viewMode = (file.viewMode === 'preview') ? 'code' : 'preview';
        window.switchToFile(window.state.activeFile);
    });

    document.getElementById('btn-analyzer')?.addEventListener('click', () => {
        if (!window.state || !window.state.openFiles) return;
        const file = window.state.openFiles.get(window.state.activeFile);
        if (!file) return;
        file.viewMode = (file.viewMode === 'analyze') ? 'code' : 'analyze';
        window.switchToFile(window.state.activeFile);
    });

    const dropZone = document.getElementById('drop-zone');
    if (dropZone) {
        dropZone.addEventListener('click', () => {
            const file = window.state.openFiles.get(window.state.activeFile);
            if (file) {
                executeAnalysis(window.state.activeFile, file);
            }
        });
    }

    document.getElementById('btn-analyzer-reset')?.addEventListener('click', () => {
        document.getElementById('report-screen').classList.add('hidden');
        document.getElementById('upload-screen').classList.remove('hidden');
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAnalyzerListeners);
} else {
    initAnalyzerListeners();
}

let logIdx = 0;
function logAnalyzer(txt) {
    const t = document.getElementById('proc-terminal');
    if(!t) return;
    const l = document.createElement('div');
    l.className = 'proc-line';
    l.style.animationDelay = `${logIdx * 0.07}s`;
    l.textContent = txt;
    t.appendChild(l);
    logIdx++;
    t.scrollTop = t.scrollHeight;
}

async function executeAnalysis(filePath, fileState) {
    const model = document.getElementById('model-input').value.trim() || 'qwen3:8b';
    document.getElementById('upload-error').classList.add('hidden');
    document.getElementById('upload-screen').classList.add('hidden');
    document.getElementById('processing-screen').classList.remove('hidden');
    document.getElementById('proc-terminal').textContent = '';
    logIdx = 0;

    logAnalyzer(`Ingesting: ${fileState.name}`);
    logAnalyzer(`Model: ${model}`);
    logAnalyzer(`Routing to Omega Command Center backend...`);

    try {
        const formData = new FormData();
        const blob = new Blob([fileState.model.getValue()], { type: 'text/plain' });
        formData.append('file', blob, fileState.name);
        formData.append('model', model);

        const resp = await fetch('http://127.0.0.1:5000/api/analyze_document', { 
            method: 'POST', 
            body: formData 
        });
        
        const data = await resp.json();
        if (!resp.ok || data.error) throw new Error(data.error || `Server error ${resp.status}`);

        logAnalyzer(`Schema received. Compiling report...`);
        
        setTimeout(() => {
            document.getElementById('processing-screen').classList.add('hidden');
            document.getElementById('report-screen').classList.remove('hidden');
            document.getElementById('report-body').textContent = window.buildHTML(data, fileState.name);
        }, 800);

    } catch(e) {
        document.getElementById('processing-screen').classList.add('hidden');
        document.getElementById('upload-screen').classList.remove('hidden');
        const el = document.getElementById('upload-error');
        el.textContent = `Error: ${e.message}`;
        el.classList.remove('hidden');
    }
}
