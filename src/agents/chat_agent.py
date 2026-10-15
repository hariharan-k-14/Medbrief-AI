import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from utils.key_fallback_manager import APIKeyRotator

logger = logging.getLogger(__name__)

GEMINI_MODELS = [
    "gemini-3.6-flash",
    "gemini-2.5-flash"
]

class ChatAgent:
    """
    Chatbot agent for answering follow-up questions about generated summaries.
    Exclusively uses Gemini AI models with 3-key fallback rotation and HuggingFace emergency fallback.
    """

    def __init__(self):
        self._embeddings = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )

    @property
    def embeddings(self):
        if self._embeddings is None:
            self._embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        return self._embeddings

    def initialize_vector_store(self, text_content):
        """Create FAISS vector store from report text content."""
        if not text_content or not text_content.strip():
            text_content = "No report context available."

        texts = self.text_splitter.split_text(text_content)
        if not texts:
            texts = [text_content]

        return FAISS.from_texts(texts, self.embeddings)

    def _format_chat_history_str(self, chat_history):
        """Format chat history into text string for prompt context."""
        if not chat_history:
            return ""
        formatted = []
        for msg in chat_history[-6:]:
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "")
            if content and isinstance(content, str) and not content.startswith("__REPORT_TEXT__"):
                formatted.append(f"{role}: {content}")
        return "\n".join(formatted)

    def _is_unrelated_query(self, query, context=""):
        """Check if query is clearly unrelated to medical reports or health context."""
        q = query.lower().strip()
        
        non_medical_keywords = [
            "who is ", "who won ", "capital of ", "president of ", "prime minister",
            "python", "javascript", "java ", "c++", "write code", "write a script",
            "write a function", "write a program", "tell me a joke", "recipe for",
            "movie", "actor", "actress", "football", "cricket", "basketball",
            "weather in", "translate ", "game of thrones", "song", "lyrics",
            "car ", "sports", "math problem", "solve x"
        ]
        
        medical_keywords = [
            "report", "summary", "test", "result", "level", "count", "blood",
            "glucose", "hemoglobin", "wbc", "rbc", "cholesterol", "thyroid",
            "liver", "kidney", "doctor", "health", "patient", "symptom",
            "diagnosis", "medicine", "dose", "bp", "pressure", "heart",
            "pulse", "vital", "normal", "high", "low", "abnormal", "range",
            "scan", "xray", "mri", "ecg", "cbc", "urine", "vitamin", "iron",
            "deficiency", "condition", "risk", "diet", "exercise", "pain",
            "fever", "cough", "disease", "treatment", "cure", "lab", "finding",
            "biomarker", "organ", "body", "stage", "grade", "index", "my", "this",
            "what", "why", "how", "can", "should", "is", "are"
        ]
        
        for nm in non_medical_keywords:
            if nm in q:
                if not any(m in q for m in medical_keywords):
                    return True
                    
        return False

    def get_response(self, query, vectorstore, chat_history=None):
        """
        Get answer to user's question about the summary using RAG + Gemini AI.
        """
        if chat_history is None:
            chat_history = []

        if self._is_unrelated_query(query):
            return "Only questions about the summary are answerable"

        # 1. Retrieve relevant context from vectorstore
        context = ""
        if vectorstore:
            try:
                retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
                try:
                    docs = retriever.invoke(query)
                except AttributeError:
                    docs = retriever.get_relevant_documents(query)
                context = "\n\n".join([doc.page_content for doc in docs if doc.page_content.strip()])
                if context.strip() == "No report context available.":
                    context = ""
            except Exception as e:
                logger.warning(f"Vectorstore retrieval warning: {e}")

        # 2. Build full prompt
        history_str = self._format_chat_history_str(chat_history)
        
        system_instruction = (
            "You are MedBrief AI, an assistant for answering follow-up questions exclusively about a patient's medical report summary.\n"
            "CRITICAL INSTRUCTION: You MUST ONLY answer questions that are directly related to the patient's medical report, lab test results, health findings, diagnosis, symptoms, or medical advice based on the report.\n"
            "If the user asks ANY question that is NOT related to the medical report, medical findings, health summary, or clinical context (e.g. general trivia, coding, sports, weather, politics, recipes, entertainment, or unrelated general chat), YOU MUST REPLY ONLY WITH THIS EXACT SENTENCE:\n"
            "\"Only questions about the summary are answerable\"\n"
            "Do NOT provide any other response, explanation, or polite greeting for unrelated questions."
        )

        prompt_parts = [system_instruction]
        if context:
            prompt_parts.append(f"\n--- REPORT SUMMARY CONTEXT ---\n{context}")
        if history_str:
            prompt_parts.append(f"\n--- PREVIOUS CHAT HISTORY ---\n{history_str}")
        prompt_parts.append(f"\nUser Question: {query}\nAnswer:")
        
        full_prompt = "\n\n".join(prompt_parts)

        # 3. Call Gemini with 3-key fallback rotation
        def call_gemini(api_key):
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                last_err = None

                for model in GEMINI_MODELS:
                    try:
                        logger.info(f"Attempting Gemini chat response with model: {model}")
                        res = client.models.generate_content(
                            model=model,
                            contents=full_prompt
                        )
                        if res and res.text:
                            return {
                                "success": True,
                                "content": res.text.strip(),
                                "model_used": f"Gemini ({model})",
                                "provider": "Gemini"
                            }
                    except Exception as ge:
                        last_err = str(ge)
                        logger.warning(f"Gemini model {model} failed: {ge}")
                        continue

                return {"success": False, "error": f"Gemini error: {last_err}"}
            except Exception as outer_e:
                return {"success": False, "error": f"Gemini client init error: {str(outer_e)}"}

        def emergency_hf_fallback():
            logger.info("Triggering Hugging Face emergency fallback for Chatbot...")
            def call_hf(hf_key):
                try:
                    from huggingface_hub import InferenceClient
                    client = InferenceClient(provider="hf-inference", api_key=hf_key)
                    res = client.chat.completions.create(
                        model="meta-llama/Llama-3.2-3B-Instruct",
                        messages=[{"role": "user", "content": full_prompt}],
                        max_tokens=1000,
                        temperature=0.7
                    )
                    return {
                        "success": True,
                        "content": res.choices[0].message.content.strip(),
                        "model_used": "Hugging Face (Llama-3.2-3B-Instruct)",
                        "provider": "HuggingFace"
                    }
                except Exception as hf_err:
                    return {"success": False, "error": f"HF error: {str(hf_err)}"}

            return APIKeyRotator.execute_with_fallback("HF", call_hf)

        result = APIKeyRotator.execute_with_fallback(
            provider="GEMINI",
            call_fn=call_gemini,
            emergency_fallback_fn=emergency_hf_fallback
        )

        if isinstance(result, dict) and result.get("success"):
            ans = result.get("content", "").strip()
            if "only questions about the summary are answerable" in ans.lower():
                return "Only questions about the summary are answerable"
            return ans
        elif isinstance(result, dict) and result.get("error"):
            return f"Error: {result.get('error')}"
        return str(result)
