# Document_Handler.py
import os
from typing import List, Dict
import chardet
from langchain_community.document_loaders import PyPDFLoader
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import io
from docx import Document
import cantools
import xml.etree.ElementTree as ET
 
# --------------------------
# Text/Document loaders
# --------------------------
def load_txt(path: str) -> str:
    with open(path, "rb") as f:
        raw_data = f.read()
    result = chardet.detect(raw_data)
    encoding = result['encoding'] or 'utf-8'
    return raw_data.decode(encoding, errors='ignore')
 
def load_md(path: str) -> str:
    return load_txt(path)
 
def load_docx(path: str) -> str:
    doc = Document(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)
 
def load_pdf_text_only(path: str) -> str:
    loader = PyPDFLoader(path)
    docs = loader.load()
    return "\n".join([doc.page_content for doc in docs])
 
def extract_diagram_text_from_pdf(path: str) -> List[Dict]:
    extracted_chunks = []
    try:
        doc = fitz.open(path)
        for page_num, page in enumerate(doc, start=1):
            for img in page.get_images(full=True):
                xref = img[0]
                base_img = doc.extract_image(xref)
                image_bytes = base_img["image"]
                image = Image.open(io.BytesIO(image_bytes))
                text = pytesseract.image_to_string(image)
                if text.strip():
                    extracted_chunks.append({
                        "text": f"[FIGURE] {text.strip()}",
                        "source": os.path.basename(path),
                        "page": page_num,
                        "type": "figure_text"
                    })
    except Exception as e:
        print(f"Error extracting diagram text from PDF {path}: {e}")
    return extracted_chunks
 
def load_pdf(path: str) -> Dict:
    text_content = load_pdf_text_only(path)
    figure_chunks = extract_diagram_text_from_pdf(path)
    chunks = [{
        "text": text_content,
        "source": os.path.basename(path),
        "page": None,
        "type": "paragraph"
    }]
    chunks.extend(figure_chunks)
    return {
        "path": path,
        "name": os.path.basename(path),
        "chunks": chunks
    }
 
# --------------------------
# DBC loader
# --------------------------
def load_dbc(path: str) -> Dict:
    try:
        db = cantools.database.load_file(path)
    except Exception as e:
        raise ValueError(f"Failed to load DBC file {path}: {e}")
 
    chunks = []
    for msg in db.messages:
        msg_text = f"Message: {msg.name} (ID: {hex(msg.frame_id)})\nSignals:"
        for sig in msg.signals:
            sig_text = (
                f" - {sig.name}: start_bit={sig.start}, length={sig.length}, "
                f"byte_order={'Motorola' if sig.byte_order == 1 else 'Intel'}, "
                f"value_type={'Signed' if sig.is_signed else 'Unsigned'}, "
                f"scale={sig.scale}, offset={sig.offset}, "
                f"min={sig.minimum}, max={sig.maximum}, "
                f"unit={sig.unit}, "
                f"enumeration={getattr(sig, 'enum', None)}, "
                f"description={getattr(sig, 'comment', None)}"
            )
            msg_text += "\n" + sig_text
 
        chunks.append({
            "text": msg_text,
            "source": os.path.basename(path),
            "page": None,
            "type": "dbc_message"
        })
 
    return {
        "path": path,
        "name": os.path.basename(path),
        "chunks": chunks
    }
 
# --------------------------
# CDD loader
# --------------------------
def load_cdd(path: str) -> Dict:
    """
    Load any CDD XML file and recursively extract all elements.
    Each element becomes a chunk with path, attributes, and text.
    """
    import xml.etree.ElementTree as ET
 
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except Exception as e:
        raise ValueError(f"Failed to load CDD file {path}: {e}")
 
    chunks = []
 
    def extract_element(elem, parent_path=""):
        tag = elem.tag.split("}")[-1]  # remove namespace
        full_path = f"{parent_path}/{tag}" if parent_path else tag
 
        # Combine text and attributes
        text = (elem.text or "").strip()
        attrs = ", ".join([f"{k}={v}" for k, v in elem.attrib.items()])
        content = f"Path: {full_path}\nAttributes: {attrs}\nText: {text}" if text or attrs else None
 
        if content:
            chunks.append({
                "text": content,
                "source": os.path.basename(path),
                "page": None,
                "type": "cdd_element"
            })
 
        # Recurse into children
        for child in elem:
            extract_element(child, full_path)
 
    extract_element(root)
 
    return {
        "path": path,
        "name": os.path.basename(path),
        "chunks": chunks
    }
 
# --------------------------
# ARXML loader
# --------------------------
def load_arxml(path: str) -> Dict:
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except Exception as e:
        raise ValueError(f"Failed to load ARXML file {path}: {e}")
 
    chunks = []
 
    def extract_elements(elem, parent_name=""):
        tag_name = elem.tag.split("}")[-1]
        full_name = f"{parent_name}/{tag_name}" if parent_name else tag_name
        if elem.text and elem.text.strip():
            chunks.append({
                "text": f"{full_name}: {elem.text.strip()}",
                "source": os.path.basename(path),
                "page": None,
                "type": "arxml_element"
            })
        for child in elem:
            extract_elements(child, full_name)
 
    extract_elements(root)
    return {
        "path": path,
        "name": os.path.basename(path),
        "chunks": chunks
    }
 
# --------------------------
# Generic loader
# --------------------------
def load_document(path: str) -> Dict:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        text = load_docx(path)
        chunks = [{"text": text, "source": os.path.basename(path), "page": None, "type": "paragraph"}]
    elif ext in [".md", ".markdown"]:
        text = load_md(path)
        chunks = [{"text": text, "source": os.path.basename(path), "page": None, "type": "paragraph"}]
    elif ext == ".pdf":
        return load_pdf(path)
    elif ext == ".txt":
        text = load_txt(path)
        chunks = [{"text": text, "source": os.path.basename(path), "page": None, "type": "paragraph"}]
    elif ext == ".dbc":
        return load_dbc(path)
    elif ext == ".cdd":
        return load_cdd(path)
    elif ext == ".arxml":
        return load_arxml(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
 
    return {
        "path": path,
        "name": os.path.basename(path),
        "chunks": chunks
    }