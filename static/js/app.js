/* ==========================================================================
   MedBrief AI — Vanilla JavaScript Application Logic
   ========================================================================== */

let currentUser = null;
let currentSession = null;
let sessions = [];
let selectedFile = null;
let isSampleSelected = false;

// Initialize App — Persist active login session on refresh
document.addEventListener("DOMContentLoaded", () => {
    const savedUser = localStorage.getItem("medbrief_user");
    if (savedUser) {
        try {
            currentUser = JSON.parse(savedUser);
            showMainScreen();
            loadSessions();
            return;
        } catch (e) {
            localStorage.removeItem("medbrief_user");
        }
    }
    currentUser = null;
    currentSession = null;
    sessions = [];
    showAuthScreen();
    schedulePurge();
});

window.addEventListener("load", () => {
    if (!currentUser) {
        schedulePurge();
    }
});

/* --- AUTHENTICATION --- */

function switchAuthTab(tab) {
    schedulePurge();
    document.getElementById("tab-login").classList.toggle("active", tab === "login");
    document.getElementById("tab-signup").classList.toggle("active", tab === "signup");
    document.getElementById("login-form").classList.toggle("hidden", tab !== "login");
    document.getElementById("signup-form").classList.toggle("hidden", tab !== "signup");
    hideAuthError();
}

function showAuthError(msg) {
    const errDiv = document.getElementById("auth-error");
    errDiv.textContent = msg;
    errDiv.classList.remove("hidden");
}

function hideAuthError() {
    document.getElementById("auth-error").classList.add("hidden");
}

async function handleLogin(event) {
    event.preventDefault();
    hideAuthError();
    const emailEl = document.getElementById("login-email");
    const passwordEl = document.getElementById("login-password");
    const email = emailEl.value.trim();
    const password = passwordEl.value.trim();
    const submitBtn = document.getElementById("login-btn");

    submitBtn.disabled = true;
    submitBtn.innerHTML = "<span>Signing In...</span>";

    try {
        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.detail || "Login failed");
        }
        currentUser = data.user;
        localStorage.setItem("medbrief_user", JSON.stringify(currentUser));
        emailEl.value = "";
        passwordEl.value = "";
        showMainScreen();
        loadSessions();
    } catch (err) {
        showAuthError(err.message);
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = "<span>Sign In</span>";
    }
}

async function handleSignup(event) {
    event.preventDefault();
    hideAuthError();
    const name = document.getElementById("signup-name").value.trim();
    const email = document.getElementById("signup-email").value.trim();
    const password = document.getElementById("signup-password").value.trim();
    const submitBtn = document.getElementById("signup-btn");

    submitBtn.disabled = true;
    submitBtn.innerHTML = "<span>Creating Account...</span>";

    try {
        const res = await fetch("/api/auth/signup", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, email, password })
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.detail || "Sign up failed");
        }
        currentUser = data.data;
        localStorage.setItem("medbrief_user", JSON.stringify(currentUser));
        showMainScreen();
        loadSessions();
    } catch (err) {
        showAuthError(err.message);
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = "<span>Create Account</span>";
    }
}

function handleLogout() {
    currentUser = null;
    currentSession = null;
    sessions = [];
    localStorage.removeItem("medbrief_user");
    localStorage.removeItem("hia_user");
    localStorage.removeItem("hia_auth");
    showAuthScreen();
}

function purgeLoginInputs() {
    const inputIds = ["login-email", "login-password", "signup-name", "signup-email", "signup-password"];
    inputIds.forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.value = "";
            input.setAttribute("autocomplete", "new-password");
        }
    });
    const loginForm = document.getElementById("login-form");
    if (loginForm) loginForm.reset();
    const signupForm = document.getElementById("signup-form");
    if (signupForm) signupForm.reset();
}

function schedulePurge() {
    purgeLoginInputs();
    setTimeout(purgeLoginInputs, 50);
    setTimeout(purgeLoginInputs, 150);
    setTimeout(purgeLoginInputs, 350);
    setTimeout(purgeLoginInputs, 700);
}

function showAuthScreen() {
    document.getElementById("auth-screen").classList.remove("hidden");
    document.getElementById("main-screen").classList.add("hidden");
    schedulePurge();
}

function showMainScreen() {
    document.getElementById("auth-screen").classList.add("hidden");
    document.getElementById("main-screen").classList.remove("hidden");

    // Populate user profile info
    const displayName = currentUser.name || currentUser.email.split("@")[0];
    document.getElementById("user-display-name").textContent = displayName;
    document.getElementById("user-display-email").textContent = currentUser.email;
    document.getElementById("user-avatar").textContent = displayName.charAt(0).toUpperCase();
}

/* --- SESSIONS & NAVIGATION --- */

