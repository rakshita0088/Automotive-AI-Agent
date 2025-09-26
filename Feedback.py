import csv
import os
from typing import Optional
import config

_HEADER = ["question", "answer", "correct", "notes"]

def record_feedback(question: str, answer: str, correct: bool, notes: Optional[str] = ""):
    file = config.FEEDBACK_CSV
    newfile = not os.path.exists(file)
    with open(file, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if newfile:
            w.writerow(_HEADER)
        w.writerow([question, answer, int(correct), notes or ""])
