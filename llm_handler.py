# Call OpenAI GPT to generate an answer
# llm_handler.py

from openai import OpenAI
from config import OPENAI_API_KEY, LLM_MODEL, TEMPERATURE, MAX_TOKENS

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def generate_answer(chunks, query):
    """
    Generates an answer using OpenAI based on the top relevant chunks.
    """
    context = "\n".join(chunks)
    prompt = f"Answer the following question based ONLY on the context below:\n\nContext:\n{context}\n\nQuestion: {query}\nAnswer:"

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating answer: {e}"
