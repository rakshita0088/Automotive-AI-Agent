import os
import json
from openai import OpenAI

class GPTVerifier:
    """
    Robot Framework library to verify AI agent outputs using GPT-4.
    """

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable not set")
        self.client = OpenAI(api_key=api_key)

    def verify_answer(self, question, ai_answer, model="gpt-4"):
        """
        Sends the AI answer and question to GPT to verify correctness.
        Returns score, pass/fail, feedback.
        """
        prompt = f"""
        You are an AI verifier. Evaluate if the AI answer is correct, relevant, and complete.
        Question: {question}
        AI Answer: {ai_answer}
        Provide your evaluation in JSON format with fields:
        - score (0.0-1.0)
        - is_pass (true/false)
        - feedback (brief explanation)
        """

        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        content = response.choices[0].message.content.strip()

        # Try to parse JSON from GPT
        try:
            data = json.loads(content)
            score = float(data.get("score", 0))
            is_pass = bool(data.get("is_pass", False))
            feedback = data.get("feedback", "")
        except Exception:
            # fallback if GPT output is not proper JSON
            score, is_pass, feedback = 0.0, False, content

        return score, is_pass, feedback
