# ============================================================
# EXACT FILE LOCATION: backend/services/llm_service.py
# ============================================================
# PURPOSE: Centralized Groq LLM API wrapper.
# Used by both interview_service.py and evaluation_service.py.
# All LLM calls go through this single module.
# ============================================================

import os
import logging
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize Groq client
_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Model to use — llama3 is fast and accurate for structured tasks
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


# ============================================================
# Core chat completion — sends messages to Groq and returns text
# ============================================================
def chat_completion(
    messages: list,
    temperature: float = 0.7,
    max_tokens: int = 1024
) -> str:
    try:
        response = _client.chat.completions.create(
            model       = GROQ_MODEL,
            messages    = messages,
            temperature = temperature,
            max_tokens  = max_tokens,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq API call failed: {e}")
        raise


# ============================================================
# Generate interview questions for a candidate
# Returns a list of dicts: [{question, category}, ...]
# ============================================================
def generate_interview_questions(
    job_title: str,
    job_description: str,
    required_skills: str,
    missing_skills: str,
    candidate_experience: str,
    num_questions: int = 5
) -> list:

    # Build a detailed prompt so Groq generates relevant questions
    system_prompt = (
        "You are a senior technical interviewer. "
        "Generate exactly the requested number of interview questions. "
        "Return ONLY a valid JSON array. No explanation, no markdown, no extra text. "
        "Each item must have: 'question' (string) and 'category' "
        "(one of: TECHNICAL, BEHAVIORAL, PROBLEM_SOLVING)."
    )

    user_prompt = f"""
Generate {num_questions} interview questions for this candidate:

Job Title: {job_title}
Job Description: {job_description[:300]}
Required Skills: {required_skills}
Skills the candidate is MISSING: {missing_skills}
Candidate Experience: {candidate_experience or 'Not specified'}

Rules:
- Focus on missing skills to test knowledge gaps
- Include at least 2 TECHNICAL questions
- Include 1 BEHAVIORAL question
- Include 1 PROBLEM_SOLVING question
- Questions must be specific to the role and skills listed

Return ONLY a JSON array like:
[
  {{"question": "Explain X concept", "category": "TECHNICAL"}},
  {{"question": "How would you handle Y", "category": "PROBLEM_SOLVING"}}
]
"""

    raw = chat_completion(
        messages    = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature = 0.7,
        max_tokens  = 800,
    )

    # Parse JSON response from Groq
    try:
        # Strip any accidental markdown fences
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        questions = json.loads(clean)
        logger.info(f"Generated {len(questions)} interview questions for {job_title}")
        return questions
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Groq question JSON: {e}\nRaw: {raw}")
        # Return a safe fallback set of questions
        return [
            {"question": f"Explain your experience with {required_skills.split(',')[0].strip() if required_skills else 'this role'}.", "category": "TECHNICAL"},
            {"question": "Describe a challenging project you worked on and how you solved a key problem.", "category": "BEHAVIORAL"},
            {"question": f"How would you approach learning {missing_skills.split(',')[0].strip() if missing_skills else 'a new technology'}?", "category": "PROBLEM_SOLVING"},
        ]


# ============================================================
# Evaluate a single candidate answer using Groq LLM
# Returns: score (0-100), feedback string
# ============================================================
def evaluate_answer(
    question: str,
    answer: str,
    job_title: str,
    expected_skills: str
) -> dict:

    system_prompt = (
        "You are a strict but fair technical interviewer evaluating a candidate's answer. "
        "Return ONLY valid JSON. No markdown, no explanation outside the JSON."
    )

    user_prompt = f"""
Evaluate this interview answer:

Job: {job_title}
Expected skills context: {expected_skills}
Question: {question}
Candidate's Answer: {answer}

Score the answer from 0 to 100 based on:
- Technical correctness (40%)
- Relevance to the question (30%)
- Depth of understanding (20%)
- Communication clarity (10%)

Return ONLY JSON:
{{
  "score": <number 0-100>,
  "feedback": "<one or two sentences of specific feedback>"
}}
"""

    raw = chat_completion(
        messages    = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature = 0.3,   # low temperature = more consistent scoring
        max_tokens  = 300,
    )

    try:
        clean  = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        result = json.loads(clean)
        return {
            "score":    float(result.get("score", 50)),
            "feedback": str(result.get("feedback", "No feedback provided.")),
        }
    except Exception as e:
        logger.error(f"Failed to parse evaluation JSON: {e}\nRaw: {raw}")
        return {"score": 50.0, "feedback": "Evaluation could not be parsed."}


# ============================================================
# Generate overall interview summary after all answers evaluated
# ============================================================
def generate_interview_summary(
    candidate_name: str,
    job_title: str,
    question_results: list,    # list of {question, answer, score, feedback}
    avg_score: float
) -> dict:

    qa_text = "\n".join([
        f"Q{i+1}: {r['question']}\nA: {r['answer'][:150]}\nScore: {r['score']}/100"
        for i, r in enumerate(question_results)
    ])

    system_prompt = (
        "You are a senior HR analyst writing a final interview assessment. "
        "Return ONLY valid JSON. No markdown."
    )

    user_prompt = f"""
Write a final interview summary for:
Candidate: {candidate_name}
Job: {job_title}
Average Interview Score: {avg_score:.1f}/100

Interview Q&A Summary:
{qa_text}

Return ONLY JSON:
{{
  "overall_feedback": "<2-3 sentence summary>",
  "strengths": ["<strength 1>", "<strength 2>"],
  "weaknesses": ["<weakness 1>", "<weakness 2>"],
  "recommendation": "<one of: Excellent, Good, Average, Weak>"
}}
"""

    raw = chat_completion(
        messages    = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature = 0.5,
        max_tokens  = 500,
    )

    try:
        clean  = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        result = json.loads(clean)
        return result
    except Exception as e:
        logger.error(f"Failed to parse summary JSON: {e}")
        return {
            "overall_feedback": f"{candidate_name} completed the interview with an average score of {avg_score:.1f}%.",
            "strengths":        ["Completed the interview"],
            "weaknesses":       ["Some answers lacked depth"],
            "recommendation":   "Average" if avg_score >= 50 else "Weak",
        }