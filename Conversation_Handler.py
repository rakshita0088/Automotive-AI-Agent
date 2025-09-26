# Conversation_Handler.py (Offline / Local Version)
import re

def rewrite_question_offline(current_question: str, conversation_history: list, max_history: int = 3) -> str:
    """
    Rewrites the current question to include context from previous conversation
    using simple offline heuristics.

    Args:
        current_question: The latest user question.
        conversation_history: List of previous Q&A dicts: {"question": ..., "answer": ...}
        max_history: Number of previous Q&A to include for context.

    Returns:
        Rewritten question as a self-contained string.
    """
    if not conversation_history:
        return current_question

    # Take last max_history questions
    recent_questions = [qa['question'] for qa in conversation_history[-max_history:]]

    # Heuristic: if current question starts with a pronoun or is short, prepend previous context
    pronouns = ["it", "this", "that", "these", "those", "they", "them", "its"]
    first_word = current_question.strip().split(" ")[0].lower()

    if first_word in pronouns or len(current_question.split()) < 5:
        context = " / ".join(recent_questions)
        rewritten_question = f"In context of: {context}, {current_question}"
    else:
        rewritten_question = current_question

    # Clean extra spaces
    rewritten_question = re.sub(r"\s+", " ", rewritten_question).strip()
    return rewritten_question
