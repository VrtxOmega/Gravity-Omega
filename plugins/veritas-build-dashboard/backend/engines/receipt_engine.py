"""
VERITAS Docs — Receipt Engine
================================
Generates an interactive HTML provenance receipt for every export.
Contains: trace ID, file hashes, operation metadata, AI analysis (if applicable),
tiered findings, sealed output block, and machine-readable JSON.
"""

import json
import os
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from models import BrandPreset, VeritasDocument, VeritasDocsOutput


def _escape(text: str) -> str:
    return (str(text).replace('&', '&amp;').replace('<', '&lt;')
                     .replace('>', '&gt;').replace('"', '&quot;'))


def render(doc: VeritasDocument, output: VeritasDocsOutput,
           brand: BrandPreset, output_path: Path) -> Path:
    """Generate an interactive HTML receipt for this export."""
    gen_date = datetime.now().strftime('%B %d, %Y — %H:%M')

    # Build format rows
    format_rows = ''
    for fmt, path in output.formats.items():
        file_hash = output.hashes.get(fmt, 'pending')
        fname = Path(path).name if path else '—'
        format_rows += f'''
        <tr>
          <td><span class="fmt-badge">{_escape(fmt.upper())}</span></td>
          <td>{_escape(fname)}</td>
          <td class="hash-cell">{_escape(file_hash[:16])}...</td>
        </tr>'''

    # AI analysis section (if present)
    ai_section = ''
    if doc.ai_analysis:
        ai = doc.ai_analysis
        sections_html = ''
        for sec in ai.get('sections', []):
            items_html = ''
            for item in sec.get('items', []):
                status = (item.get('status', 'info') or 'info').lower()
                items_html += f'''
                <div class="r-item {status}">
                  <div class="r-item-hdr">
                    <span class="r-item-lbl">{_escape(item.get('label', ''))}</span>
                    <span class="r-sbadge {status}">{_escape(status.upper())}</span>
                  </div>
                  <div class="r-item-body">{_escape(item.get('content', ''))}</div>
                </div>'''
            sections_html += f'''
            <div class="r-section">
              <div class="r-sec-hdr">
                <span class="r-sec-num">Section {_escape(str(sec.get('number', '')))}</span>
                <span class="r-sec-ttl">{_escape(sec.get('title', ''))}</span>
              </div>
              {items_html}
            </div>'''

        findings_html = ''
        for f in ai.get('feasible_set', []):
            tier = min(max(int(f.get('tier', 1)), 1), 3)
            tier_labels = {1: 'TIER I — VERIFIED', 2: 'TIER II — SUPPORTED', 3: 'TIER III — CANDIDATE'}
            subs = ''.join(f'<div class="r-sub">{_escape(s)}</div>' for s in f.get('subitems', []))
            findings_html += f'''
            <div class="r-finding t{tier}">
              <div class="r-fhdr">
                <span class="r-fttl">{_escape(f.get('title', ''))}</span>
                <span class="r-tbadge t{tier}">{tier_labels.get(tier, '')}</span>
              </div>
              <div class="r-fbody">{_escape(f.get('content', ''))}
                {f'<div class="r-subs">{subs}</div>' if subs else ''}
              </div>
            </div>'''

        witness = ai.get('witness', '')
        ai_section = f'''
        <div class="ai-analysis">
          <div class="r-sec-hdr">
            <span class="r-sec-num">AI Analysis</span>
            <span class="r-sec-ttl">INTELLIGENCE REPORT</span>
          </div>
          {sections_html}
          {f'<div class="r-sec-hdr"><span class="r-sec-num">Feasible Set</span><span class="r-sec-ttl">KEY FINDINGS</span></div>{findings_html}' if findings_html else ''}
          {f'<div class="r-witness">{_escape(witness)}</div>' if witness else ''}
        </div>'''

    # Machine-readable provenance JSON
    provenance_json = json.dumps({
        'trace_id': output.trace_id,
        'document_id': output.document_id,
        'operation': output.operation,
        'source_name': doc.source_name,
        'source_hash': doc.source_hash,
        'formats': output.formats,
        'hashes': output.hashes,
        'version': output.version,
        'created_at': output.created_at,
        'model': output.model,
        'brand': brand.name,
        'confidentiality': brand.confidentiality,
    }, indent=2)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Receipt — {_escape(output.trace_id)} — VERITAS Docs</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;500;600;700&family=Orbitron:wght@400;700;900&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{--gold:#C9A84C;--gold-dim:#8B6B20;--gold-border:#2a1f08;--bg:#080808;--white:#F5EDD6;--gray:#4a4030;--fatal:#FF4444;--warning:#FF8C42;--pass:#7ABD7A;--tier1:#C9A84C;--tier2:#E8E8C0;--tier3:#9ABDD4}}
body{{background:var(--bg);color:var(--white);font-family:'Share Tech Mono',monospace;font-size:13px;line-height:1.7;padding:0}}
.hero{{text-align:center;padding:40px;border-bottom:1px solid var(--gold-border);position:relative}}
.hero::before{{content:'';position:absolute;top:0;left:50%;transform:translateX(-50%);width:600px;height:300px;background:radial-gradient(ellipse at 50% 0%,rgba(201,168,76,.08) 0%,transparent 65%);pointer-events:none}}
.omega{{font-family:'Orbitron',monospace;font-size:48px;font-weight:900;color:var(--gold);text-shadow:0 0 12px rgba(240,192,64,0.5);position:relative;z-index:1}}
.brand{{font-family:'Rajdhani',sans-serif;font-weight:700;font-size:14px;letter-spacing:6px;color:var(--gold);text-transform:uppercase;margin-top:6px;position:relative;z-index:1}}
.receipt-label{{font-family:'Rajdhani',sans-serif;font-weight:700;font-size:10px;letter-spacing:4px;color:var(--gold-dim);margin-top:4px;position:relative;z-index:1}}
.content{{max-width:800px;margin:0 auto;padding:30px 24px}}
.meta-grid{{display:grid;grid-template-columns:120px 1fr;gap:6px 14px;border:1px solid var(--gold-border);padding:16px;margin-bottom:24px;background:#0a0a0a}}
.meta-lbl{{font-family:'Rajdhani',sans-serif;font-size:11px;letter-spacing:2px;color:var(--gold-dim);text-transform:uppercase}}
.meta-val{{color:var(--white);opacity:.8;font-size:12px;word-break:break-all}}
.section-title{{font-family:'Rajdhani',sans-serif;font-weight:700;font-size:13px;letter-spacing:3px;color:var(--gold);margin:24px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--gold-border)}}
table{{width:100%;border-collapse:collapse;margin:12px 0}}
th{{background:var(--gold);color:#0d0d0d;font-family:'Rajdhani',sans-serif;font-weight:700;font-size:10px;letter-spacing:2px;text-align:left;padding:8px 10px;text-transform:uppercase}}
td{{padding:7px 10px;border-bottom:1px solid #1a1a1a;font-size:12px}}
tr:nth-child(even) td{{background:#0a0a0a}}
.fmt-badge{{font-family:'Rajdhani',sans-serif;font-weight:700;font-size:10px;letter-spacing:2px;color:var(--gold);border:1px solid var(--gold-border);padding:2px 8px}}
.hash-cell{{font-family:'Share Tech Mono',monospace;font-size:10px;color:var(--gold-dim)}}
.r-section{{margin-bottom:20px}}
.r-sec-hdr{{display:flex;align-items:center;gap:14px;margin:20px 0 12px;padding-bottom:8px;border-bottom:1px solid var(--gold-border)}}
.r-sec-num{{font-family:'Rajdhani',sans-serif;font-size:10px;letter-spacing:3px;color:var(--gold-dim);min-width:80px}}
.r-sec-ttl{{font-family:'Rajdhani',sans-serif;font-weight:700;font-size:13px;letter-spacing:3px;color:var(--gold);text-transform:uppercase}}
.r-item{{border:1px solid var(--gold-border);margin-bottom:10px;background:#0a0a0a;position:relative;overflow:hidden}}
.r-item::before{{content:'';position:absolute;top:0;left:0;width:3px;height:100%}}
.r-item.fatal::before{{background:#8B2020}}.r-item.warning::before{{background:#8B4A20}}.r-item.pass::before{{background:#2a6b2a}}.r-item.note::before{{background:var(--gold-border)}}.r-item.info::before{{background:var(--gray)}}
.r-item-hdr{{padding:8px 14px;border-bottom:1px solid var(--gold-border);display:flex;justify-content:space-between;align-items:center}}
.r-item-lbl{{font-family:'Rajdhani',sans-serif;font-weight:700;font-size:11px;letter-spacing:2px;text-transform:uppercase}}
.r-sbadge{{font-family:'Rajdhani',sans-serif;font-weight:700;font-size:9px;letter-spacing:2px;padding:2px 8px;border:1px solid}}
.r-sbadge.fatal{{color:var(--fatal);border-color:#8B2020}}.r-sbadge.warning{{color:var(--warning);border-color:#8B4A20}}.r-sbadge.pass{{color:var(--pass);border-color:#2a6b2a}}.r-sbadge.note{{color:var(--gold-dim);border-color:var(--gold-border)}}.r-sbadge.info{{color:var(--gray);border-color:var(--gray)}}
.r-item-body{{padding:10px 14px;font-size:12px;opacity:.82;line-height:1.7}}
.r-finding{{border:1px solid var(--gold-border);margin-bottom:10px;background:#0a0a0a;position:relative;overflow:hidden}}
.r-finding::after{{content:'';position:absolute;top:0;left:0;width:3px;height:100%}}
.r-finding.t1::after{{background:var(--tier1)}}.r-finding.t2::after{{background:var(--tier2)}}.r-finding.t3::after{{background:var(--tier3)}}
.r-fhdr{{padding:8px 14px;border-bottom:1px solid var(--gold-border);display:flex;justify-content:space-between;align-items:center}}
.r-fttl{{font-family:'Rajdhani',sans-serif;font-weight:700;font-size:11px;letter-spacing:2px;text-transform:uppercase}}
.r-tbadge{{font-family:'Rajdhani',sans-serif;font-weight:700;font-size:9px;letter-spacing:2px;padding:2px 8px;border:1px solid}}
.r-tbadge.t1{{color:var(--tier1);border-color:var(--tier1)}}.r-tbadge.t2{{color:var(--tier2);border-color:var(--tier2)}}.r-tbadge.t3{{color:var(--tier3);border-color:var(--tier3)}}
.r-fbody{{padding:10px 14px;font-size:12px;opacity:.82;line-height:1.7}}
.r-subs{{margin-top:8px;padding-left:12px;border-left:1px solid var(--gold-border)}}
.r-sub{{color:var(--gold-dim);font-size:11px;margin-bottom:4px}}.r-sub::before{{content:'\\2713  ';color:var(--gold)}}
.r-witness{{border-left:3px solid var(--gold);padding:12px 16px;margin:16px 0;background:rgba(201,168,76,.04);font-size:13px;line-height:1.8}}
.seal{{border:1px solid var(--gold);padding:20px;margin-top:28px;background:#0a0a0a;position:relative;box-shadow:0 0 20px rgba(201,168,76,.15)}}
.seal::before{{content:'\\03A9  SEALED RECEIPT';position:absolute;top:-10px;left:16px;background:#0a0a0a;padding:0 8px;font-family:'Rajdhani',sans-serif;font-weight:700;font-size:10px;letter-spacing:4px;color:var(--gold)}}
.seal-row{{color:var(--gray);font-size:11px;margin-bottom:4px}}.seal-row span{{color:var(--gold-dim)}}
.seal-status{{font-family:'Rajdhani',sans-serif;font-weight:700;font-size:12px;letter-spacing:4px;color:var(--gold);text-align:right;margin-top:12px;text-shadow:0 0 12px rgba(240,192,64,0.5)}}
.footer{{text-align:center;padding:20px;border-top:1px solid var(--gold-border);margin-top:30px;font-family:'Rajdhani',sans-serif;font-size:10px;letter-spacing:4px;color:var(--gold-dim);text-transform:uppercase}}
.footer span{{color:var(--gold)}}
</style>
</head>
<body>
<div class="hero">
  <div class="omega">{_escape(brand.logo_text)}</div>
  <div class="brand">VERITAS DOCS</div>
  <div class="receipt-label">PROVENANCE RECEIPT</div>
</div>
<div class="content">
  <div class="meta-grid">
    <span class="meta-lbl">Trace ID</span><span class="meta-val">{_escape(output.trace_id)}</span>
    <span class="meta-lbl">Document</span><span class="meta-val">{_escape(doc.title)}</span>
    <span class="meta-lbl">Source</span><span class="meta-val">{_escape(doc.source_name)}</span>
    <span class="meta-lbl">Source Hash</span><span class="meta-val">{_escape(doc.source_hash[:32])}...</span>
    <span class="meta-lbl">Operation</span><span class="meta-val">{_escape(output.operation.upper())}</span>
    <span class="meta-lbl">Version</span><span class="meta-val">{_escape(output.version)}</span>
    <span class="meta-lbl">Generated</span><span class="meta-val">{gen_date}</span>
    {f'<span class="meta-lbl">AI Model</span><span class="meta-val">{_escape(output.model)}</span>' if output.model else ''}
    <span class="meta-lbl">Classification</span><span class="meta-val" style="color:{brand.confidentiality_color}">{_escape(brand.confidentiality.upper())}</span>
  </div>

  <div class="section-title">EXPORTED FORMATS</div>
  <table>
    <thead><tr><th>Format</th><th>Filename</th><th>SHA-256</th></tr></thead>
    <tbody>{format_rows}</tbody>
  </table>

  {ai_section}

  <div class="seal">
    <div class="seal-row"><span>TRACE ID:</span> &nbsp; {_escape(output.trace_id)}</div>
    <div class="seal-row"><span>DOCUMENT:</span> &nbsp; {_escape(doc.title)}</div>
    <div class="seal-row"><span>FORMATS:</span> &nbsp; {_escape(', '.join(f.upper() for f in output.formats.keys()))}</div>
    <div class="seal-row"><span>SOURCE HASH:</span> &nbsp; {_escape(doc.source_hash[:32])}...</div>
    <div class="seal-status">STATUS: SEALED — {_escape(output.trace_id)} ✓</div>
  </div>

  <div class="footer"><span>Ω</span> &nbsp; VERITAS DOCS &nbsp;·&nbsp; PROVENANCE RECEIPT &nbsp;·&nbsp; <span>v1.0</span></div>
</div>

<!-- Machine-readable provenance data -->
<script type="application/json" id="veritas-provenance">
{provenance_json}
</script>
</body>
</html>'''

    os.makedirs(output_path.parent, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return output_path
