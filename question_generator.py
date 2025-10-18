"""
QuestionGenerator v11
- Generates AUTOSAR questions strictly per document/module
- Avoids using context or keywords from unrelated modules
- Ensures no duplicates from previous runs
"""
 
import os
import re
from openai import OpenAI
 
MODEL = "gpt-4o-mini"
MAX_RETRIES = 2
NUM_QUESTIONS = 10  # per document
 
# Keywords to detect module type in doc name or text
# MODULE_KEYWORDS = {
#     "RTE": [r"\brte\b", r"runtime environment", r"runnable"],
#     "COM": [r"\bcom\b", r"communication module", r"\bsignal\b", r"\bipdu\b"],
#     "PDUR": [r"\bpdur\b", r"\bpdu router\b"],
#     "CANIF": [r"\bcanif\b", r"can interface"],    # first check CANIF
#     "CANTP": [r"\bcantp\b", r"can transport protocol"], # first check CANTP
#     "CAN": [r"\bcan\b", r"\bcan driver\b"],      # CAN exact word only
#     "DCM": [r"\bdcm\b", r"diagnostic communication"],        # precise full-word match
#     "DEM": [r"\bdem\b", r"diagnostic event"],                # precise full-word match
#     "NVM": [r"\bnvm\b", r"non volatile memory", r"nvblock"]
# }
MODULE_KEYWORDS = {
    "RTE": [r"\brte\b", r"\brunnable\b", r"runtime environment"],
    "COM": [r"\bcom\b", r"communication module", r"\bipdu\b", r"\bsignal\b"],
    "PDUR": [r"\bpdur\b", r"\bpdu router\b"],
    "CANIF": [r"\bcanif\b", r"can interface", r"can interface module", r"can interface layer"],
    "CANTP": [r"\bcantp\b", r"can transport protocol"],
    "CAN": [r"\bcan driver\b"],
    "DEM": [r"\bdem\b", r"diagnostic event"],
    "DCM": [r"\bdcm\b", r"diagnostic communication"],
    "NVM": [r"\bnvm\b", r"non volatile memory", r"nvblock"]
}
 
def _get_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment")
    return api_key
 
_client = OpenAI(api_key=_get_api_key())
 
class QuestionGenerator:
    def __init__(self, model=MODEL):
        self.model = model
 
    def detect_module(self, doc_name: str, context: str = "") -> str:
        """
        Detects module based on document name and context.
        Returns module string (RTE, COM, PDUR, etc.) or GENERAL.
        Prioritizes exact module matches using regex word boundaries.
        """
        combined = (doc_name + " " + context[:2000]).lower()
        # Priority order: specific modules first to avoid conflicts
        # priority = ["CANTP", "CANIF", "DCM", "DEM", "CAN", "PDUR", "COM", "RTE", "NVM"]
        # priority = ["CANTP", "CANIF", "DEM", "DCM", "RTE", "COM", "CAN", "PDUR", "NVM"]
        priority = ["CANTP", "CANIF", "DEM", "DCM", "COM", "RTE", "CAN", "PDUR", "NVM"]
 
        for mod in priority:
            keywords = MODULE_KEYWORDS.get(mod, [])
            for kw in keywords:
                if re.search(kw, combined, re.IGNORECASE):
                    return mod
 
        return "GENERAL"
 
    def generate(self, full_context: str, prev_questions: set, doc_name: str,
             num_questions: int = NUM_QUESTIONS, module: str = None):
        """
        Generate new, module-specific AUTOSAR questions from document context.
        Respects the module passed from pipeline; only falls back to detection if module=None.
        """
        # Respect module detected by pipeline
        if not module or module == "GENERAL":
            module = self.detect_module(doc_name, full_context)
 
        if "caninterface" in doc_name.lower() or "can_if" in doc_name.lower():
            module = "CANIF"
        if "LayeredSoftwareArchitecture" in doc_name or "Architecture" in doc_name.lower():
            module = "GENERAL"
        if "SoftwareComponentTemplate" in doc_name or "SWC Template" in doc_name.lower():
            module = "GENERAL"
 
        print(f"🧩 Generating questions for detected module: {module}")
 
        # Prompt strictly instructs the model to generate questions only for this module
        prompt = f"""
    You are an AUTOSAR expert question generator.
 
    Generate {num_questions} unique questions strictly about the **{module} module**.
 
    Requirements:
    0. Keep all questions only about {module} — no other AUTOSAR modules.
    1. Focus on AUTOSAR layers, RTE, COM, PduR, CanIf, CANTp CAN, DCM, DEM, NvM.
    2. Include configurations, parameters, containers, sub-containers, APIs, callbacks, signals, and flows.
    3. Use descriptive keywords: "Explain", "What is", "How does", "Describe the flow", "List all", "Give all".
    4. Include questions specifically about:
    - All configuration containers of a module (e.g., Can, Com, PduR, CanIf)
    - Sub-containers within general and controller configurations
    - All parameters of signals, IPdus, Pdus, RTE runnables, DEM/UDS services
    - ECU configuration parameters and default values
    5. Keep questions concise (10–25 words max).
    6. Include a mix of simple (definitions, roles, purposes, differences) and moderate (interactions, flows, sequences, timers) questions.
    7. Avoid very advanced system-level questions.
    8. Avoid duplicates or rewording of previous questions.
    9. Output as a clean numbered list (1., 2., 3., ...).
    Avoid these previous questions: {list(prev_questions)[:100]}
    """
 
        for attempt in range(MAX_RETRIES):
            try:
                response = _client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.8,
                    max_tokens=1200
                )
 
                raw_output = response.choices[0].message.content.strip()
                # Split by numbered list
                questions = re.split(r"\n\d+\.\s*", raw_output)
                questions = [q.strip() for q in questions if 8 < len(q.strip()) < 200]
 
                # Remove duplicates and previously asked questions
                new_questions = [q for q in questions if q not in prev_questions]
 
                # Return structured list
                result = [
                    {"module": module, "difficulty": "moderate", "question": q}
                    for q in new_questions[:num_questions]
                ]
                return result
 
            except Exception as e:
                print(f"⚠️ Question generation attempt {attempt+1} failed: {e}")
 
        return []