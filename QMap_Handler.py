# QuestionMapper.py
import json
 
MAP_FILE = "Question_Map.json"  # your merged canonical + aliases JSON
 
with open(MAP_FILE, "r") as f:
    question_map = json.load(f)
 
def normalize_question(query: str) -> str:
    """
    Map any user question (module or configuration) to its canonical question.
    """
    q_lower = query.lower().strip()
 
    for _, entry in question_map.items():
        # Match canonical question itself
        if q_lower == entry["canonical"].lower():
            return entry["canonical"]
        # Match any alias
        for alias in entry.get("aliases", []):
            if q_lower == alias.lower():
                return entry["canonical"]
 
    return query  # fallback if no match found