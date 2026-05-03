from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import pdfplumber
from docx import Document
from groq import Groq
from dotenv import load_dotenv
import json
import logging

# ---------------- CONFIG ----------------
logging.getLogger("pdfminer").setLevel(logging.ERROR)

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---------------- MODELS ----------------
class EvaluationRequest(BaseModel):
    question: str
    answer: str


class FinalReportRequest(BaseModel):
    evaluations: list


# ---------------- HELPERS ----------------
def clean_ai_json(result: str):
    """
    Removes markdown formatting and safely parses JSON.
    """
    result = result.strip()
    result = result.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(result)
    except:
        return None


# ---------------- ATS SCORE ----------------
def calculate_ats_score(text):
    keywords = [
        "python", "fastapi", "api", "sql",
        "git", "docker", "backend", "developer"
    ]

    text_lower = text.lower()

    match_count = sum(1 for word in keywords if word in text_lower)
    keyword_score = (match_count / len(keywords)) * 40

    length_score = min(len(text) / 500, 1) * 20

    sections = ["education", "skills", "project", "experience"]
    section_score = sum(1 for s in sections if s in text_lower) * 10

    return round(keyword_score + length_score + section_score, 2)


# ---------------- FILE PARSING ----------------
def parse_pdf(file_path):
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception as e:
        print("PDF Error:", e)

    return text


def parse_docx(file_path):
    try:
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        print("DOCX Error:", e)
        return ""


# ---------------- AI ANALYSIS ----------------
def analyze_resume_with_ai(text, role, level, experience):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": f"""
You are an expert ATS resume analyzer.

Analyze this resume for:

Role: {role}
Level: {level}
Experience: {experience} years

Return ONLY valid JSON in this exact format:

{{
    "strengths": [
        "strength 1",
        "strength 2"
    ],
    "weaknesses": [
        "weakness 1",
        "weakness 2"
    ],
    "missing_keywords": [
        "keyword1",
        "keyword2"
    ],
    "suggestions": [
        "suggestion1",
        "suggestion2"
    ]
}}

Resume:
{text[:2000]}
"""
                }
            ],
            temperature=0.5
        )

        result = response.choices[0].message.content.strip()

        result = result.replace("```json", "").replace("```", "").strip()

        return json.loads(result)

    except Exception as e:
        print("AI Error:", e)

        return {
            "strengths": [],
            "weaknesses": [],
            "missing_keywords": [],
            "suggestions": []
        }


# ---------------- INTERVIEW QUESTIONS ----------------
def generate_interview_questions(text, role, level, experience):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": f"""
You are an AI interviewer.

Generate exactly 5 interview questions.

Role: {role}
Level: {level}
Experience: {experience} years

Rules:
- 2 technical
- 1 project-based
- 1 behavioral
- 1 HR

Return ONLY JSON array:
[
 "Question 1",
 "Question 2",
 "Question 3",
 "Question 4",
 "Question 5"
]

Resume:
{text[:2000]}
"""
                }
            ],
            temperature=0.7
        )

        result = response.choices[0].message.content

        parsed = clean_ai_json(result)

        if parsed:
            return parsed

        return [
            q.strip("- ").strip()
            for q in result.split("\n")
            if q.strip()
        ]

    except Exception as e:
        return [f"Error generating questions: {str(e)}"]


# ---------------- ROUTES ----------------
@app.get("/")
def home():
    return {"message": "Backend Running 🚀"}


# ---------------- RESUME ANALYZER ----------------
@app.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    role: str = Form(...),
    level: str = Form(...),
    experience: str = Form(...),
    technologies: str = Form("")   # ✅ ADD THIS
):
    file_ext = file.filename.split(".")[-1].lower()
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    # ✅ SAVE FILE
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # ✅ EXTRACT TEXT FIRST
    if file_ext == "pdf":
        text = parse_pdf(file_path)

    elif file_ext == "docx":
        text = parse_docx(file_path)

    else:
        return {"error": "Unsupported file type"}

    print("TEXT LENGTH:", len(text))

    # ❗ SAFETY CHECK
    if not text.strip():
        return {
            "filename": file.filename,
            "text": "",
            "ats_score": 0,
            "match_score": 0,
            "analysis": {},
            "error": "No text extracted"
        }

    # ✅ NOW CALL AI (AFTER TEXT READY)
    match_data = calculate_match_score_ai(
        text, role, technologies, experience
    )

    score = calculate_ats_score(text)
    analysis = analyze_resume_with_ai(text, role, level, experience)

    return {
        "filename": file.filename,
        "text": text,
        "ats_score": score,
        "match_score": match_data["match_score"],
        "match_reason": match_data["reason"],
        "analysis": analysis
    }

# ---------------- START INTERVIEW ----------------
@app.post("/interview")
async def start_interview(
    file: UploadFile = File(...),
    role: str = Form(...),
    level: str = Form(...),
    experience: str = Form(...)
):
    file_ext = file.filename.split(".")[-1].lower()
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    if file_ext == "pdf":
        text = parse_pdf(file_path)

    elif file_ext == "docx":
        text = parse_docx(file_path)

    else:
        return {"error": "Unsupported file"}

    questions = generate_interview_questions(text, role, level, experience)

    return {
        "questions": questions
    }


# ---------------- EVALUATE ANSWER ----------------
@app.post("/evaluate")
async def evaluate_answer(data: EvaluationRequest):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": f"""
You are a professional interviewer.

Evaluate candidate's answer.

Question:
{data.question}

Answer:
{data.answer}

Return ONLY JSON:
{{
 "score": number,
 "feedback": "short feedback",
 "improvements": "how to improve",
 "confidence": "low/medium/high"
}}
"""
                }
            ],
            temperature=0.5
        )

        result = response.choices[0].message.content

        parsed = clean_ai_json(result)

        if parsed:
            return parsed

        return {
            "score": 5,
            "feedback": result,
            "improvements": "Try to improve clarity.",
            "confidence": "medium"
        }

    except Exception as e:
        return {"error": str(e)}


# ---------------- FINAL REPORT ----------------
@app.post("/final-report")
async def final_report(data: FinalReportRequest):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": f"""
Analyze these interview evaluations:

{data.evaluations}

Return ONLY JSON:
{{
 "overall_summary":"Overall performance summary",
 "strengths":["strength1","strength2"],
 "weaknesses":["weakness1","weakness2"],
 "recommendations":["tip1","tip2"]
}}
"""
                }
            ],
            temperature=0.5
        )

        result = response.choices[0].message.content

        parsed = clean_ai_json(result)

        if parsed:
            return parsed

        return {
            "overall_summary": result,
            "strengths": [],
            "weaknesses": [],
            "recommendations": []
        }

    except Exception as e:
        return {"error": str(e)}
    
# ---------------- CANDIDATE OVERVIEW ----------------
def calculate_match_score_ai(text, role, technologies, experience):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": f"""
You are an AI recruiter.

Evaluate how well this resume matches the job.

Job Requirements:
Role: {role}
Technologies: {technologies}
Experience: {experience} years

Resume:
{text[:2000]}

Return ONLY JSON:
{{
  "match_score": number (0-100),
  "reason": "short explanation"
}}
"""
                }
            ],
            temperature=0.3
        )

        result = response.choices[0].message.content
        parsed = clean_ai_json(result)

        if parsed:
            return parsed

        return {"match_score": 0, "reason": "error"}

    except Exception as e:
        print("AI Match Error:", e)
        return {"match_score": 0, "reason": "error"}