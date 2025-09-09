from document_handler import load_pdf
from data_handler import chunk_text, embed_chunks
from database_handler import VectorDB
from query_handler import answer_query
from llm_handler import generate_answer

PDF_PATH = "/home/sweng-06/Documents/AUTOSAR_SWS_PDURouter 4.4.0.pdf"

# Load PDF
text = load_pdf(PDF_PATH)

# Chunk and embed
chunks = chunk_text(text)
embeddings = embed_chunks(chunks)

# Create DB and add chunks
db = VectorDB(dimension=embeddings[0].shape[0])
db.add_chunks(embeddings, chunks)

# Ask questions
while True:
    query = input("Enter your question (or 'exit'): ")
    if query.lower() == "exit":
        break
    answer = answer_query(db, query)
    print("\nAnswer:\n", answer, "\n")

