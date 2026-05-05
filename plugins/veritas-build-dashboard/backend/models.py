"""
VERITAS Docs — Core Data Models
================================
Shared data structures used across all engines and routes.
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def generate_trace_id() -> str:
    """Generate a unique VERITAS Docs trace ID."""
    short = uuid.uuid4().hex[:8].upper()
    date = datetime.now().strftime("%Y-%m-%d")
    return f"VD-{date}-{short}"


def hash_content(content: str) -> str:
    """SHA-256 hash of string content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def hash_file(path: Path) -> str:
    """SHA-256 hash of file bytes."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class BrandPreset:
    """Branding configuration for document output."""
    name: str = "veritas"
    logo_text: str = "Ω"
    logo_font: str = "Orbitron"
    motto: str = (
        "VERITAS does not determine what is true. "
        "It determines what survives disciplined attempts to falsify it."
    )
    primary_color: str = "#C9A84C"
    bg_color: str = "#080808"
    header_font: str = "Rajdhani"
    body_font: str = "Share Tech Mono"
    display_font: str = "Orbitron"
    footer_text: str = "Built by RJ Lopez | VERITAS Framework"
    watermark: Optional[str] = None
    watermark_opacity: float = 0.15
    confidentiality: str = "internal"  # public | internal | confidential | restricted

    # Derived colors
    @property
    def gold(self) -> str:
        return self.primary_color

    @property
    def gold_bright(self) -> str:
        return "#F0C040"

    @property
    def gold_dim(self) -> str:
        return "#8B6B20"

    @property
    def obsidian(self) -> str:
        return self.bg_color

    @property
    def warm_white(self) -> str:
        return "#F5EDD6"

    @property
    def mid_gray(self) -> str:
        return "#333333"

    @property
    def confidentiality_label(self) -> str:
        labels = {
            "public": "",
            "internal": "INTERNAL USE ONLY",
            "confidential": "CONFIDENTIAL",
            "restricted": "RESTRICTED",
        }
        return labels.get(self.confidentiality, "")

    @property
    def confidentiality_color(self) -> str:
        colors = {
            "public": "#7ABD7A",
            "internal": "#4A90D9",
            "confidential": "#C9A84C",
            "restricted": "#FF4444",
        }
        return colors.get(self.confidentiality, "#666666")


@dataclass
class VeritasDocument:
    """Internal representation of any document in the system."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = "Untitled Document"
    subtitle: Optional[str] = None
    content: str = ""  # Markdown source
    source_type: str = "file"  # file | url | clipboard | voice | screenshot
    source_name: str = "unknown"
    source_hash: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "1.0"
    confidentiality: str = "internal"
    brand_preset: str = "veritas"
    tags: List[str] = field(default_factory=list)
    ai_analysis: Optional[dict] = None
    redactions: List[dict] = field(default_factory=list)
    citations: List[dict] = field(default_factory=list)
    charts: List[dict] = field(default_factory=list)

    def compute_source_hash(self):
        """Compute and cache the hash of the content."""
        self.source_hash = hash_content(self.content)
        return self.source_hash


@dataclass
class VeritasDocsOutput:
    """Every export operation produces this."""
    trace_id: str = field(default_factory=generate_trace_id)
    document_id: str = ""
    operation: str = "create"  # create | analyze | brief
    formats: Dict[str, str] = field(default_factory=dict)  # format -> file path
    hashes: Dict[str, str] = field(default_factory=dict)  # format -> SHA-256
    receipt_path: str = ""
    receipt_hash: str = ""
    version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    model: Optional[str] = None  # AI model if applicable

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "document_id": self.document_id,
            "operation": self.operation,
            "formats": self.formats,
            "hashes": self.hashes,
            "receipt_path": self.receipt_path,
            "receipt_hash": self.receipt_hash,
            "version": self.version,
            "created_at": self.created_at,
            "model": self.model,
        }


# ── SUPPORTED FORMATS ────────────────────────────────────────
SUPPORTED_FORMATS = ["pdf", "docx", "html", "md", "txt", "slides"]

FORMAT_LABELS = {
    "pdf": "PDF",
    "docx": "DOCX",
    "html": "HTML",
    "md": "Markdown",
    "txt": "Plain Text",
    "slides": "Slide Deck",
}

FORMAT_EXTENSIONS = {
    "pdf": ".pdf",
    "docx": ".docx",
    "html": ".html",
    "md": ".md",
    "txt": ".txt",
    "slides": "_slides.html",
}
