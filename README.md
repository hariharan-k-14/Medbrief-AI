# 🩺 MedBrief AI

AI Agent to analyze patient medical reports (PDF & Images) and provide detailed health insights with RAG-powered interactive follow-up chat.

<p align="center">
  <a href="#-features">Features</a> |
  <a href="#%EF%B8%8F-tech-stack">Tech Stack</a> |
  <a href="#-installation">Installation</a> |
  <a href="#-project-structure">Project Structure</a> |
  <a href="#-contributing">Contributing</a> |
  <a href="#-license">License</a>
</p>

---

## 🌟 Features

- **Agent-based Architecture**:
  - **Analysis Agent**: Medical report analysis with structured formatting, health metric extraction, and specialized medical prompts.
  - **Chat Agent**: RAG-powered follow-up Q&A over patient reports using FAISS vector search and HuggingFace embeddings.
  - **Multi-Model Cascade & Key Fallback**: Automatic failover across Groq model chains and Google Gemini API with API key rotation (`KeyFallbackManager`).
- **Multi-Format Report Support**:
  - **PDF Reports**: Upload up to 20MB, max 50 pages text extraction via `pdfplumber` and `pypdf`.
  - **Report Images**: OCR text extraction for `PNG`, `JPG`, `JPEG`, `WEBP`, `BMP`, and `TIFF` medical report scans.
  - **Medical Content Validation**: Strict validation to ensure only medical reports are processed.
  - **Sample Medical Report**: Built-in sample report for instant testing.
- **Dual User Interface Options**:
  - **FastAPI + Modern Web App**: Single-page application (HTML5/CSS3/Vanilla JS) with dark mode, real-time status notifications, drag-and-drop upload, and session sidebar.
  - **Streamlit Application**: Interactive dashboard interface (`src/main.py`).
- **Authentication & Persistence**:
  - **Supabase Auth**: Email/password sign up and sign in.
  - **Session Management**: Persistent chat sessions, medical report text caching, and full message history stored in PostgreSQL via Supabase.

---

## 🛠️ Tech Stack

- **Backend / API**: FastAPI, Uvicorn, Python 3.8+
- **Frontend**:
  - **Modern Web Interface**: Vanilla JavaScript, CSS3 (Glassmorphism, CSS Variables, Dark Theme), HTML5
  - **Streamlit Interface**: Streamlit 1.42+
- **AI / LLM Orchestration**:
  - **Report Analysis**: Groq API cascade (`openai/gpt-oss-120b`, `qwen/qwen3.8-27b`, `openai/gpt-oss-20b`) + Google Gemini fallback
  - **Follow-up Chat (RAG)**: LangChain, HuggingFace Embeddings (`all-MiniLM-L6-v2`), FAISS Vector Store
- **Database & Auth**: Supabase (PostgreSQL), Supabase Auth (`gotrue`)
  - **Tables**: `users`, `chat_sessions`, `chat_messages`
- **Document & Image Processing**: PDFPlumber, PyPDF, Tesseract OCR / PIL, filetype

---

## 🚀 Installation & Setup

### Prerequisites

- Python 3.8+
- Supabase account (PostgreSQL database + Auth)
- Groq API Key (and optionally Gemini API Key)

### Getting Started

1. **Clone the repository**:
   ```bash
   git clone https://github.com/harshhh28/hia.git
   cd hia
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Create or edit `.streamlit/secrets.toml` (or set OS environment variables):
   ```toml
   SUPABASE_URL = "your-supabase-url"
   SUPABASE_KEY = "your-supabase-key"
   GROQ_API_KEY = "your-groq-api-key"
   GEMINI_API_KEY = "your-gemini-api-key" # Optional fallback
   ```

5. **Initialize Database Schema**:
   Run the SQL script located at `public/db/script.sql` in your Supabase SQL Editor to set up the `users`, `chat_sessions`, and `chat_messages` tables.

---

## 🏃 Running the Application

### Option 1: FastAPI Web Application (Recommended)

Run the backend server which serves both the REST API and the static web frontend:

```bash
python server.py
```
Open your browser and navigate to **`http://127.0.0.1:8000`**.

---

### Option 2: Streamlit Dashboard

Run the Streamlit frontend interface:

```bash
streamlit run src/main.py
```

---

## 📁 Project Structure

```
hia/
├── server.py                   # FastAPI application server & REST endpoints
├── requirements.txt            # Project dependencies
├── README.md                   # Project documentation
├── static/                     # Modern Web App Frontend
│   ├── index.html              # Single Page Application HTML
│   ├── css/
│   │   └── styles.css          # Glassmorphism dark mode styles & utilities
│   └── js/
│       └── app.js              # State management, API client & UI interactions
├── src/                        # Core Python Application Source
│   ├── main.py                 # Streamlit entry point
│   ├── agents/
│   │   ├── analysis_agent.py   # Report analysis agent & knowledge base context
│   │   ├── chat_agent.py       # RAG pipeline with FAISS & HuggingFace
│   │   └── model_manager.py    # Multi-model cascade orchestration
│   ├── auth/
│   │   ├── auth_service.py     # Supabase auth & chat database operations
│   │   └── session_manager.py  # User session lifecycle & timeout tracking
│   ├── components/             # Streamlit UI Components
│   │   ├── analysis_form.py
│   │   ├── auth_pages.py
│   │   ├── footer.py
│   │   ├── header.py
│   │   └── sidebar.py
│   ├── config/
│   │   ├── app_config.py       # Application constraints & thresholds
│   │   ├── prompts.py          # Specialist medical prompts
│   │   └── sample_data.py      # Default sample report data
│   ├── services/
│   │   └── ai_service.py       # Unified AI service facade
│   └── utils/
│       ├── image_extractor.py  # OCR text extraction from medical images
│       ├── key_fallback_manager.py # Multi-key API failover & rate limit handling
│       ├── pdf_extractor.py    # PDF text extraction (PDFPlumber & PyPDF)
│       └── validators.py       # File format & medical content validation
└── public/
    └── db/
        └── script.sql          # Supabase SQL schema script
```

---

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request or open an Issue.

---

## 📄 License

This project is licensed under the MIT License.


