import sys
import os
from pathlib import Path
import tempfile
import toml
from typing import Optional, List
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add src to python path
sys.path.insert(0, os.path.abspath("src"))

# Speed up transformers importlib package metadata distribution checks
import importlib.metadata
_orig_pkg_dist = importlib.metadata.packages_distributions
_pkg_dist_cache = None
def _cached_packages_distributions():
    global _pkg_dist_cache
    if _pkg_dist_cache is None:
        try:
            _pkg_dist_cache = _orig_pkg_dist()
        except Exception:
            _pkg_dist_cache = {}
    return _pkg_dist_cache
importlib.metadata.packages_distributions = _cached_packages_distributions

# Suppress Streamlit bare execution warnings when running server.py
import logging
logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)
logging.getLogger("streamlit.runtime.state.session_state_proxy").setLevel(logging.ERROR)
logging.getLogger("streamlit").setLevel(logging.ERROR)

# Load secrets into os.environ / st shim if needed
SECRETS_PATH = Path(".streamlit/secrets.toml")
secrets_dict = {}
if SECRETS_PATH.exists():
    try:
        secrets_dict = toml.load(SECRETS_PATH)
        for k, v in secrets_dict.items():
            os.environ[k] = str(v)
    except Exception as e:
        print(f"Warning: Could not parse secrets.toml: {e}")

# Inject lightweight shims for st.secrets, st.session_state, and st UI functions so existing services work cleanly
import streamlit as st

class SecretsShim(dict):
    def __getitem__(self, key):
        if key in os.environ:
            return os.environ[key]
        return super().__getitem__(key)

class SessionStateShim(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"'SessionStateShim' object has no attribute '{key}'")
    def __setattr__(self, key, value):
        self[key] = value
    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError(f"'SessionStateShim' object has no attribute '{key}'")

st.secrets = SecretsShim(secrets_dict)
st.session_state = SessionStateShim()
st.error = lambda msg, *args, **kwargs: print(f"[ERROR] {msg}")
st.warning = lambda msg, *args, **kwargs: print(f"[WARNING] {msg}")
st.info = lambda msg, *args, **kwargs: print(f"[INFO] {msg}")
st.success = lambda msg, *args, **kwargs: print(f"[SUCCESS] {msg}")

from auth.auth_service import AuthService
from agents.analysis_agent import AnalysisAgent
from agents.chat_agent import ChatAgent
from utils.pdf_extractor import extract_text_from_pdf
from utils.image_extractor import extract_text_from_image
from config.sample_data import SAMPLE_REPORT
from config.prompts import SPECIALIST_PROMPTS

