"""
AUTOSAR AI Pipeline v11:
- Extracts text per document
- Detects module per document
- Generates module-specific questions only
- Sends questions to local AI agent (http://localhost:8502/predict)
- Verifies answers using semantic scoring
- Logs all results in autosar_results.json
"""

import os
import json
import time
from datetime import datetime
import re
import requests
import fitz  # PyMuPDF

# Import the updated QuestionGenerator and Verifier
from question_generator import QuestionGenerator
from verifier import Verifier

# === Configuration ===
BASE_PATH = "/home/sweng-06/Downloads/Automotive_AI_Agent-AI_Agent_V1.4"
DOCS_FOLDER = os.path.join(BASE_PATH, "Documents.cache_uploads")
RESULT_FILE = os.path.join(BASE_PATH, "autosar_results.json")
QUESTIONS_PER_DOC = 10
AGENT_URL = "http://localhost:8502/predict"
CHUNK_SIZE = 4000


# === AIAgent adapter ===
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
            # Module keyword not found: return first CHUNK_SIZE*3 chars
            return full_context[:CHUNK_SIZE*3]

        start = max(0, idx - CHUNK_SIZE)
        end = min(len(full_context), idx + CHUNK_SIZE)
        return full_context[start:end]

    def answer(self, question, module, full_context):
        """
        Sends the question to the local AI agent.
        Returns (ai_answer:str, used_context:str)
        """
        context = self._get_module_context(module, full_context)
        question_with_instructions = (
            f"{question}\n\n"
            "Answer in detail, include all configuration parameters, default values, interactions, and flows. "
            "Use only the provided context."
        )
        try:
            payload = {"question": question_with_instructions}
            resp = requests.post(AGENT_URL, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            ai_answer = data.get("answer", "").strip()
            if not ai_answer:
                ai_answer = "[Error]: AI agent returned empty answer."
        except Exception as e:
            ai_answer = f"[Error calling local AI agent]: {e}"

        return ai_answer, context


# === Utility Functions ===
def load_existing_questions(path=RESULT_FILE):
    """Load previously asked questions to avoid duplicates."""
    if not os.path.exists(path):
        return set()
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return set(item.get("question", "") for item in data if isinstance(item, dict))
    except Exception:
        return set()


def append_results(new_entries, path=RESULT_FILE):
    """Append verification results to autosar_results.json"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    existing = []
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                existing = json.load(f)
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []

    combined = existing + new_entries
    with open(path, "w") as f:
        json.dump(combined, f, indent=2)
    print(f"💾 Appended {len(new_entries)} entries. Total stored: {len(combined)}")


def extract_text_from_doc(doc_path):
    """Extract text content from a PDF or TXT file."""
    try:
        if doc_path.lower().endswith(".txt"):
            with open(doc_path, "r", errors="ignore") as f:
                return f.read()
        elif doc_path.lower().endswith(".pdf"):
            with fitz.open(doc_path) as pdf:
                return "".join(page.get_text("text") for page in pdf)
    except Exception as e:
        print(f"⚠️ Could not read {doc_path}: {e}")
    return ""


# === Main Pipeline ===
def main():
    print("🚀 Starting AUTOSAR AI pipeline v11...")

    if not os.path.exists(DOCS_FOLDER):
        raise FileNotFoundError(f"Documents folder not found: {DOCS_FOLDER}")

    doc_files = sorted([f for f in os.listdir(DOCS_FOLDER) if os.path.isfile(os.path.join(DOCS_FOLDER, f))])
    prev_questions = load_existing_questions()

    qgen = QuestionGenerator()
    agent = AIAgent()
    verifier = Verifier()
    results = []

    for doc_name in doc_files:
        doc_path = os.path.join(DOCS_FOLDER, doc_name)
        print(f"\n📄 Processing document: {doc_name}")

        doc_context = extract_text_from_doc(doc_path)
        if not doc_context.strip():
            print(f"⚠️ Skipping {doc_name}, empty or unreadable.")
            continue

        # Try to detect module from filename first
        filename_module_map = {
            "DEM": "DEM",
            "DCM": "DCM",
            "CANTP": "CANTP",
            "CANIF": "CANIF",
            "CAN": "CAN",
            "PDUR": "PDUR",
            "COM": "COM",
            "RTE": "RTE",
            "NVM": "NVM"
        }

        module = "GENERAL"
        # Force CANIF if filename contains 'CANIF' (before any other check)
        if "canif" in doc_name.lower():
            module = "CANIF"
        for key, val in filename_module_map.items():
            if key.lower() in doc_name.lower():
                module = val
                break

        # If filename module not found, fallback to context-based detection
        if module == "GENERAL":
            module = qgen.detect_module(doc_name, doc_context)

        


        # Generate new module-specific questions only
        questions = qgen.generate(doc_context, prev_questions, doc_name, QUESTIONS_PER_DOC, module=module)
        if not questions:
            print("❌ No new questions generated for this document.")
            continue

        for i, qdata in enumerate(questions, start=1):
            question = qdata["question"]
            module = qdata.get("module", "GENERAL")

            print(f"\n🧩 [{i}] {question}")
            ai_answer, used_context = agent.answer(question, module, doc_context)
            verification = verifier.verify(question, ai_answer, used_context, module)

            # Retry once if score < threshold
            if verification["score"] < 85:
                retry_prompt = f"Improve your previous answer. Feedback: {verification['feedback']}\n\n" \
                               "Answer in detail, include all configuration parameters, default values, interactions, and flows. Use only the provided context."
                ai_answer, _ = agent.answer(retry_prompt, module, doc_context)
                verification = verifier.verify(question, ai_answer, used_context, module)

            entry = {
                "timestamp": datetime.now().isoformat(),
                "document": doc_name,
                "module": module,
                "question": question,
                "ai_answer": ai_answer,
                "verification": verification
            }

            print(f"→ Verifier: {verification.get('status')} | Score: {verification.get('score')}")
            results.append(entry)
            time.sleep(0.2)

    append_results(results)

    total = len(results)
    passed = sum(1 for r in results if r["verification"]["status"] == "PASS")
    accuracy = round((passed / total) * 100, 2) if total else 0

    print("\n📊 FINAL SUMMARY")
    print(f"✅ Total Questions: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {total - passed}")
    print(f"📈 Accuracy: {accuracy}%")
    print("✅ AUTOSAR AI pipeline finished.")


if __name__ == "__main__":
    main()
