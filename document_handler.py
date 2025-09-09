# document_handler.py
import pdfplumber
import warnings
import logging

# Suppress pdfminer warnings about invalid float values
warnings.filterwarnings("ignore", category=UserWarning)
logging.getLogger("pdfminer").setLevel(logging.ERROR)

def load_pdf(file_path):
    """
    Load a PDF and extract all text.
    
    Args:
        file_path (str): Path to the PDF file.
        
    Returns:
        str: Full text extracted from the PDF.
    """
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:  # Avoid None
                text += page_text + "\n"
    return text
