import streamlit as st
from document_handler import load_pdf
from data_handler import chunk_text, embed_chunks
from database_handler import VectorDB
from query_handler import answer_query

st.title("📘 AUTOSAR PDF Q&A")

# Upload PDF
uploaded_file = st.file_uploader("Upload a PDF", type="pdf")

if uploaded_file is not None:
    with open("temp.pdf", "wb") as f:
        f.write(uploaded_file.read())

    # 1️⃣ Load PDF
    text = load_pdf("temp.pdf")

    # 2️⃣ Chunk + embed
    chunks = chunk_text(text)
    embeddings = embed_chunks(chunks)

    # 3️⃣ Create DB
    db = VectorDB(dimension=embeddings[0].shape[0])
    db.add_chunks(embeddings, chunks)

    st.success("✅ PDF processed. You can now ask questions.")

    # 4️⃣ User question
    query = st.text_input("Ask a question about the PDF:")
    if query:
        answer = answer_query(db, query)
        st.subheader("Answer")
        st.write(answer)