app = FastAPI(title="MedBrief AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services
auth_service = AuthService()
analysis_agent = AnalysisAgent()
chat_agent = ChatAgent()

# In-memory vector store cache per session
session_vectorstores = {}
session_report_texts = {}

# Pydantic Schemas
class AuthRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None

class CreateSessionRequest(BaseModel):
    user_id: str
    title: Optional[str] = None

class ChatRequest(BaseModel):
    session_id: str
    prompt: str


@app.post("/api/auth/signup")
def signup(req: AuthRequest):
    if not req.email or not req.password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    name = req.name or req.email.split("@")[0]
    success, result = auth_service.sign_up(req.email, req.password, name)
    if not success:
        raise HTTPException(status_code=400, detail=str(result))
    return {"success": True, "data": result}


@app.post("/api/auth/login")
def login(req: AuthRequest):
    success, result = auth_service.sign_in(req.email, req.password)
    if not success:
        raise HTTPException(status_code=401, detail=str(result))
    return {"success": True, "user": result}


@app.get("/api/sessions")
def get_sessions(user_id: str):
    success, sessions = auth_service.get_user_sessions(user_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to fetch sessions")
    return {"success": True, "sessions": sessions}


@app.post("/api/sessions")
def create_session(req: CreateSessionRequest):
    success, session = auth_service.create_session(req.user_id, req.title)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create session")
    return {"success": True, "session": session}


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    success, err = auth_service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=500, detail=err or "Failed to delete session")
    session_vectorstores.pop(session_id, None)
    session_report_texts.pop(session_id, None)
    return {"success": True}


@app.get("/api/sessions/{session_id}/messages")
def get_messages(session_id: str):
    success, messages = auth_service.get_session_messages(session_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to fetch messages")
    return {"success": True, "messages": messages}


from utils.validators import validate_pdf_file, validate_pdf_content

@app.post("/api/analyze")
async def analyze_report(
    session_id: str = Form(...),
    use_sample: bool = Form(False),
    age: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    symptoms: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    report_text = ""

    if use_sample:
        report_text = SAMPLE_REPORT
    elif file:
        content = await file.read()
        filename = file.filename or "upload.pdf"
        ext = Path(filename).suffix.lower()
        if not ext:
            ext = ".png" if getattr(file, "content_type", "").startswith("image/") else ".pdf"

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"] or getattr(file, "content_type", "").startswith("image/"):
                extracted = extract_text_from_image(tmp_path)
            else:
                extracted = extract_text_from_pdf(tmp_path)
        finally:
            try:
                os.remove(tmp_path)
            except:
                pass

        if isinstance(extracted, str) and (
            extracted.startswith("Only medical reports are summarized")
            or extracted.startswith("Only reports can be summarized")
            or extracted.startswith(("Error", "PDF exceeds", "Could not extract", "File exceeds", "Only PDF", "Could not read"))
        ):
            raise HTTPException(status_code=400, detail=extracted)

        report_text = extracted
    else:
        raise HTTPException(status_code=400, detail="Please provide a PDF or Photo report file or use sample report")

    is_valid_report, report_err = validate_pdf_content(report_text)
    if not is_valid_report:
        raise HTTPException(status_code=400, detail="Only medical reports are summarized, upload a report")

    data = {
        "report": report_text,
        "age": age or "",
        "gender": gender or "",
        "symptoms": symptoms or ""
    }

    result = analysis_agent.analyze_report(data, SPECIALIST_PROMPTS["comprehensive_analyst"])
    if not result.get("success"):
        err_detail = result.get("error", "Analysis failed")
        raise HTTPException(status_code=400 if "Only medical reports are summarized" in err_detail else 500, detail=err_detail)

    analysis_content = result.get("content", "")

    # Save system report text metadata to Supabase messages
    system_msg = f"__REPORT_TEXT__\n{report_text}\n__END_REPORT_TEXT__"
    auth_service.save_chat_message(session_id, system_msg, role="system")
    auth_service.save_chat_message(session_id, analysis_content, role="assistant")

    # Cache report text & vectorstore in memory
    session_report_texts[session_id] = report_text
    try:
        vs = chat_agent.initialize_vector_store(report_text)
        session_vectorstores[session_id] = vs
    except Exception as e:
        print(f"Warning: Failed to initialize vectorstore: {e}")

    return {
        "success": True,
        "content": analysis_content,
        "model_used": result.get("model_used", "Groq"),
        "provider": result.get("provider", "Groq")
    }


@app.post("/api/chat")
def chat_followup(req: ChatRequest):
    session_id = req.session_id
    prompt = req.prompt.strip()

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    # Save user message
    auth_service.save_chat_message(session_id, prompt, role="user")

    # Retrieve context
    report_text = session_report_texts.get(session_id, "")
    vectorstore = session_vectorstores.get(session_id)

    if not report_text or not vectorstore:
        # Fetch system message from Supabase history
        success, messages = auth_service.get_session_messages(session_id)
        if success and messages:
            for msg in messages:
                if msg.get("role") == "system" and "__REPORT_TEXT__" in msg.get("content", ""):
                    content = msg.get("content", "")
                    start_idx = content.find("__REPORT_TEXT__\n") + len("__REPORT_TEXT__\n")
                    end_idx = content.find("\n__END_REPORT_TEXT__")
                    if start_idx > 0 and end_idx > start_idx:
                        report_text = content[start_idx:end_idx]
                        session_report_texts[session_id] = report_text
                        vectorstore = chat_agent.initialize_vector_store(report_text)
                        session_vectorstores[session_id] = vectorstore
                        break

    # Fetch messages history for context
    success, messages = auth_service.get_session_messages(session_id)
    chat_history = messages if success else []

    response_text = chat_agent.get_response(prompt, vectorstore, chat_history)

    # Save assistant message
    auth_service.save_chat_message(session_id, response_text, role="assistant")

    return {
        "success": True, 
        "response": response_text,
        "provider": "Gemini",
        "model_used": "Gemini AI"
    }


# Serve static web frontend with no-cache headers for dev hot-reload
@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
