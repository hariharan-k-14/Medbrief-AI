import os
import base64
import toml
from pathlib import Path
from PIL import Image

def extract_text_from_image(image_input):
    """
    Extract medical report text from an image file (PNG, JPG, JPEG, WEBP)
    using Groq Vision OCR with pytesseract fallback.
    """
    try:
        image_bytes = None
        file_path = None

        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                return "Error: Image file does not exist"
            file_path = image_input
            with open(image_input, "rb") as f:
                image_bytes = f.read()
        elif hasattr(image_input, "read"):
            image_bytes = image_input.read()
            if hasattr(image_input, "seek"):
                image_input.seek(0)
        elif isinstance(image_input, bytes):
            image_bytes = image_input

        if not image_bytes:
            return "Could not read image file data"

        # Check size (max 20MB)
        if len(image_bytes) > 20 * 1024 * 1024:
            return "Image file exceeds 20MB limit"

        # Primary OCR: Groq Vision AI OCR (qwen/qwen3.8-27b)
        groq_api_key = os.environ.get("GROQ_API_KEY", "")
        if not groq_api_key:
            secrets_path = Path(".streamlit/secrets.toml")
            if secrets_path.exists():
                try:
                    secrets_dict = toml.load(secrets_path)
                    groq_api_key = secrets_dict.get("GROQ_API_KEY", "")
                except Exception:
                    pass

        extracted_text = ""

        if groq_api_key:
            try:
                import groq
                client = groq.Groq(api_key=groq_api_key)
                b64_str = base64.b64encode(image_bytes).decode("utf-8")
                
                mime_type = "image/png"
                if file_path:
                    ext = Path(file_path).suffix.lower()
                    if ext in [".jpg", ".jpeg"]:
                        mime_type = "image/jpeg"
                    elif ext == ".webp":
                        mime_type = "image/webp"

                response = client.chat.completions.create(
                    model="qwen/qwen3.8-27b",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Perform high-accuracy medical document OCR on this report image. Extract and transcribe all text, patient details, lab test names, numerical values, units, reference ranges, and clinical notes verbatim."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mime_type};base64,{b64_str}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=4096
                )
                if response.choices and response.choices[0].message.content:
                    extracted_text = response.choices[0].message.content.strip()
            except Exception as e:
                print(f"[OCR] Groq Vision attempt warning: {e}")

        # Fallback: pytesseract
        if not extracted_text or len(extracted_text.strip()) < 10:
            try:
                import pytesseract
                import io
                img = Image.open(io.BytesIO(image_bytes))
                ocr_txt = pytesseract.image_to_string(img)
                if ocr_txt and len(ocr_txt.strip()) >= 10:
                    extracted_text = ocr_txt
            except Exception:
                pass

        if not extracted_text or not extracted_text.strip():
            return "Could not extract text from image. Please make sure the photo is clear and contains readable medical report text."

        return extracted_text

    except Exception as e:
        return f"Error extracting text from image: {str(e)}"
