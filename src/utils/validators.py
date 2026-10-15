import os
import re
from pathlib import Path
from config.app_config import MAX_UPLOAD_SIZE_MB

def validate_password(password):
    """Validate password meets security requirements."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    return True, None

def validate_email(email):
    """Validate email format."""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))

def validate_signup_fields(name, email, password, confirm_password):
    """Validate all signup form fields."""
    if not all([name, email, password, confirm_password]):
        return False, "Please fill in all fields"
        
    if not validate_email(email):
        return False, "Please enter a valid email address"
        
    if password != confirm_password:
        return False, "Passwords do not match"
        
    is_valid, error_msg = validate_password(password)
    if not is_valid:
        return False, error_msg
        
    return True, None

def validate_pdf_file(file):
    """Validate PDF or Photo report file size and type (supports file paths, Streamlit and FastAPI file objects)."""
    if not file:
        return False, "No file uploaded"

    allowed_exts = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp"}

    if isinstance(file, str):
        if not os.path.exists(file):
            return False, "File does not exist"
        file_size = os.path.getsize(file)
        file_size_mb = file_size / (1024 * 1024)
        if file_size_mb > MAX_UPLOAD_SIZE_MB:
            return False, f"File size ({file_size_mb:.1f}MB) exceeds the {MAX_UPLOAD_SIZE_MB}MB limit"
        ext = Path(file).suffix.lower()
        if ext not in allowed_exts:
            return False, "Invalid file type. Please upload a PDF or Photo report (.pdf, .png, .jpg, .jpeg, .webp)"
        return True, None

    file_size = getattr(file, "size", 0)
    file_size_mb = file_size / (1024 * 1024)
    if file_size_mb > MAX_UPLOAD_SIZE_MB:
        return False, f"File size ({file_size_mb:.1f}MB) exceeds the {MAX_UPLOAD_SIZE_MB}MB limit"

    filename = getattr(file, "name", getattr(file, "filename", ""))
    ext = Path(filename).suffix.lower() if filename else ""
    file_type = getattr(file, "type", "")

    if ext and ext not in allowed_exts and file_type not in ["application/pdf", "image/png", "image/jpeg", "image/webp"]:
        return False, "Invalid file type. Please upload a PDF or Photo report (.pdf, .png, .jpg, .jpeg, .webp)"

    return True, None

def validate_pdf_content(text):
    """Validate if the PDF content appears to be a patient health/medical report."""
    if not text or not isinstance(text, str) or len(text.strip()) < 10:
        return False, "Only medical reports are summarized, upload a report"

    text_lower = text.lower()

    # 1. Explicit Non-Medical Document Indicators (Code files, web markup, software specs)
    non_medical_patterns = [
        r'\bdef\s+\w+\(', r'\bimport\s+\w+', r'\bfrom\s+\w+\s+import',
        r'\bpublic\s+static\s+void\b', r'\bfunction\s*\w*\s*\(',
        r'<!doctype\s+html', r'<html\b', r'\bselect\s+.*\s+from\b',
        r'#include\s*<', r'\bvar\s+\w+\s*=', r'\bconst\s+\w+\s*=', r'\blet\s+\w+\s*='
    ]
    for pattern in non_medical_patterns:
        if re.search(pattern, text_lower):
            return False, "Only medical reports are summarized, upload a report"

    # 2. Comprehensive Medical Terms, Disease Names & Lab Parameter Vocabulary
    medical_terms = [
        # General Report & Clinical Indicators
        'blood', 'test', 'report', 'laboratory', 'lab', 'patient', 'specimen',
        'reference range', 'ref range', 'analysis', 'results', 'medical', 'diagnostic',
        'pathology', 'radiology', 'ultrasound', 'x-ray', 'xray', 'ct scan', 'mri',
        'biopsy', 'hematology', 'biochemistry', 'microbiology', 'cytology',
        'histopathology', 'prescription', 'discharge', 'consultation', 'checkup',
        'examination', 'investigation', 'screening', 'profile', 'panel', 'vitals',
        'impression', 'findings', 'observation', 'diagnosis', 'prognosis', 'doctor',
        'physician', 'hospital', 'clinic', 'polyclinic', 'dr', 'dr.', 'patient name',
        'dob', 'age', 'gender', 'sex', 'male', 'female', 'sample', 'collected',
        'reported', 'referred', 'health', 'clinical', 'rx', 'tab', 'tablet',
        'cap', 'capsule', 'syr', 'syrup', 'mg', 'ml', 'treatment', 'dose', 'daily',
        'oral', 'medication', 'disease', 'symptom', 'symptoms', 'history',
        'chief complaint', 'assessment', 'plan', 'stage', 'grade', 'critical',
        'borderline', 'desirable', 'optimal', 'normal', 'abnormal', 'high', 'low',
        'positive', 'negative', 'reactive', 'non-reactive', 'detected', 'not detected',

        # Diabetes, Endocrine & Metabolic Diseases
        'diabetes', 'diabetic', 'mellitus', 'sugar', 'blood sugar', 'hba1c', 'hb a1c',
        'a1c', 'glycated', 'glycohemoglobin', 'glucose', 'fasting glucose', 'fbs',
        'ppbs', 'ogtt', 'glucose tolerance', 'insulin', 'c-peptide', 'microalbumin',
        'microalbuminuria', 'ketone', 'ketones', 'ketoacidosis', 'dka',
        'hyperglycemia', 'hypoglycemia', 'eag', 'estimated average glucose',
        'fructosamine', 'endocrin', 'endocrine', 'endocrinologist', 'pancreas',
        'pancreatic', 'metabolic', 'metabolism', 'syndrome', 'prediabetes',
        'prediabetic', 't1d', 't2d', 'type 1', 'type 2', 'glycemia', 'glucagon',
        'thyroid', 'tsh', 't3', 'ft3', 't4', 'ft4', 'thyroxine', 'triiodothyronine',
        'cortisol', 'acth', 'estrogen', 'testosterone', 'progesterone', 'prolactin',
        'parathyroid', 'pth', 'goiter', 'hashimoto', 'graves', 'cushing', 'addison',
        'obesity', 'dyslipidemia', 'hyperlipidemia', 'hypercholesterolemia', 'gout',
        'hyperuricemia', 'osteoporosis', 'rickets', 'vitamin d',

        # Cardiovascular & Lipid Parameters
        'cardiac', 'cardiovascular', 'cardiology', 'cardiologist', 'hypertension',
        'hypotension', 'blood pressure', 'bp', 'arterial', 'vascular', 'coronary',
        'angina', 'infarction', 'myocardial', 'arrhythmia', 'atherosclerosis', 'ecg',
        'ekg', 'echo', 'echocardiogram', 'troponin', 'bnp', 'nt-probnp', 'ck-mb',
        'lipid', 'cholesterol', 'triglyceride', 'triglycerides', 'hdl', 'ldl',
        'vldl', 'apolipoprotein', 'thrombosis', 'embolism', 'stroke', 'ischemia',

        # Renal, Nephrology & Urinary
        'renal', 'kidney', 'nephrology', 'nephrologist', 'egfr', 'gfr', 'creatinine',
        'urea', 'bun', 'uric acid', 'dialysis', 'nephropathy', 'nephritis',
        'proteinuria', 'albuminuria', 'hematuria', 'urine', 'urinalysis', 'cystitis',
        'pyelonephritis', 'kidney stone', 'nephrolithiasis', 'incontinence', 'uti',

        # Hepatic, Gastrointestinal & Biliary
        'liver', 'hepatic', 'hepatology', 'hepatitis', 'sgot', 'sgpt', 'alt',
        'ast', 'alp', 'alkaline phosphatase', 'ggt', 'bilirubin', 'cirrhosis',
        'fatty liver', 'steatosis', 'gastro', 'gastroenterology', 'endoscopy',
        'colonoscopy', 'pancreatitis', 'cholecystitis', 'gallbladder', 'gastritis',
        'ulcer', 'gerd', 'reflux', 'colitis', 'crohn', 'celiac', 'jaundice',

        # Hematology, Oncology, Immunology & Autoimmune
        'hematology', 'hemoglobin', 'hb', 'wbc', 'rbc', 'platelet', 'platelets',
        'hematocrit', 'mcv', 'mch', 'mchc', 'rdw', 'neutrophil', 'neutrophils',
        'lymphocyte', 'lymphocytes', 'monocyte', 'monocytes', 'eosinophil',
        'eosinophils', 'basophil', 'basophils', 'esr', 'crp', 'c-reactive',
        'ferritin', 'iron', 'anemia', 'anaemia', 'thalassemia', 'leukemia',
        'lymphoma', 'myeloma', 'melanoma', 'carcinoma', 'sarcoma', 'tumor',
        'tumour', 'neoplasm', 'malignancy', 'oncology', 'metastasis', 'biopsy',
        'cytology', 'psa', 'cea', 'ca-125', 'ca125', 'ca19-9', 'afp', 'immunology',
        'antibody', 'antigen', 'ana', 'rheumatoid', 'lupus', 'autoimmune',
        'inflammation', 'inflammatory', 'infection', 'sepsis', 'septicemia',

        # Respiratory & Pulmonology
        'pulmonary', 'pulmonology', 'respiratory', 'lung', 'lungs', 'asthma',
        'copd', 'pneumonia', 'bronchitis', 'tuberculosis', 'tb', 'spirometry',
        'chest', 'pleural', 'oxygen', 'spo2', 'apnea', 'covid', 'influenza',

        # Infectious Diseases & Microorganism Tests
        'malaria', 'dengue', 'typhoid', 'cholera', 'hiv', 'aids', 'herpes',
        'shingles', 'chickenpox', 'measles', 'rabies', 'bacterial', 'viral',
        'fungal', 'parasitic', 'pcr', 'swab', 'sputum', 'stool', 'smear', 'culture',

        # Neurology & Musculoskeletal
        'neurology', 'neurological', 'brain', 'seizure', 'stroke', 'neuropathy',
        'eeg', 'emg', 'migraine', 'epilepsy', 'dementia', 'alzheimer', 'parkinson',
        'arthritis', 'osteoarthritis', 'rheumatoid', 'fracture', 'bone', 'joint',

        # Units & Measurements
        'vital', 'pulse', 'heart rate', 'temperature', 'weight', 'height', 'bmi',
        'mmhg', 'mg/dl', 'g/dl', 'mmol/l', 'iu/l', 'u/l', 'bpm', 'mcg', 'meq/l',
        'ng/ml', 'pg/ml', 'mciu/ml', 'miu/l', 'g/l', 'ref', 'interval', 'range', 'unit'
    ]

    term_matches = sum(1 for term in medical_terms if term in text_lower)

    # 3. Check for numerical lab data patterns (e.g. "Glucose: 95 mg/dL", "12.5 g/dL", "HbA1c: 6.5 %")
    lab_value_pattern = r'\b(\d+(\.\d+)?)\s*(mg/dl|g/dl|mmol/l|iu/l|u/l|bpm|mmhg|%|mcg|meq/l|ng/ml|pg/ml|mciu/ml|miu/l|g/l|cells/mm3|cells/mcl|/hpf|/lpf)\b'
    has_lab_values = bool(re.search(lab_value_pattern, text_lower))

    # Accept if at least 1 medical term match OR has lab value pattern
    if term_matches >= 1 or has_lab_values:
        return True, None

    return False, "Only medical reports are summarized, upload a report"