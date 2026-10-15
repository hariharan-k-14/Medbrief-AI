import pdfplumber
try:
    import pypdf
except ImportError:
    pypdf = None

from config.app_config import MAX_PDF_PAGES
from utils.validators import validate_pdf_file, validate_pdf_content

def extract_text_from_pdf(pdf_file):
    """Extract and validate text from PDF file or file path using pdfplumber + pypdf fallback."""
    try:
        # Validate file size and type
        is_valid, error = validate_pdf_file(pdf_file)
        if not is_valid:
            return error

        text = ""

        # 1. Primary extraction with pdfplumber
        try:
            with pdfplumber.open(pdf_file) as pdf:
                if len(pdf.pages) > MAX_PDF_PAGES:
                    return f"PDF exceeds maximum page limit of {MAX_PDF_PAGES}"
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
        except Exception:
            text = ""

        # 2. Fallback extraction with pypdf if pdfplumber extracted empty or minimal text
        if (not text or len(text.strip()) < 10) and pypdf is not None:
            try:
                reader = pypdf.PdfReader(pdf_file)
                if len(reader.pages) > MAX_PDF_PAGES:
                    return f"PDF exceeds maximum page limit of {MAX_PDF_PAGES}"
                pypdf_text = ""
                for page in reader.pages:
                    p_text = page.extract_text()
                    if p_text:
                        pypdf_text += p_text + "\n"
                if pypdf_text.strip():
                    text = pypdf_text
            except Exception:
                pass

        if not text or not text.strip():
            return "Could not read text from PDF. Please make sure the PDF file contains readable text."

        # Validate extracted content
        is_valid, error = validate_pdf_content(text)
        if not is_valid:
            return error
            
        return text
    except Exception as e:
        return f"Error extracting text from PDF: {str(e)}"
