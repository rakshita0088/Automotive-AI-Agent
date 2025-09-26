from fastapi import FastAPI
from pydantic import BaseModel
from UI import normalize_question, map_to_canonical, cached_embed, msearch, search_good_answer
from LLM_Handler import answer_with_context, answer_with_code, answer_with_flowchart

app = FastAPI(title="AUTOSAR AI Agent API")

class QuestionRequest(BaseModel):
    question: str
    generate_code: bool = False
    code_language: str = "Python"
    generate_flowchart: bool = False

@app.post("/predict")
def predict(q: QuestionRequest):
    query_clean = normalize_question(q.question.strip())
    query_canonical = map_to_canonical(query_clean)
    combined_context = []

    # Check for good answers first
    good_hits = search_good_answer(query_canonical)
    if good_hits:
        answer = good_hits[0].get("answer", "")
    else:
        qvec = cached_embed(query_canonical)
        doc_results = msearch(query_canonical, top_k=5)
        if doc_results:
            for r in doc_results:
                text_content = r.get("text", "")
                chunk_type = r.get("type", "paragraph")
                if "[FIGURE]" in text_content.upper():
                    text_content = "[FIGURE CONTEXT] " + text_content
                combined_context.append({
                    "source": r.get("source", "doc"),
                    "text": text_content,
                    "type": chunk_type
                })

        context_text = "\n".join([r["text"] for r in combined_context]) if combined_context else ""

        if not context_text:
            answer = "No documents or good answers indexed yet. Please ingest docs first."
        else:
            if q.generate_flowchart:
                dot_code = answer_with_flowchart(query_canonical, combined_context)
                answer = "Flowchart / Diagram generated"
            elif q.generate_code:
                answer = answer_with_code(query_canonical, combined_context, language=q.code_language)
            else:
                answer = answer_with_context(query_canonical, context_text)

    return {"answer": answer}
