"""
GOLIATH HUNTER — OMEGA_DOSSIER v1.0
=====================================
Auto-generates a structured intelligence dossier.
Wraps the existing veritas_pdf.py (no edits to that file).
Falls back to Markdown if PDF dependencies are unavailable.

Sections:
  1. Executive Summary
  2. Entity Map (top co-occurring entities)
  3. Timeline of Knowledge
  4. Contradiction Vectors (Audit of Omission)
  5. Evidence Appendix (all sealed nodes)
"""

import json
import os
import sys
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List

from .omega_pattern_engine import PatternReport, ContradictionVector
from .omega_province import SealedProof, OmegaProvince
from .omega_array import IntelNode


class OmegaDossier:
    """
    Generates the final intelligence dossier from a completed hunt run.
    Outputs Markdown (always) + PDF (if veritas_pdf available).
    """

    def __init__(self, output_dir: Path, run_id: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id

    def generate(self,
                 pattern_report: PatternReport,
                 sealed_proofs: List[SealedProof],
                 all_nodes: List[IntelNode],
                 audit_of_omission: str,
                 lead_summary: str = "",
                 break_layer_md: str = "") -> Path:
        """Render and save the full dossier. Returns path to the markdown file."""

        md = self._render_markdown(pattern_report, sealed_proofs,
                                   all_nodes, audit_of_omission,
                                   lead_summary, break_layer_md)

        md_path = self.output_dir / f"DOSSIER_{self.run_id}.md"
        md_path.write_text(md, encoding="utf-8")
        print(f"[DOSSIER] Markdown saved → {md_path}")

        # Attempt PDF generation via existing veritas_pdf module
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from veritas_pdf import generate_pdf  # type: ignore
            pdf_path = self.output_dir / f"DOSSIER_{self.run_id}.pdf"
            generate_pdf(md, str(pdf_path))
            print(f"[DOSSIER] PDF saved → {pdf_path}")
        except Exception as e:
            print(f"[DOSSIER] PDF generation skipped ({e}) — Markdown is the output")

        return md_path

    def _render_markdown(self,
                         report: PatternReport,
                         proofs: List[SealedProof],
                         nodes: List[IntelNode],
                         audit: str,
                         lead_summary: str = "",
                         break_layer_md: str = "") -> str:

        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        dossier_hash = hashlib.sha256(
            f"{self.run_id}{ts}".encode()).hexdigest()[:16].upper()

        lines = [
            f"# GRAVITY OMEGA INTELLIGENCE DOSSIER",
            f"**Run ID:** `{self.run_id}`  ",
            f"**Generated:** {ts}  ",
            f"**Dossier Seal:** `{dossier_hash}`  ",
            f"**Seeds:** {', '.join(report.seeds_searched)}",
            "",
            "---",
            "",
            "## 1. Executive Summary",
            "",
            f"- **Intel Nodes Harvested:** {report.nodes_analyzed}",
            f"- **Entities Discovered:** {sum(report.entity_type_summary.values())}",
            f"- **Contradiction Vectors:** {len(report.contradiction_vectors)}",
            f"- **Sealed Proofs (passed strict necessity):** {len(proofs)}",
            f"- **New Seeds Identified:** {len(report.new_seeds)}",
            "",
        ]

        # Contradiction summary in exec section
        if proofs:
            lines += [
                "### Key Findings",
                "",
            ]
            for p in proofs[:5]:
                lines.append(
                    f"- **{p.vector.entity}** — "
                    f"{p.vector.claim_a[:80]}... contradicted by: "
                    f"{p.vector.claim_b[:80]}..."
                )
            lines.append("")

        lines += [
            "---",
            "",
            "## 2. Entity Intelligence Map",
            "",
            "Top entities discovered across all sources, ranked by connection density:",
            "",
            "| Rank | Entity | Connections | Type |",
            "|:-----|:-------|:-----------|:-----|",
        ]
        for i, (ent, deg) in enumerate(report.top_entities[:20], 1):
            lines.append(f"| {i} | {ent} | {deg} | — |")
        lines += ["", ""]

        lines += [
            "### Self-Directed Next Targets",
            "",
            "The Pattern Engine identified these entities for the next search cycle:",
            "",
        ]
        for seed in report.new_seeds:
            lines.append(f"- `{seed}`")
        lines += ["", "---", ""]

        lines += [
            "## 3. Evidence Type Breakdown",
            "",
            "| Type | Count |",
            "|:-----|:------|",
        ]
        for etype, count in sorted(
                report.entity_type_summary.items(), key=lambda x: -x[1]):
            lines.append(f"| {etype} | {count} |")
        lines += ["", "---", ""]

        lines += [
            "## 4. Audit of Omission",
            "",
            "```",
            audit,
            "```",
            "",
            "---",
            "",
            "## 5. Contradiction Proofs (Sealed)",
            "",
        ]
        if proofs:
            for p in proofs:
                lines += [
                    f"### Proof `{p.proof_id}`",
                    f"- **Entity:** {p.vector.entity}",
                    f"- **Tier:** {p.vector.tier}",
                    f"- **Public Claim:** {p.vector.claim_a}",
                    f"- **Contradicting Evidence:** {p.vector.claim_b}",
                    f"- **Source A:** [{p.vector.node_a_url}]({p.vector.node_a_url})",
                    f"- **Source B:** [{p.vector.node_b_url}]({p.vector.node_b_url})",
                    f"- **Seal Hash:** `{p.seal_hash}`",
                    f"- **Confidence:** {p.gate_confidence:.2f}",
                    "",
                ]
        else:
            lines += [
                "_No contradiction vectors passed strict necessity in this run._",
                "_Increase search depth or refine seeds to surface quantitative evidence._",
                "",
            ]

        lines += [
            "---",
            "",
            "## 5. 🔴 Break Layer — Adversarial Falsification",
            "",
            "> *Anti-bias gate: What would disprove this? What doesn't fit? Where are we assuming?*",
            "",
        ]
        if break_layer_md:
            # Embed the break report inline (skip the H1 title line, already in section header)
            br_body = "\n".join(break_layer_md.split("\n")[3:])
            lines.append(br_body[:4000])
        else:
            lines += [
                "_Break Layer not run. Re-run without --dry-run to enable._",
                "",
            ]

        lines += [
            "---",
            "",
            "## 6. Lead Content — Full Text Excerpts",
            "",
            "> The Lead Fetcher read the full content of the highest-priority discovered URLs.",
            "> Each excerpt below is a direct quote of the first 600 characters of the fetched document.",
            "",
        ]
        if lead_summary and "Enriched nodes: 0" not in lead_summary:
            # Extract individual lead blocks from the summary
            blocks = lead_summary.split("## [")
            if len(blocks) > 1:
                for block in blocks[1:21]:  # max 20 leads in dossier
                    lines.append(f"### [{block[:120]}")
                    lines.append("")
            else:
                lines.append(lead_summary[:3000])
                lines.append("")
        else:
            lines += [
                "_No full-text content fetched in this run._",
                "_Run without `--dry-run` and with `--max-fetch N` to enable lead fetching._",
                "",
            ]

        lines += [
            "---",
            "",
            "## 7. Evidence Appendix",
            "",
            f"All {len(nodes)} harvested intel nodes, cryptographically sealed.",
            "",
            "| # | Source | Title | Seal (16) | Confidence | URL |",
            "|:--|:-------|:------|:----------|:-----------|:----|",
        ]
        for i, n in enumerate(nodes, 1):
            title = n.title[:40].replace("|", "–") if n.title else "—"
            url   = n.url[:60] if n.url else "—"
            lines.append(
                f"| {i} | {n.source} | {title} | `{n.sha256[:16]}` "
                f"| {n.confidence:.2f} | {url} |"
            )

        lines += [
            "",
            "---",
            "",
            f"*GOLIATH HUNTER v1.0 — Gravity Omega | Dossier Seal: `{dossier_hash}`*",
        ]

        return "\n".join(lines)
