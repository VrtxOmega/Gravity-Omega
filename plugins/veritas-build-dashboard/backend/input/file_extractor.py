import os
import json
import csv
import io
from pathlib import Path

def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Extracts text from various file formats.
    Supported: .txt, .md, .csv, .json, .pdf, .docx
    """
    ext = Path(filename).suffix.lower()
    
    if ext == '.pdf':
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            text = []
            for page in reader.pages:
                text.append(page.extract_text() or "")
            return "\n\n".join(text)
        except Exception as e:
            return f"Error extracting PDF text: {str(e)}"
            
    elif ext == '.docx':
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            text = [para.text for para in doc.paragraphs]
            return "\n".join(text)
        except Exception as e:
            return f"Error extracting DOCX text: {str(e)}"
            
    elif ext == '.csv':
        try:
            # Convert CSV to Markdown table
            content = file_bytes.decode("utf-8", errors="replace")
            reader = csv.reader(io.StringIO(content))
            rows = list(reader)
            if not rows:
                return "Empty CSV"
                
            md_table = []
            # Header
            md_table.append("| " + " | ".join(rows[0]) + " |")
            # Separator
            md_table.append("|" + "|".join(["---" for _ in rows[0]]) + "|")
            # Body
            for row in rows[1:]:
                #Pad row if needed
                if len(row) < len(rows[0]):
                    row.extend([""] * (len(rows[0]) - len(row)))
                md_table.append("| " + " | ".join(row) + " |")
                
            return "\n".join(md_table)
        except Exception as e:
            return f"Error extracting CSV text: {str(e)}"
            
    elif ext == '.json':
        try:
            content = file_bytes.decode("utf-8", errors="replace")
            data = json.loads(content)
            return "```json\n" + json.dumps(data, indent=2) + "\n```"
        except Exception as e:
            return f"Error parsing JSON: {str(e)}"
            
    else:
        # Default text fallback (.md, .txt, etc.)
        return file_bytes.decode("utf-8", errors="replace")