async function loadSessions() {
    if (!currentUser) return;
    try {
        const res = await fetch(`/api/sessions?user_id=${currentUser.id}`);
        const data = await res.json();
        if (res.ok && data.success) {
            sessions = data.sessions || [];
            renderSessionsList();
            if (sessions.length > 0 && !currentSession) {
                selectSession(sessions[0].id);
            } else if (sessions.length === 0) {
                showView("welcome");
            }
        }
    } catch (err) {
        console.error("Failed to load sessions:", err);
    }
}

function renderSessionsList() {
    const listEl = document.getElementById("sessions-list");
    listEl.innerHTML = "";

    sessions.forEach(session => {
        const item = document.createElement("div");
        item.className = `session-item ${currentSession && currentSession.id === session.id ? "active" : ""}`;
        item.onclick = () => selectSession(session.id);

        item.innerHTML = `
            <span class="session-title-text">📊 ${escapeHtml(session.title)}</span>
            <button class="btn-icon delete-btn" onclick="event.stopPropagation(); deleteSession('${session.id}')" title="Delete Session">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
            </button>
        `;
        listEl.appendChild(item);
    });
}

async function createNewSession() {
    if (!currentUser) return;
    try {
        const res = await fetch("/api/sessions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: currentUser.id })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            const newSession = data.session;
            sessions.unshift(newSession);
            selectSession(newSession.id);
        }
    } catch (err) {
        showReportModal("Failed to create new session", "⚠️ Session Error");
    }
}

async function deleteSession(sessionId) {
    if (!confirm("Are you sure you want to delete this analysis session?")) return;
    try {
        const res = await fetch(`/api/sessions/${sessionId}`, { method: "DELETE" });
        if (res.ok) {
            sessions = sessions.filter(s => s.id !== sessionId);
            if (currentSession && currentSession.id === sessionId) {
                currentSession = null;
                if (sessions.length > 0) {
                    selectSession(sessions[0].id);
                } else {
                    renderSessionsList();
                    showView("welcome");
                }
            } else {
                renderSessionsList();
            }
        }
    } catch (err) {
        showReportModal("Failed to delete session", "⚠️ Session Error");
    }
}

async function selectSession(sessionId) {
    currentSession = sessions.find(s => s.id === sessionId);
    if (!currentSession) return;

    renderSessionsList();
    document.getElementById("current-session-title").textContent = `📊 ${currentSession.title}`;

    // Fetch messages for session
    try {
        const res = await fetch(`/api/sessions/${sessionId}/messages`);
        const data = await res.json();
        if (res.ok && data.success) {
            const messages = data.messages || [];
            if (messages.length > 0) {
                showView("chat");
                renderChatMessages(messages);
            } else {
                resetAnalysisForm();
                showView("analysis-form");
            }
        }
    } catch (err) {
        console.error("Error loading session messages:", err);
    }
}

function showView(viewName) {
    document.getElementById("welcome-view").classList.toggle("hidden", viewName !== "welcome");
    document.getElementById("analysis-form-view").classList.toggle("hidden", viewName !== "analysis-form");
    document.getElementById("chat-view").classList.toggle("hidden", viewName !== "chat");
}

/* --- FILE UPLOAD & ANALYSIS --- */

function triggerFileInput() {
    document.getElementById("pdf-input").click();
}

let currentInputMode = 'pdf'; // 'pdf' or 'photo'

function switchInputMode(mode) {
    currentInputMode = mode;
    const tabPdf = document.getElementById("tab-mode-pdf");
    const tabPhoto = document.getElementById("tab-mode-photo");
    const dropIcon = document.getElementById("dropzone-icon");
    const label = document.getElementById("file-label");
    const subtext = document.getElementById("file-subtext");
    const fileInput = document.getElementById("pdf-input");

    if (mode === 'photo') {
        if (tabPdf) tabPdf.classList.remove("active");
        if (tabPhoto) tabPhoto.classList.add("active");
        if (dropIcon) dropIcon.textContent = "📷";
        if (label) label.textContent = "Click or Drag & Drop Photo / Medical Scan";
        if (subtext) subtext.textContent = "Supports Image files (PNG, JPG, JPEG, WEBP) up to 20MB";
        if (fileInput) fileInput.setAttribute("accept", ".png,.jpg,.jpeg,.webp,.bmp");
    } else {
        if (tabPhoto) tabPhoto.classList.remove("active");
        if (tabPdf) tabPdf.classList.add("active");
        if (dropIcon) dropIcon.textContent = "📄";
        if (label) label.textContent = "Click or Drag & Drop PDF Report";
        if (subtext) subtext.textContent = "Supports PDF documents up to 20MB";
        if (fileInput) fileInput.setAttribute("accept", ".pdf");
    }

    selectedFile = null;
    isSampleSelected = false;
    const dropzone = document.getElementById("dropzone");
    if (dropzone) dropzone.classList.remove("has-file");
}

