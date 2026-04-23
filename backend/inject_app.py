import sys, os

APP_PATH = "c:/Veritas_Lab/gravity-omega-v2/backend/web_server.py"

with open(APP_PATH, "r", encoding="utf-8") as f:
    orig = f.read()

INJECT = """
# ═══ VERITAS ANALYZER ENDPOINT ═══
import io, json, re, requests, uuid
from werkzeug.utils import secure_filename
from flask import request, jsonify

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

OLLAMA_URL = "http://127.0.0.1:11434"
MAX_CHARS = 14_000

SYSTEM_PROMPT = \"\"\"You are the VERITAS structured analysis engine for Gravity Omega.
Analyze the document and return a single JSON report object.

RETURN ONLY RAW JSON. No markdown. No backticks. No explanation. Just the JSON.

Required schema:
{
  "title": "Document title — concise and descriptive",
  "subtitle": "One-line description of document type and purpose",
  "session_id": "0xABCD-TOPIC-AUDIT",
  "mode": "Analysis mode e.g. Investigative Review · Evidence Extraction",
  "sections": [
    {
      "number": "01",
      "title": "UPPERCASE SECTION TITLE",
      "intro": "One sentence framing this section.",
      "items": [
        {
          "label": "Item label",
          "status": "fatal|warning|pass|note|info",
          "content": "Precise analytical content. One to three sentences.",
          "note": null,
          "verdict": null
        }
      ]
    }
  ],
  "feasible_set": [
    {
      "number": "01",
      "title": "Finding or conclusion title",
      "tier": 1,
      "content": "Description of this finding.",
      "subitems": ["Supporting detail one", "Supporting detail two"]
    }
  ],
  "witness": "2-3 sentence analytical summary. Declarative, precise, no hedging on confirmed facts.",
  "trace_id": "Omega-1.0-TOPIC-0x99A"
}

Rules:
- 2 to 5 sections. Each section 1 to 4 items.
- 3 to 7 feasible_set items representing key conclusions.
- tier: 1=confirmed fact or direct evidence, 2=well-supported conclusion, 3=inference or leading hypothesis
- status: fatal=critical issue or failure, warning=concern or risk, pass=verified or confirmed, note=supplementary, info=neutral
- subitems: 2-3 strings per item
- note and verdict: null if not applicable
- Be concise and analytical. Never verbose.\"\"\"

def extract_text(file_bytes, filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in {".txt", ".md", ".csv"}:
        return file_bytes.decode("utf-8", errors="replace")
    if ext == ".json":
        text = file_bytes.decode("utf-8", errors="replace")
        try: return json.dumps(json.loads(text), indent=2)
        except: return text
    if ext == ".docx":
        if not DOCX_AVAILABLE: raise RuntimeError("python-docx not installed.")
        doc = DocxDocument(io.BytesIO(file_bytes))
        return "\\n".join(p.text for p in doc.paragraphs if p.text.strip())
    if ext == ".pdf":
        if not PDF_AVAILABLE: raise RuntimeError("pdfplumber not installed.")
        text_parts = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages[:40]:
                t = page.extract_text()
                if t: text_parts.append(t)
        return "\\n".join(text_parts)
    raise ValueError(f"Unsupported file type: {ext}")

def call_ollama(text, model):
    truncated = text if len(text) <= MAX_CHARS else text[:MAX_CHARS] + "\\n\\n[Content truncated]"
    payload = {
        "model": model, "stream": False, "format": "json",
        "options": {"temperature": 0.15, "num_predict": 3500},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this document and return the JSON report:\\n\\n{truncated}"}
        ]
    }
    resp = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=180)
    resp.raise_for_status()
    raw = resp.json().get("message", {}).get("content", "")
    clean = re.sub(r"^```json\\s*", "", raw.strip())
    clean = re.sub(r"```\\s*$", "", clean).strip()
    return json.loads(clean)

@app.route("/api/analyze_document", methods=["POST"])
def analyze_document():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400
    
    f = request.files["file"]
    model = request.form.get("model", "qwen3:8b").strip()
    filename = secure_filename(f.filename or "upload.txt")
    
    try:
        file_bytes = f.read()
        raw_text = extract_text(file_bytes, filename)
    except Exception as e:
        return jsonify({"error": f"Extraction failed: {str(e)}"}), 422
    
    try:
        report_data = call_ollama(raw_text, model)
        report_data["_meta"] = {"source_file": filename, "model": model, "trace": f"Omega-1.0-{str(uuid.uuid4())[:8].upper()}"}
        return jsonify(report_data)
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

"""

if "VERITAS ANALYZER ENDPOINT" not in orig:
    target = "if __name__ == '__main__':"
    idx = orig.find(target)
    if idx > -1:
        new_content = orig[:idx] + INJECT + orig[idx:]
        with open(APP_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Successfully injected.")
    else:
        print("Target 'if __name__' not found")
else:
    print("Already injected.")
