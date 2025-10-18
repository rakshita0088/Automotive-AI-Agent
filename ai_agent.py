import requests
 
CHUNK_SIZE = 4000
AGENT_URL = "http://localhost:8502/predict"
 
class AIAgent:
    def __init__(self):
        pass
 
    def _get_module_context(self, module, full_context):
        """
        Return only relevant context for the module.
        No fallback to other modules.
        """
        if not module or module == "GENERAL":
            return full_context[:CHUNK_SIZE*3]
 
        key = module.lower()
        idx = full_context.lower().find(key)
        if idx == -1:
            # If module keyword not found, just return first CHUNK_SIZE*3 chars
            return full_context[:CHUNK_SIZE*3]
 
        start = max(0, idx - CHUNK_SIZE)
        end = min(len(full_context), idx + CHUNK_SIZE)
        return full_context[start:end]
 
    def answer(self, question, module, full_context):
        """
        Sends the question to the local AI agent.
        Always returns a tuple: (ai_answer:str, used_context:str)
        """
        # Get module-specific context
        context = self._get_module_context(module, full_context)
 
        # Add detailed instruction
        question_with_instruction = (
            f"{question}\n\n"
            "Answer in detail, include all configuration parameters, default values, interactions, and flows. "
            "Use only the provided context."
        )
 
        try:
            payload = {"question": question_with_instruction}
            resp = requests.post(AGENT_URL, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            ai_answer = data.get("answer", "").strip()
 
            if not ai_answer:
                ai_answer = "[Error]: AI agent returned empty answer."
 
        except Exception as e:
            ai_answer = f"[Error calling local AI agent]: {e}"
 
        return ai_answer, context