function handleFileSelected(event) {
    const file = event.target.files[0];
    if (file) {
        const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
        const isImg = file.type.startsWith("image/") || /\.(png|jpg|jpeg|webp|bmp)$/i.test(file.name);

        if (isPdf || isImg) {
            selectedFile = file;
            isSampleSelected = false;
            const icon = isImg ? "📷" : "📄";
            document.getElementById("file-label").textContent = `${icon} ${file.name}`;
            document.getElementById("dropzone").classList.add("has-file");
        } else {
            showReportModal("Only medical reports are summarized, upload a report");
        }
    }
}

function handleDragOver(e) {
    e.preventDefault();
    document.getElementById("dropzone").classList.add("dragover");
}

function handleDragLeave(e) {
    e.preventDefault();
    document.getElementById("dropzone").classList.remove("dragover");
}

function handleFileDrop(e) {
    e.preventDefault();
    document.getElementById("dropzone").classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        const file = e.dataTransfer.files[0];
        const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
        const isImg = file.type.startsWith("image/") || /\.(png|jpg|jpeg|webp|bmp)$/i.test(file.name);

        if (isPdf || isImg) {
            selectedFile = file;
            isSampleSelected = false;
            const icon = isImg ? "📷" : "📄";
            document.getElementById("file-label").textContent = `${icon} ${file.name}`;
            document.getElementById("dropzone").classList.add("has-file");
        } else {
            showReportModal("Only medical reports are summarized, upload a report");
        }
    }
}

function useSampleReport() {
    isSampleSelected = true;
    selectedFile = null;
    document.getElementById("file-label").textContent = "📄 Using Sample Report";
    document.getElementById("pdf-input").value = "";
}

function resetAnalysisForm() {
    selectedFile = null;
    isSampleSelected = false;
    const defaultText = currentInputMode === 'photo' ? "Click or Drag & Drop Photo / Medical Scan" : "Click or Drag & Drop PDF Report";
    document.getElementById("file-label").textContent = defaultText;
    document.getElementById("pdf-input").value = "";
    document.getElementById("patient-age").value = "";
    document.getElementById("patient-gender").value = "";
    document.getElementById("patient-symptoms").value = "";
}

// Override window.alert to completely prevent native browser alert pop-ups (127.0.0.1:8000 says...)
window.alert = function(msg) {
    showReportModal(msg);
};

