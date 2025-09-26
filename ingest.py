import argparse
import os
from Document_Handler import load_document
from Data_Handler import chunk_text, embed_texts
from Database_Handler import add_text_chunks

def ingest(paths):
    for p in paths:
        doc = load_document(p)
        chunks = chunk_text(doc["content"])
        if not chunks:
            print(f"[skip] {doc['name']} is empty.")
            continue
        embs = embed_texts(chunks)
        n = add_text_chunks(chunks, embs, source_name=doc["name"], source_path=doc["path"])
        print(f"[ok] Indexed {n} chunks from {doc['name']}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Ingest docs into the vector store.")
    ap.add_argument("paths", nargs="+", help="Files: .txt .md .pdf")
    args = ap.parse_args()
    ingest(args.paths)
