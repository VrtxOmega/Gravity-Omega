"""
VERITAS Docs — Format Router
==============================
Orchestrates multi-format export: takes a VeritasDocument + requested formats,
routes to each engine, collects outputs, generates receipt, returns VeritasDocsOutput.
"""

import os
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from models import (
    BrandPreset, VeritasDocument, VeritasDocsOutput,
    generate_trace_id, hash_file, SUPPORTED_FORMATS, FORMAT_EXTENSIONS
)

from engines import pdf_engine, docx_engine, html_engine
from engines import md_engine, txt_engine, slide_engine, receipt_engine


# ── ENGINE REGISTRY ──────────────────────────────────────────
ENGINES = {
    "pdf": pdf_engine,
    "docx": docx_engine,
    "html": html_engine,
    "md": md_engine,
    "txt": txt_engine,
    "slides": slide_engine,
}


def get_output_dir() -> Path:
    """Get the output directory for documents."""
    base = Path(__file__).resolve().parent.parent / "output" / "documents"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_receipt_dir() -> Path:
    """Get the output directory for receipts."""
    base = Path(__file__).resolve().parent.parent / "output" / "receipts"
    base.mkdir(parents=True, exist_ok=True)
    return base


def export(doc: VeritasDocument, formats: list, brand: BrandPreset = None,
           operation: str = "create") -> VeritasDocsOutput:
    """
    Export a document to one or more formats.

    Args:
        doc: The document to export
        formats: List of format strings (e.g., ["pdf", "html", "md"])
        brand: Brand preset to use (defaults to VERITAS)
        operation: "create", "analyze", or "brief"

    Returns:
        VeritasDocsOutput with all paths and hashes
    """
    if brand is None:
        brand = BrandPreset()

    # Validate formats
    valid_formats = [f for f in formats if f in SUPPORTED_FORMATS]
    if not valid_formats:
        raise ValueError(f"No valid formats. Choose from: {SUPPORTED_FORMATS}")

    # Ensure source hash
    if not doc.source_hash:
        doc.compute_source_hash()

    # Generate trace ID
    trace_id = generate_trace_id()

    # Build safe filename base
    safe_title = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in doc.title)
    safe_title = safe_title[:50].rstrip('_')

    # Output paths
    output = VeritasDocsOutput(
        trace_id=trace_id,
        document_id=doc.id,
        operation=operation,
        version=doc.version,
        model=None,
    )

    doc_dir = get_output_dir()
    receipt_dir = get_receipt_dir()

    # Run each engine
    for fmt in valid_formats:
        engine = ENGINES.get(fmt)
        if engine is None:
            continue

        ext = FORMAT_EXTENSIONS.get(fmt, f".{fmt}")
        out_path = doc_dir / f"{safe_title}_{trace_id}{ext}"

        try:
            engine.render(doc, brand, out_path)
            output.formats[fmt] = str(out_path)
            output.hashes[fmt] = hash_file(out_path)
        except Exception as e:
            output.formats[fmt] = f"ERROR: {str(e)}"
            output.hashes[fmt] = "ERROR"

    # Always generate receipt
    receipt_path = receipt_dir / f"{trace_id}_receipt.html"
    receipt_engine.render(doc, output, brand, receipt_path)
    output.receipt_path = str(receipt_path)
    output.receipt_hash = hash_file(receipt_path)

    return output


def export_single(doc: VeritasDocument, fmt: str,
                  brand: BrandPreset = None) -> VeritasDocsOutput:
    """Convenience: export to a single format."""
    return export(doc, [fmt], brand)


def export_all(doc: VeritasDocument,
               brand: BrandPreset = None) -> VeritasDocsOutput:
    """Export to all supported formats."""
    return export(doc, SUPPORTED_FORMATS, brand)
