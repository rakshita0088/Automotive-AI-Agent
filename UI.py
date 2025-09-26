# UI.py
import streamlit as st
import pandas as pd
import os
import pickle
import time
from graphviz import Source
import streamlit.components.v1 as components
import json
from difflib import get_close_matches
import hashlib
 
from Document_Handler import load_document, load_dbc, load_cdd
from Data_Handler import chunk_text, embed_texts, embed_query, process_document_chunks
from Database_Handler import add_text_chunks, msearch
from LLM_Handler import answer_with_context, answer_with_code, answer_with_flowchart
from valid_answer import add_good_answer, search_good_answer
import config
from QMap_Handler import normalize_question
 
# --- Directories & files ---
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
 
FEEDBACK_FILE = os.path.join(DATA_DIR, "feedback_log.csv")
DOCS_FILE = os.path.join(DATA_DIR, "uploaded_docs.csv")
EMB_CACHE_FILE = os.path.join(DATA_DIR, "embedding_cache.pkl")
QMAP_FILE = os.path.join(DATA_DIR, "Question_Map.json")
 
# --- Load question mapping JSON ---
if os.path.exists(QMAP_FILE):
    with open(QMAP_FILE, "r") as f:
        qmap = json.load(f)
else:
    qmap = {}
 
# --- Extract MODULE_PARAMS_TEMPLATE from Question_Map.json ---
MODULE_PARAMS_TEMPLATE = qmap.get("module_name_parameters", {}).get("config", {})
 
# --- Map user query to canonical ---
def map_to_canonical(query: str) -> str:
    query_clean = query.lower().strip()
    candidates = []
    for key, data in qmap.items():
        canonical = data.get("canonical", "")
        aliases = data.get("aliases", [])
        all_forms = [canonical] + aliases
        for form in all_forms:
            candidates.append((form, canonical))
    for form, canonical in candidates:
        if query_clean == form.lower().strip():
            return canonical
    all_forms_lower = [form.lower().strip() for form, _ in candidates]
    best_match = get_close_matches(query_clean, all_forms_lower, n=1, cutoff=0.6)
    if best_match:
        for form, canonical in candidates:
            if form.lower().strip() == best_match[0]:
                return canonical
    return query
 
# --- Streamlit setup ---
st.set_page_config(page_title="AUTOSAR AI AGENT", layout="wide")
st.title("🚗 AUTOSAR AI AGENT")
 
# --- Session state ---
if "last_answer" not in st.session_state:
    st.session_state.last_answer = None
    st.session_state.last_query = None
    st.session_state.last_canonical = None
    st.session_state.results = None
    st.session_state.answer_generated = False
    st.session_state.query_time_sec = 0.0
    st.session_state.last_flowchart_svg = None
    st.session_state.conversation = []
 
# --- Embedding cache ---
if os.path.exists(EMB_CACHE_FILE):
    with open(EMB_CACHE_FILE, "rb") as f:
        emb_cache = pickle.load(f)
else:
    emb_cache = {}
 
def cached_embed(text: str):
    """
    Return deterministic embedding for a text.
    Uses SHA256 hash as key in embedding cache.
    """
    key = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
 
    if key in emb_cache:
        return emb_cache[key]
 
    emb = embed_query(text)
    emb_cache[key] = emb
 
    with open(EMB_CACHE_FILE, "wb") as f:
        pickle.dump(emb_cache, f)
 
    return emb
 
# --- Feedback ---
def save_feedback(feedback_type):
    df_fb_new = pd.DataFrame([{
        "question": st.session_state.last_query,
        "feedback": feedback_type
    }])
    df_fb_new.to_csv(FEEDBACK_FILE, mode="a", index=False, header=not os.path.exists(FEEDBACK_FILE))
    if feedback_type == "good":
        add_good_answer(st.session_state.last_query, st.session_state.last_answer)
 
# --- Tabs ---
tabs = st.tabs(["📂 Upload Document", "❓ Ask Questions"])
 
# -------- Upload Tab --------
with tabs[0]:
    st.subheader("Upload AUTOSAR Documents")
    files = st.file_uploader(
        "Upload .docx / .md / .pdf / .dbc / .cdd / .arxml files",
        type=["docx", "md", "markdown", "pdf", "dbc", "cdd", "arxml"],
        accept_multiple_files=True
    )
 
    if st.button("Process & Index") and files:
        total = 0
        uploaded_files = []
        os.makedirs("Documents.cache_uploads", exist_ok=True)
 
        for f in files:
            tmp_path = os.path.join("Documents.cache_uploads", f.name)
            with open(tmp_path, "wb") as out:
                out.write(f.read())
 
            ext = os.path.splitext(f.name)[1].lower()
            if ext == ".dbc":
                doc = load_dbc(tmp_path)
            elif ext == ".cdd":
                doc = load_cdd(tmp_path)
            else:  # .docx, .md, .pdf, .arxml
                doc = load_document(tmp_path)
 
            # Flatten chunks and embed
            chunks = process_document_chunks(doc["chunks"])
            embs = embed_texts(chunks)
            added = add_text_chunks(chunks, embs, source_name=doc["name"], source_path=tmp_path)
            total += added
            uploaded_files.append(doc["name"])
 
        st.success(f"Indexed {total} chunks.")
 
        if uploaded_files:
            df = pd.DataFrame(uploaded_files, columns=["document"])
            df.to_csv(DOCS_FILE, mode="a", index=False, header=not os.path.exists(DOCS_FILE))
 
    st.markdown("### 📂 Uploaded Documents")
    if os.path.exists(DOCS_FILE):
        df_docs = pd.read_csv(DOCS_FILE).drop_duplicates()
        st.dataframe(df_docs, width='stretch')
    else:
        st.info("No documents uploaded yet.")
 