function showReportModal(msg, title = "⚠️ Invalid Document") {
    const defaultMsg = "Only medical reports are summarized, upload a report";
    const textToShow = msg || defaultMsg;

    // Show in-UI popup card directly in PDF input area
    const pdfPopup = document.getElementById("pdf-alert-popup");
    const pdfMsg = document.getElementById("pdf-alert-msg");
    if (pdfMsg) pdfMsg.textContent = textToShow;
    if (pdfPopup) {
        pdfPopup.classList.remove("hidden");
        pdfPopup.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // Also update modal overlay if active
    const modal = document.getElementById("report-modal");
    const msgEl = document.getElementById("modal-message");
    const titleEl = document.querySelector("#report-modal .modal-title");
    if (titleEl) titleEl.textContent = title;
    if (msgEl) msgEl.textContent = textToShow;
    if (modal) modal.classList.remove("hidden");
}

function closeReportModal() {
    const pdfPopup = document.getElementById("pdf-alert-popup");
    if (pdfPopup) pdfPopup.classList.add("hidden");

    const modal = document.getElementById("report-modal");
    if (modal) modal.classList.add("hidden");

    resetAnalysisForm();
}

async function submitAnalysis() {
    if (!currentSession) return;
    if (!selectedFile && !isSampleSelected) {
        showReportModal("Only medical reports are summarized, upload a report");
        return;
    }

    const analyzeBtn = document.getElementById("analyze-btn");
    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = "<span>⌛ Analyzing Report & Generating Insights...</span>";

    const formData = new FormData();
    formData.append("session_id", currentSession.id);
    formData.append("use_sample", isSampleSelected);

    if (selectedFile) {
        formData.append("file", selectedFile);
    }

    const age = document.getElementById("patient-age").value;
    const gender = document.getElementById("patient-gender").value;
    const symptoms = document.getElementById("patient-symptoms").value;

    if (age) formData.append("age", age);
    if (gender) formData.append("gender", gender);
    if (symptoms) formData.append("symptoms", symptoms);

    try {
        const res = await fetch("/api/analyze", {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            const errDetail = data.detail || data.error || "Analysis failed";
            throw new Error(errDetail);
        }

        // Switch to chat view and reload messages
        selectSession(currentSession.id);

    } catch (err) {
        const errMsg = err.message || "An error occurred while analyzing the report";
        showReportModal(errMsg);
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = "<span>⚡ Analyze Report & Generate Insights</span>";
    }
}

/* --- RAG CHAT & CLINICAL REPORT DOCUMENT FORMATTING --- */

function extractReportMetrics(fullText) {
    const metrics = [];
    const seenNames = new Set();

    if (!fullText || typeof fullText !== "string") return [];

    function addMetric(name, val, unit = "", statusStr = "", refRange = "") {
        const cleanName = name.trim();
        if (seenNames.has(cleanName.toLowerCase())) return;
        seenNames.add(cleanName.toLowerCase());

        let status = "NORMAL";
        let pillClass = "pill-green";
        let strokeColor = "#10B981";
        let dashoffset = 15;

        const s = (statusStr || "").toUpperCase();
        if (s.includes("HIGH") || s.includes("ELEVATED") || s.includes("ABNORMAL") || s.includes("CRITICAL") || s.includes("POS")) {
            status = s.includes("HIGH") ? "HIGH" : (s.includes("CRITICAL") ? "CRITICAL" : "ELEVATED");
            pillClass = "pill-amber";
            strokeColor = "#F59E0B";
            dashoffset = 45;
        } else if (s.includes("LOW")) {
            status = "LOW";
            pillClass = "pill-amber";
            strokeColor = "#3B82F6";
            dashoffset = 65;
        }

        let icon = "🧪";
        const nLower = cleanName.toLowerCase();
        if (nLower.includes("sugar") || nLower.includes("glucose") || nLower.includes("hba1c") || nLower.includes("a1c")) icon = "🍬";
        else if (nLower.includes("blood pressure") || nLower.includes("bp") || nLower.includes("heart")) icon = "❤️";
        else if (nLower.includes("cholesterol") || nLower.includes("lipid") || nLower.includes("triglyceride") || nLower.includes("hdl") || nLower.includes("ldl")) icon = "🩸";
        else if (nLower.includes("thyroid") || nLower.includes("tsh")) icon = "🦋";
        else if (nLower.includes("hemoglobin") || nLower.includes("cbc") || nLower.includes("wbc") || nLower.includes("rbc")) icon = "💉";
        else if (nLower.includes("creatinine") || nLower.includes("kidney") || nLower.includes("urea")) icon = "🫘";
        else if (nLower.includes("alt") || nLower.includes("ast") || nLower.includes("liver") || nLower.includes("bilirubin")) icon = "🫁";

        metrics.push({
            name: cleanName,
            val: String(val).trim(),
            unit: unit ? unit.trim() : "",
            status: status,
            pillClass: pillClass,
            refText: refRange ? `Ref: ${refRange}` : "Report Value",
            conclusion: status === "NORMAL" ? "Healthy Level" : `${status} Indicator`,
            strokeColor: strokeColor,
            dashoffset: dashoffset,
            icon: icon
        });
    }

    // 1. Try parsing formatted Key Test Results section from LLM markdown
    // Format: - **HbA1c**: 7.8 % (Ref: < 5.7%) - High
    const keyResultLines = fullText.match(/- \*\*([^*]+)\*\*:\s*([^(\n-]+)(?:\(([^)]+)\))?(?:-\s*(\w+))?/g);
    if (keyResultLines) {
        keyResultLines.forEach(line => {
            const m = line.match(/- \*\*([^*]+)\*\*:\s*([^(\n-]+)(?:\(([^)]+)\))?(?:-\s*(\w+))?/);
            if (m) {
                const tName = m[1].trim();
                const rawValUnit = m[2].trim();
                const ref = m[3] ? m[3].replace(/^ref:\s*/i, "").trim() : "";
                const stat = m[4] ? m[4].trim() : "";

                const valMatch = rawValUnit.match(/^([0-9./]+)\s*(.*)$/);
                if (valMatch) {
                    addMetric(tName, valMatch[1], valMatch[2], stat, ref);
                } else {
                    addMetric(tName, rawValUnit, "", stat, ref);
                }
            }
        });
    }

    // 2. Comprehensive pattern matchers for common specific lab tests in report text
    if (metrics.length < 4) {
        // HbA1c
        const hba1cMatch = fullText.match(/(?:hba1c|hb a1c|glycated hemoglobin|a1c):?\s*([0-9.]+)\s*(%|mmol\/mol)?/i);
        if (hba1cMatch) addMetric("Blood Sugar (HbA1c)", hba1cMatch[1], hba1cMatch[2] || "%", parseFloat(hba1cMatch[1]) >= 5.7 ? "ELEVATED" : "NORMAL", "< 5.7%");

        // Fasting Glucose / Blood Sugar
        const gluMatch = fullText.match(/(?:fasting (?:blood )?sugar|fasting glucose|fbs|blood glucose|glucose):?\s*([0-9.]+)\s*(mg\/dl|mmol\/l)?/i);
        if (gluMatch) addMetric("Fasting Glucose", gluMatch[1], gluMatch[2] || "mg/dL", parseFloat(gluMatch[1]) > 100 ? "ELEVATED" : "NORMAL", "70 - 100 mg/dL");

        // Post Prandial Glucose
        const ppgluMatch = fullText.match(/(?:post prandial (?:blood )?sugar|ppbs|pp glucose):?\s*([0-9.]+)\s*(mg\/dl|mmol\/l)?/i);
        if (ppgluMatch) addMetric("Post Prandial Glucose", ppgluMatch[1], ppgluMatch[2] || "mg/dL", parseFloat(ppgluMatch[1]) > 140 ? "ELEVATED" : "NORMAL", "< 140 mg/dL");

        // Blood Pressure
        const bpMatch = fullText.match(/(?:blood pressure|bp):?\s*([0-9]{2,3}\/[0-9]{2,3})\s*(mmhg)?/i);
        if (bpMatch) addMetric("Blood Pressure", bpMatch[1], "mmHg", "IDEAL", "< 120/80 mmHg");

        // Triglycerides
        const triMatch = fullText.match(/(?:triglycerides|triglyceride):?\s*([0-9.]+)\s*(mg\/dl)?/i);
        if (triMatch) addMetric("Triglycerides", triMatch[1], "mg/dL", parseFloat(triMatch[1]) > 150 ? "ELEVATED" : "NORMAL", "< 150 mg/dL");

        // Total Cholesterol
        const cholMatch = fullText.match(/(?:total cholesterol|cholesterol):?\s*([0-9.]+)\s*(mg\/dl)?/i);
        if (cholMatch) addMetric("Total Cholesterol", cholMatch[1], "mg/dL", parseFloat(cholMatch[1]) > 200 ? "ELEVATED" : "NORMAL", "< 200 mg/dL");

        // LDL Cholesterol
        const ldlMatch = fullText.match(/(?:ldl cholesterol|ldl):?\s*([0-9.]+)\s*(mg\/dl)?/i);
        if (ldlMatch) addMetric("LDL Cholesterol", ldlMatch[1], "mg/dL", parseFloat(ldlMatch[1]) > 100 ? "ELEVATED" : "NORMAL", "< 100 mg/dL");

        // Hemoglobin
        const hbMatch = fullText.match(/(?:hemoglobin|hb):?\s*([0-9.]+)\s*(g\/dl)?/i);
        if (hbMatch) addMetric("Hemoglobin", hbMatch[1], "g/dL", parseFloat(hbMatch[1]) < 12 ? "LOW" : "NORMAL", "12.0 - 16.0 g/dL");

        // Creatinine
        const creatMatch = fullText.match(/(?:serum creatinine|creatinine):?\s*([0-9.]+)\s*(mg\/dl)?/i);
        if (creatMatch) addMetric("Serum Creatinine", creatMatch[1], "mg/dL", parseFloat(creatMatch[1]) > 1.2 ? "ELEVATED" : "NORMAL", "0.6 - 1.2 mg/dL");

        // TSH
        const tshMatch = fullText.match(/(?:tsh|thyroid stimulating hormone):?\s*([0-9.]+)\s*(uiu\/ml|miu\/l)?/i);
        if (tshMatch) addMetric("TSH (Thyroid)", tshMatch[1], tshMatch[2] || "uIU/mL", (parseFloat(tshMatch[1]) > 4.5 || parseFloat(tshMatch[1]) < 0.4) ? "ELEVATED" : "NORMAL", "0.4 - 4.5 uIU/mL");
    }

    // Return ONLY extracted metrics from report. NO FAKE DUMMY FALLBACKS!
    return metrics.slice(0, 4);
}

function buildGaugesGridHtml(metrics) {
    if (!metrics || metrics.length === 0) return "";

    const cards = metrics.map(m => `
        <div class="gauge-meter-card">
            <div class="gauge-meter-header">
                <span class="gauge-meter-icon">${m.icon}</span>
                <span class="gauge-meter-title">${escapeHtml(m.name)}</span>
            </div>
            <div class="gauge-graphic-container">
                <svg class="gauge-svg" viewBox="0 0 100 60">
                    <path class="gauge-bg-arc" d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#E2E8F0" stroke-width="9" stroke-linecap="round"/>
                    <path class="gauge-fill-arc" d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="${m.strokeColor}" stroke-width="9" stroke-linecap="round" stroke-dasharray="126" stroke-dashoffset="${m.dashoffset}"/>
                </svg>
                <div class="gauge-val-overlay">
                    <span class="val-num">${escapeHtml(m.val)}</span>
                    <span class="val-unit">${escapeHtml(m.unit)}</span>
                </div>
            </div>
            <div class="gauge-pill ${m.pillClass}">${escapeHtml(m.status)}</div>
            <div class="gauge-ref-range">${escapeHtml(m.refText)}</div>
            <div class="gauge-conclusion-text">${escapeHtml(m.conclusion)}</div>
        </div>
    `).join("");

    return `
        <div class="report-banner-header">
            <h3>YOUR LATEST TEST RESULTS</h3>
        </div>
        <div class="report-gauges-grid">
            ${cards}
        </div>
    `;
}

function formatAssistantContent(rawText) {
    if (!rawText || typeof rawText !== "string") return "";

    let text = rawText.replace(/\r\n/g, "\n");

    const isMedicalReport = /diagnosis|health risks|recommendations|disclaimer/i.test(text);

    if (!isMedicalReport) {
        let html = marked.parse(text);
        const temp = document.createElement("div");
        temp.innerHTML = html;
        temp.querySelectorAll("ul").forEach(ul => ul.classList.add("chat-card-list"));
        temp.querySelectorAll("blockquote").forEach(bq => {
            const card = document.createElement("div");
            card.className = "disclaimer-card";
            card.innerHTML = `<div class="disclaimer-header"><span class="disclaimer-badge">⚕️ Medical Disclaimer</span></div><div class="disclaimer-text">${bq.innerHTML}</div>`;
            bq.parentNode.replaceChild(card, bq);
        });
        return temp.innerHTML;
    }

    let disclaimerHtml = "";
    let diagnosisHtml = "";
    let actionPlanCards = [];
    let summaryHtml = "";

    const lines = text.split("\n");
    
    let currentSection = ""; 
    let currentCategory = ""; 
    
    let disclaimerLines = [];
    let riskItems = [];
    let currentRisk = null;

    let categoryItemsMap = {
        "lifestyle": { title: "Lifestyle Modifications", icon: "🏃‍♂️", colorClass: "rec-card-teal", items: [] },
        "dietary": { title: "Dietary Recommendations", icon: "🥗", colorClass: "rec-card-emerald", items: [] },
        "tests": { title: "Follow-up Tests Required", icon: "🧪", colorClass: "rec-card-sky", items: [] },
        "preventive": { title: "Preventive Measures", icon: "🛡️", colorClass: "rec-card-indigo", items: [] },
        "urgency": { title: "Urgency of Consultation", icon: "🚨", colorClass: "rec-card-rose", items: [] }
    };

    const recHeaderRules = [
        { key: "lifestyle", match: /lifestyle/i },
        { key: "dietary", match: /dietary/i },
        { key: "tests", match: /follow[- ]?up|test/i },
        { key: "preventive", match: /preventive|prevention/i },
        { key: "urgency", match: /urgency|consultation/i }
    ];

    let summaryLines = [];

    lines.forEach(line => {
        const trimmed = line.trim();
        if (!trimmed) return;

        const lower = trimmed.toLowerCase();

        // Detect Disclaimer
        if (lower.includes("disclaimer")) {
            currentSection = "disclaimer";
            const discText = trimmed.replace(/^[>\s*-]+/, "").replace(/\*\*/g, "").replace(/^Disclaimer:?\s*/i, "");
            if (discText) disclaimerLines.push(discText);
            return;
        }

        if (currentSection === "disclaimer" && !lower.includes("diagnosis") && !lower.includes("health risks")) {
            disclaimerLines.push(trimmed.replace(/^[>\s*-]+/, "").replace(/\*\*/g, ""));
            return;
        }

        // Detect Diagnosis Section
        if (lower.includes("diagnosis") || lower.includes("potential health risks")) {
            currentSection = "diagnosis";
            return;
        }

        // Detect Recommendations Section
        if (lower.includes("recommendations") || lower.includes("action plan")) {
            currentSection = "recommendations";
            return;
        }

        // Detect Summary Section
        if (lower.includes("overall summary") || lower.includes("summary:")) {
            currentSection = "summary";
            const sumText = trimmed.replace(/\*\*/g, "").replace(/^Overall Summary:?\s*/i, "");
            if (sumText) summaryLines.push(sumText);
            return;
        }

        // Process Diagnosis Section
        if (currentSection === "diagnosis") {
            const cleanLine = trimmed.replace(/^[\s*•\-oO▪>0-9.]+\s*/, "");
            
            if (/evidence:/i.test(cleanLine)) {
                if (currentRisk) {
                    currentRisk.evidence.push(cleanLine.replace(/\*\*/g, "").replace(/^Evidence:?\s*/i, ""));
                }
            } else if (/risk|level|normal/i.test(cleanLine)) {
                if (currentRisk) riskItems.push(currentRisk);
                
                const sepIdx = cleanLine.search(/–|-|:|\|/);
                let title = cleanLine;
                let badge = "Risk Monitored";
                if (sepIdx !== -1) {
                    title = cleanLine.substring(0, sepIdx).replace(/\*\*/g, "").trim();
                    badge = cleanLine.substring(sepIdx + 1).replace(/\*\*/g, "").trim();
                } else {
                    title = cleanLine.replace(/\*\*/g, "").trim();
                }

                currentRisk = { title, badge, evidence: [] };
            } else if (currentRisk) {
                currentRisk.evidence.push(trimmed.replace(/\*\*/g, ""));
            }
        }

        // Process Recommendations Section
        if (currentSection === "recommendations") {
            const headerMatch = recHeaderRules.find(r => r.match.test(trimmed));
            if (headerMatch && trimmed.length < 50 && !trimmed.includes(":")) {
                currentCategory = headerMatch.key;
            } else if (currentCategory && categoryItemsMap[currentCategory]) {
                const cleanItem = trimmed.replace(/^[\s*•\-oO▪>0-9.]+\s*/, "").replace(/\*\*/g, "");
                categoryItemsMap[currentCategory].items.push(cleanItem);
            }
        }

        // Process Summary Section
        if (currentSection === "summary") {
            summaryLines.push(trimmed.replace(/\*\*/g, ""));
        }
    });

    if (currentRisk) riskItems.push(currentRisk);

    // Filter out invalid or header risk items
    riskItems = riskItems.filter(item => {
        if (!item || !item.title) return false;
        const cleanTitle = item.title.trim().toLowerCase();
        if (cleanTitle.includes("potential health risks") || cleanTitle.includes("health risks") || cleanTitle === "diagnosis" || cleanTitle === "potential risks") return false;
        if (cleanTitle.endsWith(":") && item.evidence.length === 0) return false;
        return true;
    });

    // Extract Gauge Metrics
    const extractedMetrics = extractReportMetrics(rawText);
    const gaugesGridHtml = buildGaugesGridHtml(extractedMetrics);

    // Build Disclaimer
    if (disclaimerLines.length > 0) {
        disclaimerHtml = `
            <div class="disclaimer-card">
                <div class="disclaimer-header">
                    <span class="disclaimer-badge">⚕️ Medical Disclaimer</span>
                </div>
                <div class="disclaimer-text">${escapeHtml(disclaimerLines.join(" "))}</div>
            </div>
        `;
    }

    // Build Diagnosis Section
    if (riskItems.length > 0) {
        const riskCardsHtml = riskItems.map(item => buildRiskCard(item.title, item.badge, item.evidence.join(" "))).join("");
        diagnosisHtml = `
            <div class="diagnosis-section-card">
                <div class="report-banner-header">
                    <h3>UNDERSTANDING YOUR RESULTS</h3>
                </div>
                <div class="understanding-takeaway-banner">
                    <div class="takeaway-heart-icon">❤️</div>
                    <div class="takeaway-text">
                        <p><strong>Clinical Key Takeaway:</strong> Your indicators have been parsed into clear risk levels. Keep maintaining targeted lifestyle and health habits!</p>
                    </div>
                </div>
                <div class="risk-cards-grid">
                    ${riskCardsHtml}
                </div>
            </div>
        `;
    }

    // Build Action Plan Cards
    Object.keys(categoryItemsMap).forEach(key => {
        const cat = categoryItemsMap[key];
        if (cat.items.length > 0) {
            const listItemsHtml = cat.items.map(item => {
                const colonIdx = item.indexOf(":");
                if (colonIdx > 0 && colonIdx < 35) {
                    const label = item.substring(0, colonIdx).trim();
                    const val = item.substring(colonIdx + 1).trim();
                    return `<li><strong>${escapeHtml(label)}:</strong> ${escapeHtml(val)}</li>`;
                }
                return `<li>${escapeHtml(item)}</li>`;
            }).join("");

            actionPlanCards.push(`
                <div class="rec-card ${cat.colorClass} ${key === 'urgency' ? 'full-width-card' : ''}">
                    <div class="rec-card-header">
                        <span class="rec-icon">${cat.icon}</span>
                        <h4>${cat.title}</h4>
                    </div>
                    <ul class="rec-list">
                        ${listItemsHtml}
                    </ul>
                </div>
            `);
        }
    });

    let recSectionHtml = "";
    if (actionPlanCards.length > 0) {
        recSectionHtml = `
            <div class="recommendations-section">
                <div class="report-banner-header">
                    <h3>RECOMMENDATIONS & ACTION PLAN</h3>
                </div>
                <div class="recommendations-grid">
                    ${actionPlanCards.join("")}
                </div>
            </div>
        `;
    }

    // Build Summary Card
    if (summaryLines.length > 0) {
        summaryHtml = `
            <div class="rec-card rec-card-teal full-width-card" style="margin-top: 1rem;">
                <div class="rec-card-header">
                    <span class="rec-icon">💡</span>
                    <h4>Overall Clinical Summary</h4>
                </div>
                <div style="font-size: 0.95rem; line-height: 1.65; color: #334155;">
                    ${escapeHtml(summaryLines.join(" "))}
                </div>
            </div>
        `;
    }

    const formattedDate = new Date().toLocaleDateString("en-US", { year: 'numeric', month: 'long', day: 'numeric' });

    return `
        <div class="medical-report-document">
            <!-- CLINIC HEADER -->
            <div class="report-doc-header">
                <div class="report-clinic-brand">
                    <div class="clinic-logo-icon">➕</div>
                    <div class="clinic-brand-text">
                        <span class="clinic-name">GENERAL HEALTH CLINIC</span>
                        <span class="clinic-sub">MedBrief AI Patient Brief</span>
                    </div>
                </div>
                <div class="report-doc-title-box">
                    <h2>MEDICAL REPORT SUMMARY</h2>
                    <span class="report-doc-subtitle">A Simple Medical Guide</span>
                </div>
                <div class="report-doc-date">
                    ${formattedDate}
                </div>
            </div>

            <!-- GAUGE METRICS SECTION -->
            ${gaugesGridHtml}

            <!-- DIAGNOSIS & UNDERSTANDING RESULTS -->
            ${diagnosisHtml}

            <!-- RECOMMENDATIONS SECTION -->
            ${recSectionHtml}

            <!-- SUMMARY SECTION -->
            ${summaryHtml}

            <!-- DISCLAIMER & FOOTER -->
            <div class="report-doc-footer">
                ${disclaimerHtml}
            </div>
        </div>
    `;
}

function buildRiskCard(title, badgeText, evidenceText) {
    let badgeClass = "badge-medium";
    const lowerBadge = (badgeText || "").toLowerCase();
    
    if (lowerBadge.includes("high") && !lowerBadge.includes("medium")) {
        badgeClass = "badge-high";
    } else if (lowerBadge.includes("low") && !lowerBadge.includes("medium")) {
        badgeClass = "badge-low";
    } else if (lowerBadge.includes("medium") || lowerBadge.includes("borderline")) {
        badgeClass = "badge-medium";
    }

    const cleanTitle = escapeHtml(title.replace(/\*\*/g, "").replace(/^[*•-]\s*/, ""));
    const cleanBadge = escapeHtml(badgeText.replace(/\*\*/g, "").replace(/^Risk Level:?\s*/i, ""));
    const cleanEvidence = escapeHtml(evidenceText.replace(/\*\*/g, "").replace(/^Evidence:?\s*/i, ""));

    return `
        <div class="risk-card ${badgeClass}-border">
            <div class="risk-card-header">
                <div class="risk-title-wrapper">
                    <span class="risk-bullet-icon">🩺</span>
                    <h4 class="risk-title">${cleanTitle}</h4>
                </div>
                ${cleanBadge ? `<span class="risk-badge ${badgeClass}">${cleanBadge}</span>` : ""}
            </div>
            ${cleanEvidence ? `
                <div class="risk-evidence-box">
                    <span class="evidence-icon">📊</span>
                    <div class="evidence-text"><strong>Evidence:</strong> ${cleanEvidence}</div>
                </div>
            ` : ""}
        </div>
    `;
}

function renderChatMessages(messages) {
    const container = document.getElementById("chat-messages");
    container.innerHTML = "";

    let assistantCount = 0;
    messages.forEach(msg => {
        if (msg.role === "system") return; // Hide internal system report metadata

        const row = document.createElement("div");
        row.className = `message-row ${msg.role}`;

        const bubble = document.createElement("div");
        bubble.className = "message-bubble";

        if (msg.role === "assistant") {
            assistantCount++;
            const providerBadge = assistantCount === 1 
                ? `<div class="badge-header"><span class="model-badge groq-badge">⚡ Medical Analysis</span></div>`
                : `<div class="badge-header"><span class="model-badge gemini-badge">✨ Health Assistant</span></div>`;

            bubble.innerHTML = providerBadge + formatAssistantContent(msg.content);
        } else {
            bubble.textContent = msg.content;
        }

        row.appendChild(bubble);
        container.appendChild(row);
    });

    container.scrollTop = container.scrollHeight;
}

async function handleChatSubmit(event) {
    event.preventDefault();
    if (!currentSession) return;

    const inputEl = document.getElementById("chat-input");
    const prompt = inputEl.value.trim();
    if (!prompt) return;

    inputEl.value = "";
    const container = document.getElementById("chat-messages");

    // Append user message immediately
    const userRow = document.createElement("div");
    userRow.className = "message-row user";
    userRow.innerHTML = `<div class="message-bubble">${escapeHtml(prompt)}</div>`;
    container.appendChild(userRow);

    // Append loading indicator for assistant
    const assistantRow = document.createElement("div");
    assistantRow.className = "message-row assistant";
    assistantRow.innerHTML = `<div class="message-bubble"><div class="badge-header"><span class="model-badge gemini-badge">✨ Health Assistant</span></div><div class="thinking-state"><em>⌛ Thinking...</em></div></div>`;
    container.appendChild(assistantRow);
    container.scrollTop = container.scrollHeight;

    const sendBtn = document.getElementById("chat-send-btn");
    sendBtn.disabled = true;

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: currentSession.id,
                prompt: prompt
            })
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.detail || "Failed to get response");
        }

        const badgeText = `<div class="badge-header"><span class="model-badge gemini-badge">✨ Health Assistant</span></div>`;

        assistantRow.querySelector(".message-bubble").innerHTML = badgeText + formatAssistantContent(data.response);
    } catch (err) {
        assistantRow.querySelector(".message-bubble").innerHTML = `<div class="badge-header"><span class="model-badge gemini-badge">✨ Health Assistant</span></div><div style="color: #DC2626; padding-top: 0.5rem;">Error: ${escapeHtml(err.message)}</div>`;
    } finally {
        sendBtn.disabled = false;
        container.scrollTop = container.scrollHeight;
    }
}

function escapeHtml(text) {
    if (!text) return "";
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

