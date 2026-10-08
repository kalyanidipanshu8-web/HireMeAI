from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from pathlib import Path
from pypdf import PdfReader
import os

from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel
from typing import List


# ---------------- PYDANTIC MODEL ----------------

class Resume(BaseModel):
    name: str
    email: str
    phone: str
    location: str
    education: str
    technical_skills: List[str]
    programming_languages: List[str]
    frameworks_and_libraries: List[str]
    tools_and_technologies: List[str]
    projects: List[str]
    work_experience: List[str]
    certifications: List[str]
    achievements: List[str]
    interests: List[str]
    career_summary: str
    
# ---------------- CHAT WITH CANDIDATE ----------------

class ChatRequest(BaseModel):
    question: str


def ask_candidate(question: str, resume: Resume):

    system_prompt = f"""
You are an AI assistant representing a job candidate.

Below is everything you know about the candidate.

{resume.model_dump_json(indent=2)}

Rules:

1. Answer only using this information.
2. Never hallucinate.
3. If the answer is not available in the resume, say:
   "That information is not mentioned in the resume."
4. Do not invent skills, experience, education, projects, or achievements.
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": question
            }
        ],
        temperature=0
    )

    return response.choices[0].message.content
def chat_loop(resume: Resume):

    print("\n==============================")
    print("   Resume Chatbot Started")
    print("==============================")
    print("Ask anything about the candidate.")
    print("Type 'exit' to quit.\n")

    while True:

        question = input("You: ")

        if question.lower() == "exit":
            print("Chat ended.")
            break

        answer = ask_candidate(question, resume)

        print(f"\nAI: {answer}\n")

# ---------------- GROQ SETUP ----------------

load_dotenv()

my_api_key = os.getenv("GROQ_API_KEY")

if not my_api_key:
    raise ValueError("Where is the API key maan")

client = Groq(api_key=my_api_key)

model = "openai/gpt-oss-120b"


# ---------------- PDF EXTRACTION ----------------

pdf_path = Path("resume.pdf")


def extract_pdf_text(pdf_path):
    reader = PdfReader(pdf_path)

    text = ""

    for page in reader.pages:
        text += page.extract_text() or ""

    return text


# ---------------- RESUME ANALYSIS ----------------

def analyze_resume(resume_text):

    prompt = f"""
You are an expert resume analysis assistant.

Analyze the resume below and extract information ONLY from the
resume. Never invent, assume, or hallucinate information.

Return ONLY valid JSON matching this structure:

{{
    "name": "",
    "email": "",
    "phone": "",
    "location": "",
    "education": "",
    "technical_skills": [],
    "programming_languages": [],
    "frameworks_and_libraries": [],
    "tools_and_technologies": [],
    "projects": [],
    "work_experience": [],
    "certifications": [],
    "achievements": [],
    "interests": [],
    "career_summary": ""
}}

IMPORTANT RULES:

- Do NOT make up information.
- Do NOT infer information.
- For string fields, if information is missing, use:
  "Not mentioned in the resume."
- For list fields, if information is missing, return an empty list [].
- Interests must contain ONLY interests explicitly mentioned in the resume.
- If no interests are explicitly mentioned, return [].
- technical_skills, programming_languages, frameworks_and_libraries,
  tools_and_technologies, projects, work_experience, certifications,
  achievements, and interests MUST ALWAYS be JSON arrays.
- Keep all extracted information accurate.
- Return valid JSON only.
- Do not use Markdown.
- Do not put the JSON inside ```json blocks.

RESUME:
{resume_text}
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a precise resume extraction assistant."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    result = response.choices[0].message.content

    # Convert JSON string into Pydantic object
    resume = Resume.model_validate_json(result)

    return resume


# ---------------- FASTAPI ----------------

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

resume = None


@app.on_event("startup")
def load_resume():

    global resume

    resume_text = extract_pdf_text(pdf_path)
    resume = analyze_resume(resume_text)

    print("\nResume analyzed successfully.")


@app.get("/")
def home():

    return {
        "message": "HireMeAI is running"
    }


@app.post("/chat")
def chat(request: ChatRequest):

    answer = ask_candidate(request.question, resume)

    return {
        "answer": answer
    }