# -------- Ask Tab --------
with tabs[1]:
    st.subheader("Ask a Question")
 
    query = st.text_input("Your question about AUTOSAR:", key="query_input", on_change=None)
 
    generate_code = st.checkbox("Generate code snippet", value=False)
    code_language = st.selectbox("Select programming language", ["Python", "C", "C++", "Java"], index=0)
    generate_flowchart = st.checkbox("Generate Flowchart / Diagram", value=False)
 
    # --- Submit function ---
    def submit_question(user_query):
        if not user_query.strip():
            return
 
        query_clean = normalize_question(user_query.strip())
        query_canonical = map_to_canonical(query_clean)
 
        start_time = time.time()
        combined_context = []
 
        # --- Check for module configuration template ---
        config_answer_generated = False
        if query_canonical.lower() == "what are the configuration parameters of module_name":
            if MODULE_PARAMS_TEMPLATE:
                answer_lines = []
                for container, subcontainers in MODULE_PARAMS_TEMPLATE.items():
                    answer_lines.append(f"### {container}")
                    for subcontainer, params in subcontainers.items():
                        answer_lines.append(f"#### {subcontainer}")
                        for param, desc in params.items():
                            answer_lines.append(f"- **{param}**: {desc}")
                new_answer = "\n".join(answer_lines)
                flowchart_svg = None
                config_answer_generated = True
 
        if not config_answer_generated:
            good_hits = search_good_answer(query_canonical)
            if good_hits:
                new_answer = good_hits[0].get("answer", "")
                flowchart_svg = None
            else:
                qvec = cached_embed(query_canonical)
                doc_results = msearch(query_canonical, top_k=config.TOP_K)
 
                if doc_results:
                    for r in doc_results:
                        text_content = r.get("text", "")
                        chunk_type = r.get("type", "paragraph")
                        page_info = r.get("page", "")
                        if "[FIGURE]" in text_content.upper():
                            text_content = "[FIGURE CONTEXT] " + text_content
                        combined_context.append({
                            "source": r.get("source", "doc"),
                            "text": text_content,
                            "type": chunk_type,
                            "page": page_info
                        })
 
                context_text = "\n".join([r["text"] for r in combined_context]) if combined_context else ""
 
                if not context_text:
                    new_answer = "No documents or good answers indexed yet. Please ingest docs first."
                    flowchart_svg = None
                else:
                    if generate_flowchart:
                        dot_code = answer_with_flowchart(query_canonical, combined_context)
                        flowchart_svg = Source(dot_code).pipe(format="svg").decode("utf-8")
                        new_answer = "Flowchart / Diagram generated below."
                    elif generate_code:
                        new_answer = answer_with_code(query_canonical, combined_context, language=code_language)
                        flowchart_svg = None
                    else:
                        new_answer = answer_with_context(query_canonical, context_text)
                        flowchart_svg = None
 
        end_time = time.time()
        total_time = end_time - start_time
 
        st.session_state.last_answer = new_answer
        st.session_state.last_query = user_query
        st.session_state.last_canonical = query_canonical
        st.session_state.results = combined_context
        st.session_state.answer_generated = True
        st.session_state.query_time_sec = total_time
        st.session_state.last_flowchart_svg = flowchart_svg
 
        if not st.session_state.conversation or st.session_state.conversation[0]["question"] != query_canonical:
            st.session_state.conversation.insert(0, {
                "question": query_canonical,
                "answer": new_answer,
                "flowchart_svg": flowchart_svg,
                "results": combined_context
            })
        else:
            st.session_state.conversation[0]["answer"] = new_answer
            st.session_state.conversation[0]["flowchart_svg"] = flowchart_svg
            st.session_state.conversation[0]["results"] = combined_context
 
    if query:
        submit_question(query)
 
    if st.button("Get Answer"):
        submit_question(query)
 
    # --- Display latest Q&A ---
    if st.session_state.conversation:
        latest = st.session_state.conversation[0]
        st.markdown("###  Latest Question & Answer")
        st.markdown(f"**You:** {latest['question']}")
        st.markdown(f"**AUTOSAR AI:** {latest['answer']}")
        if latest.get("flowchart_svg"):
            components.html(
                f"<div style='overflow:auto; border:1px solid #ddd; width:100%; height:400px;'>{latest['flowchart_svg']}</div>",
                height=420,
                scrolling=True
            )
        st.markdown("---")
 
    # --- Display previous Q&A ---
    if len(st.session_state.conversation) > 1:
        st.markdown("###  Previous Questions & Answers")
        for chat in st.session_state.conversation[1:]:
            st.markdown(f"**You:** {chat['question']}")
            st.markdown(f"**AUTOSAR AI:** {chat['answer']}")
            if chat.get("flowchart_svg"):
                components.html(
                    f"<div style='overflow:auto; border:1px solid #ddd; width:100%; height:300px;'>{chat['flowchart_svg']}</div>",
                    height=320,
                    scrolling=True
                )
            st.markdown("---")
 
    # --- Feedback ---
    if st.session_state.last_answer:
        st.markdown("#### Feedback")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("👍 Good", key="good_btn"):
                save_feedback("good")
                st.success("Feedback recorded as GOOD (stored in Good Answers DB)")
        with col2:
            if st.button("👌 Average", key="average_btn"):
                save_feedback("average")
                st.info("Feedback recorded as AVERAGE")
        with col3:
            if st.button("👎 Bad", key="bad_btn"):
                save_feedback("bad")
                st.error("Feedback recorded as BAD")



