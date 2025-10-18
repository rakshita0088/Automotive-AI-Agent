"""
Verifier:
- Uses OpenAI to evaluate AI answers relative to docs context
- Returns dict: {score, feedback, status}
"""
import re
import json
import os
from openai import OpenAI
 
MODEL = "gpt-4o-mini"
PASS_THRESHOLD = 85
MAX_RETRIES = 2
 
def _get_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found")
    return api_key
 
_client = OpenAI(api_key=_get_api_key())
 
class Verifier:
    def __init__(self, model=MODEL):
        self.model = model
 
    def verify(self, question, ai_answer, context, module):
        """
        Verifies AI answer against module context.
        Returns dict: {score:int, feedback:str, status:"PASS"/"FAIL"}
        """
        if not ai_answer or ai_answer.startswith("[Error"):
            return {"score": 0, "feedback": "No valid AI answer returned", "status": "FAIL"}
 
        trimmed_context = (context or "")#[:100000]
 
        prompt = f"""
You are an AUTOSAR expert evaluator.
 
Question:
{question}
 
AI Answer:
{ai_answer}
 
Context (trimmed):
{trimmed_context}
 
Evaluate the AI answer for correctness and completeness relative to the provided context.
Return ONLY a JSON object exactly in this format:
{{"score": <integer 0-100>, "feedback": "<short reason>", "status": "PASS" or "FAIL"}}
Pass if score >= {PASS_THRESHOLD}.
"""
 
        for attempt in range(MAX_RETRIES):
            try:
                resp = _client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=600
                )
                raw = resp.choices[0].message.content.strip()
                m = re.search(r'\{.*\}', raw, re.DOTALL)
                if m:
                    obj = json.loads(m.group())
                    score = int(obj.get("score", 0))
                    status = "PASS" if score >= PASS_THRESHOLD else "FAIL"
                    feedback = obj.get("feedback", "")
                    return {"score": score, "feedback": feedback, "status": status}
            except Exception as e:
                print(f"⚠️ Verifier attempt failed: {e}")
 
        return {"score": 0, "feedback": "Verifier failed to return JSON", "status": "FAIL"}