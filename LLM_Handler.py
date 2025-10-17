# LLM_Handler.py (Strict doc-only enforcement for AUTOSAR)
import os
from openai import OpenAI
import tiktoken
from typing import List, Dict
import config
from graphviz import Digraph
import re

# ---------------------------
# API Key Handling
# ---------------------------
def get_api_key():
    api_key = os.getenv("OPENAI_API_KEY") or getattr(config, "OPENAI_API_KEY", None)
    if not api_key:
        raise ValueError(
            "OpenAI API key not found. "
            "Set OPENAI_API_KEY as environment variable or in config.py"
        )
    return api_key

# Initialize OpenAI client
_client = OpenAI(api_key=get_api_key())

# ---------------------------
# Token Helpers
# ---------------------------
def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))

def safe_trim_context(context_text: str, model: str = "gpt-4o-mini", max_tokens: int = 30000) -> str:
    enc = tiktoken.encoding_for_model(model)
    tokens = enc.encode(context_text)
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
    return enc.decode(tokens)

# ---------------------------
# Doc-only Enforcement
# ---------------------------
# def enforce_doc_only(answer: str, context_text: str) -> str:
#     """
#     Ensure that the answer contains only parameters, containers, sub-containers, and APIs
#     that exist in the retrieved AUTOSAR context. Remove or mark anything not in the context.
#     """

#     # 1. Extract potential container/parameter/API names from answer
#     # Matches RTE, PduR, Com, CanIf, Dcm, CanTp APIs and container/sub-container names
#     pattern = r"\b(?:Rte|PduR|Com|CanIf|Dcm|CanTp|[A-Z][A-Za-z0-9_-]*)\b"
#     tokens_in_answer = re.findall(pattern, answer)

#     # 2. Extract tokens from context
#     tokens_in_context = set(re.findall(pattern, context_text))

#     # 3. Filter answer tokens against context tokens
#     filtered_answer = answer
#     for token in set(tokens_in_answer):
#         if token not in tokens_in_context:
#             # Replace any token not in context with a placeholder note
#             filtered_answer = re.sub(rf"\b{re.escape(token)}\b",
#                                      f"[{token} not in AUTOSAR doc]",
#                                      filtered_answer)

#     # 4. Clean up extra blank lines
#     filtered_answer = re.sub(r'\n\s*\n', '\n', filtered_answer).strip()

#     return filtered_answer
# def enforce_doc_only(answer: str, context_text: str) -> str:
#     """
#     Ensure the answer contains ONLY containers/sub-containers and parameters
#     that exist in the context. Any container not present in the context is removed.
#     Ensure the answer contains ONLY items from the given context.
#     If module='RTE', enforce stricter filtering for RTE APIs/params.
#     """

#     # Extract all container/sub-container names from the context
#     container_pattern = r"\b[A-Z][A-Za-z0-9_-]+\b"
#     context_containers = set(re.findall(container_pattern, context_text))

#     # Filter answer lines
#     filtered_lines = []
#     include_line = False
#     for line in answer.splitlines():
#         stripped = line.strip()
#         if not stripped:
#             continue
#         # Always include description lines
#         if stripped.lower().startswith("description:"):
#             if include_line:
#                 filtered_lines.append(stripped)
#             continue

#         # Check if this line mentions a container/sub-container
#         tokens = re.findall(container_pattern, stripped)
#         # Only include lines where at least one token exists in context
#         if any(token in context_containers for token in tokens):
#             filtered_lines.append(stripped)
#             include_line = True
#         else:
#             include_line = False  # skip lines not in context

#     return "\n".join(filtered_lines)
def enforce_doc_only(answer: str, context_text: str, relaxed: bool = False) -> str:
    """
    If relaxed=True, allow AI to include answers even if items are not in the context.
    Strict filtering is only applied if relaxed=False.
    """
    if relaxed:
        return answer  # allow general knowledge

    # existing strict doc-only filtering
    container_pattern = r"\b[A-Z][A-Za-z0-9_-]+\b"
    context_containers = set(re.findall(container_pattern, context_text))

    filtered_lines = []
    include_line = False
    for line in answer.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith("description:"):
            if include_line:
                filtered_lines.append(stripped)
            continue
        tokens = re.findall(container_pattern, stripped)
        if any(token in context_containers for token in tokens):
            filtered_lines.append(stripped)
            include_line = True
        else:
            include_line = False
    return "\n".join(filtered_lines)



# ---------------------------
# Flowchart / DOT validation
# ---------------------------
def validate_dot(dot_code: str, question: str) -> str:
    if not dot_code.strip().startswith("digraph"):
        return f'digraph G {{\nlabel="{question}";\n"Start" -> "End";\n}}'
    return dot_code

# ---------------------------
# Build messages (system + user)
# ---------------------------
def build_messages(user_query: str, context_text: str = "", figure_only: bool = False) -> List[Dict]:
    system_prompt = getattr(config, "SYSTEM_PROMPT", "")
    lower_query = user_query.lower()


    if figure_only:
        clarification = (
            "Important:\n"
            "- Extract ONLY the exact steps and parameters, containers, sub-containers, and references "
            "from the sequence diagram or figure context.\n"
            "- Preserve numbering, API names, and order.\n"
            "- Do NOT summarize, generalize, or reword.\n"
            "- Use context strictly as-is."
        )
    elif "rte" in user_query.lower():
        clarification = (
            "Important:\n"
            "- Answer strictly using ONLY the provided RTE documentation context.\n"
            "- List APIs, parameters, or flows exactly as in the RTE spec.\n"
            "- Do NOT create or guess any RTE APIs or config.\n"
            "- If an API/parameter is not found in the context, explicitly state: "
            "\"This API/parameter is not available in the provided documentation.\""
        )
    elif "parameter" in user_query.lower() or "config" in user_query.lower() or "container" in user_query.lower():
        clarification = (
            "Important:\n"
            "- Extract and list ALL configuration parameters, containers, sub-containers, and references "
            "from the provided AUTOSAR documentation.\n"
            "- Do NOT skip, summarize, or combine parameters.\n"
            "- Preserve exact naming, order, and hierarchy as given in the documents.\n"
            "- Answer must include the FULL set of parameters present in context, not just a subset.\n"
            "- Do not invent any parameter, container, or sub-container."
        )
    else:
        clarification = (
            "Important:\n"
            "- Only use APIs and flows that appear in the provided AUTOSAR documents.\n"
            "- Do NOT generate or invent new APIs.\n"
            "- For RTE questions: Only use APIs explicitly from RTE documents.\n"
            "- For PduR/COM: Only use APIs from PduR and COM documents.\n"
            "- For communication stack: Do NOT include CanTp or DCM.\n"
            "- For diagnostic stack: Include CanTp APIs ONLY if context provides them.\n"
            "- If API is missing in documents, explicitly say: "
            "\"This API is not available in the provided AUTOSAR documentation.\""
        )

    messages = [{"role": "system", "content": system_prompt}]

    if context_text:
        messages.append({
            "role": "user",
            "content": f"{clarification}\nContext:\n{context_text}\n\nQuestion: {user_query}"
        })
    else:
        messages.append({
            "role": "user",
            "content": f"{clarification}\nQuestion: {user_query}"
        })

    return messages

# ---------------------------
# General Answer
# ---------------------------
def answer_with_context(query: str, context_text: str = "", model: str = "gpt-4o-mini",
                        max_context_tokens: int = 30000, figure_only: bool = False) -> str:
    """
    Answers a question using the provided AUTOSAR context.
    - Strict doc-only filtering for RTE questions.
    - Relaxed filtering for other modules: COM, CanIf, PduR, DEM, DCM.
    """
    safe_context = safe_trim_context(context_text, model=model, max_tokens=max_context_tokens)
    
    # Determine module for relaxed or strict filtering
    query_lower = query.lower()
    if "rte" in query_lower:
        # Strict RTE context only
        module_context = "\n".join([line for line in safe_context.splitlines() if "Rte" in line or "RTE" in line])
        relaxed = False
    else:
        # Allow other modules to use context
        module_context = safe_context
        relaxed = any(x in query_lower for x in ["dcm", "dem", "canif", "pdur", "com", "can"])

    messages = build_messages(query, module_context, figure_only=figure_only)

    resp = _client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
        max_tokens=1500
    )

    raw_answer = resp.choices[0].message.content.strip()
    return enforce_doc_only(raw_answer, module_context, relaxed=relaxed)


# def answer_with_context(query: str, context_text: str = "", model: str = "gpt-4o-mini",
#                         max_context_tokens: int = 30000, figure_only: bool = False) -> str:
#     safe_context = safe_trim_context(context_text, model=model, max_tokens=max_context_tokens)
#     messages = build_messages(query, safe_context, figure_only=figure_only)

#     resp = _client.chat.completions.create(
#         model=model,
#         messages=messages,
#         temperature=0,
#         max_tokens=1500
#     )
#     raw_answer = resp.choices[0].message.content.strip()
#     return enforce_doc_only(raw_answer, safe_context)
# def answer_with_context(query: str, context_text: str = "", model: str = "gpt-4o-mini",
#                         max_context_tokens: int = 30000, figure_only: bool = False) -> str:
#     # If the query is about RTE, filter the context strictly to RTE docs
#     if "rte" in query.lower():
#         context_lines = context_text.splitlines()
#         rte_only = [line for line in context_lines if "Rte" in line or "RTE" in line]
#         safe_context = safe_trim_context("\n".join(rte_only), model=model, max_tokens=max_context_tokens)
#     else:
#         safe_context = safe_trim_context(context_text, model=model, max_tokens=max_context_tokens)

#     messages = build_messages(query, safe_context, figure_only=figure_only)

#     resp = _client.chat.completions.create(
#         model=model,
#         messages=messages,
#         temperature=0,
#         max_tokens=1500
#     )
#     raw_answer = resp.choices[0].message.content.strip()
#     return enforce_doc_only(raw_answer, safe_context)

# ---------------------------
# Code Generation
# ---------------------------
def answer_with_code(question: str, retrieved_chunks: List[Dict], language: str = "C",
                     model: str = "gpt-4o-mini", max_context_tokens: int = 25000) -> str:
    context_text = "\n".join([c.get("text", "") for c in retrieved_chunks]) if retrieved_chunks else ""
    if context_text:
        safe_context = safe_trim_context(context_text, model=model, max_tokens=max_context_tokens)
        prompt_text = (
            f"Use ONLY the following context to answer the question and generate {language} code.\n"
            f"Context:\n{safe_context}\n\nQuestion: {question}\n"
            f"Generate working {language} code only."
        )
    else:
        prompt_text = f"Question: {question}\nGenerate working {language} code only."

    messages = build_messages(prompt_text)
    resp = _client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
        max_tokens=1000
    )
    raw_answer = resp.choices[0].message.content.strip()
    return enforce_doc_only(raw_answer, context_text)

# ---------------------------
# Flowchart / Block Diagram
# ---------------------------
def answer_with_flowchart(question: str, retrieved_chunks: List[Dict], model: str = "gpt-4o-mini") -> str:
    context_text = "\n".join([c.get("text", "") for c in retrieved_chunks]) if retrieved_chunks else ""
    prompt_text = (
        f"Use the following context to generate a DOT code for a flowchart or block diagram.\n"
        f"{context_text}\n\nQuestion: {question}\n"
        f"Output ONLY valid Graphviz DOT code with nodes and edges, no explanations, no markdown."
    )

    messages = build_messages(prompt_text)
    resp = _client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
        max_tokens=1000
    )

    dot_code = resp.choices[0].message.content.strip()
    return validate_dot(dot_code, question)

# def answer_with_large_context(query: str, full_context: str,
#                               model: str = "gpt-4o-mini",
#                               chunk_size: int = 4000,
#                               max_context_tokens: int = 30000) -> str:
#     """
#     Automatically split large context into chunks and answer each chunk,
#     then merge intelligently into a single answer.
#     """
#     # 1. Trim context safely
#     safe_context = safe_trim_context(full_context, model=model, max_tokens=max_context_tokens)

#     # 2. Split into chunks
#     chunks = [safe_context[i:i+chunk_size] for i in range(0, len(safe_context), chunk_size)]

#     all_answers = []
#     for idx, chunk in enumerate(chunks, 1):
#         try:
#             part = answer_with_context(query, chunk, model=model)
#             all_answers.append(part)
#         except Exception as e:
#             all_answers.append(f"[Error in chunk {idx}]: {e}")

#     # 3. Merge answers intelligently (remove duplicates)
#     merged = "\n".join(all_answers)
#     lines = merged.splitlines()
#     seen = set()
#     deduped = []
#     for line in lines:
#         line_strip = line.strip()
#         if line_strip and line_strip not in seen:
#             deduped.append(line_strip)
#             seen.add(line_strip)

#     return "\n".join(deduped)
def answer_with_large_context(query: str, full_context: str,
                              model: str = "gpt-4o-mini",
                              chunk_size: int = 4000,
                              max_context_tokens: int = 30000) -> str:
    safe_context = safe_trim_context(full_context, model=model, max_tokens=max_context_tokens)
    chunks = [safe_context[i:i+chunk_size] for i in range(0, len(safe_context), chunk_size)]

    all_answers = []
    for idx, chunk in enumerate(chunks, 1):
        try:
            part = answer_with_context(query, chunk, model=model)
            all_answers.append(part)
        except Exception as e:
            all_answers.append(f"[Error in chunk {idx}]: {e}")

    merged = "\n".join(all_answers)
    seen = set()
    deduped = []
    for line in merged.splitlines():
        line_strip = line.strip()
        if line_strip and line_strip not in seen:
            deduped.append(line_strip)
            seen.add(line_strip)
    return "\n".join(deduped)




# # LLM_Handler.py (Enhanced Dynamic Module-Based Doc-Only Enforcement for AUTOSAR)
# import os
# import json
# import re
# from typing import List, Dict
# from openai import OpenAI
# import tiktoken
# from graphviz import Digraph
# import config

# # ---------------------------
# # API Key Handling
# # ---------------------------
# def get_api_key():
#     api_key = os.getenv("OPENAI_API_KEY") or getattr(config, "OPENAI_API_KEY", None)
#     if not api_key:
#         raise ValueError(
#             "OpenAI API key not found. "
#             "Set OPENAI_API_KEY as environment variable or in config.py"
#         )
#     return api_key

# # Initialize OpenAI client
# _client = OpenAI(api_key=get_api_key())

# # ---------------------------
# # Token Helpers
# # ---------------------------
# def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
#     enc = tiktoken.encoding_for_model(model)
#     return len(enc.encode(text))

# def safe_trim_context(context_text: str, model: str = "gpt-4o-mini", max_tokens: int = 30000) -> str:
#     enc = tiktoken.encoding_for_model(model)
#     tokens = enc.encode(context_text)
#     if len(tokens) > max_tokens:
#         tokens = tokens[:max_tokens]
#     return enc.decode(tokens)

# # Optional per-module token limits
# MODULE_TOKEN_LIMIT = {
#     "RTE": 5000,
#     "COM": 4000,
#     "PduR": 4000,
#     "DCM": 3000,
#     "DEM": 3000,
#     "NVM": 3000,
#     "MEMIF": 3000,
#     "CanIf": 2000,
#     "CanTp": 2000,
#     "CAN DRIVER": 2000,
#     "SWC MODELING": 3500
# }

# def safe_trim_context_by_module(context_text: str, modules: list, model: str = "gpt-4o-mini") -> str:
#     limit = max(MODULE_TOKEN_LIMIT.get(m, 3000) for m in modules)
#     return safe_trim_context(context_text, model=model, max_tokens=limit)

# # ---------------------------
# # Dynamic Module Extraction
# # ---------------------------
# ALL_MODULES = [
#     "RTE", "COM", "PduR", "DCM", "DEM", "NVM", "MEMIF", "CanIf", "CanTp",
#     "CAN DRIVER", "CAN TRANSPORT LAYER", "CAN DATABASE", "SWC MODELING"
# ]

# def extract_module_from_query(query: str) -> list:
#     query_lower = query.lower()
#     found = []
#     for mod in ALL_MODULES:
#         if mod.lower() in query_lower:
#             found.append(mod)
#     return found if found else ALL_MODULES  # use all modules if none detected


# def filter_context_by_module(context_text: str, modules: List[str]) -> str:
#     """Return context lines that mention at least one of the modules."""
#     filtered_lines = [line for line in context_text.splitlines()
#                       if any(mod.lower() in line.lower() for mod in modules)]
#     return "\n".join(filtered_lines) if filtered_lines else context_text

# # ---------------------------
# # Doc-only Enforcement
# # ---------------------------
# def enforce_doc_only(answer: str, context_text: str) -> str:
#     """
#     Ensure the answer contains ONLY containers/sub-containers and parameters
#     that exist in the context.
#     """
#     container_pattern = r"\b[A-Z][A-Za-z0-9_-]+\b"
#     context_containers = set(re.findall(container_pattern, context_text))

#     filtered_lines = []
#     include_line = False
#     for line in answer.splitlines():
#         stripped = line.strip()
#         if not stripped:
#             continue
#         # Include description lines if the previous line is included
#         if stripped.lower().startswith("description:"):
#             if include_line:
#                 filtered_lines.append(stripped)
#             continue
#         # Check if this line mentions a container/sub-container
#         tokens = re.findall(container_pattern, stripped)
#         if any(token in context_containers for token in tokens):
#             filtered_lines.append(stripped)
#             include_line = True
#         else:
#             include_line = False
#     return "\n".join(filtered_lines)

# # ---------------------------
# # Flowchart / DOT validation
# # ---------------------------
# def validate_dot(dot_code: str, question: str) -> str:
#     if not dot_code.strip().startswith("digraph"):
#         return f'digraph G {{\nlabel="{question}";\n"Start" -> "End";\n}}'
#     return dot_code

# # ---------------------------
# # Build messages (system + user)
# # ---------------------------
# def build_messages(user_query: str, context_text: str = "", figure_only: bool = False) -> List[Dict]:
#     system_prompt = getattr(config, "SYSTEM_PROMPT", "")

#     if figure_only:
#         clarification = (
#             "Important:\n"
#             "- Extract ONLY the exact steps, parameters, containers, sub-containers, and references "
#             "from the sequence diagram or figure context.\n"
#             "- Preserve numbering, API names, and order.\n"
#             "- Do NOT summarize, generalize, or reword.\n"
#             "- Use context strictly as-is."
#         )
#     elif "rte" in user_query.lower():
#         clarification = (
#             "Important:\n"
#             "- Answer strictly using ONLY the provided RTE documentation context.\n"
#             "- List APIs, parameters, or flows exactly as in the RTE spec.\n"
#             "- Do NOT create or guess any RTE APIs or config.\n"
#             "- If an API/parameter is not found in the context, explicitly state: "
#             "\"This API/parameter is not available in the provided RTE documentation.\""
#         )
#     elif "parameter" in user_query.lower() or "config" in user_query.lower() or "container" in user_query.lower():
#         clarification = (
#             "Important:\n"
#             "- Extract and list ALL configuration parameters, containers, sub-containers, and references "
#             "from the provided AUTOSAR documentation.\n"
#             "- Do NOT skip, summarize, or combine parameters.\n"
#             "- Preserve exact naming, order, and hierarchy as given in the documents.\n"
#             "- Answer must include the FULL set of parameters present in context, not just a subset.\n"
#             "- Do not invent any parameter, container, or sub-container."
#         )
#     else:
#         clarification = (
#             "Important:\n"
#             "- Only use APIs and flows that appear in the provided AUTOSAR documents.\n"
#             "- Do NOT generate or invent new APIs.\n"
#             "- For RTE questions: Only use APIs explicitly from RTE documents.\n"
#             "- For PduR/COM: Only use APIs from PduR and COM documents.\n"
#             "- For communication stack: Do NOT include CanTp or DCM.\n"
#             "- For diagnostic stack: Include CanTp APIs ONLY if context provides them.\n"
#             "- If API is missing in documents, explicitly say: "
#             "\"This API is not available in the provided AUTOSAR documentation.\""
#         )

#     messages = [{"role": "system", "content": system_prompt}]
#     if context_text:
#         messages.append({
#             "role": "user",
#             "content": f"{clarification}\nContext:\n{context_text}\n\nQuestion: {user_query}"
#         })
#     else:
#         messages.append({
#             "role": "user",
#             "content": f"{clarification}\nQuestion: {user_query}"
#         })
#     return messages

# # ---------------------------
# # General Answer
# # ---------------------------
# def answer_with_context(query: str, context_text: str = "", model: str = "gpt-4o-mini",
#                         max_context_tokens: int = 30000, figure_only: bool = False) -> str:
#     modules = extract_module_from_query(query)
#     context_text = filter_context_by_module(context_text, modules)
#     safe_context = safe_trim_context_by_module(context_text, modules, model=model)

#     messages = build_messages(query, safe_context, figure_only=figure_only)

#     resp = _client.chat.completions.create(
#         model=model,
#         messages=messages,
#         temperature=0,
#         max_tokens=1500
#     )
#     raw_answer = resp.choices[0].message.content.strip()
#     filtered_answer = enforce_doc_only(raw_answer, safe_context)
#     return filtered_answer or "This API/parameter is not available in the provided documentation."

# # ---------------------------
# # Code Generation
# # ---------------------------
# def answer_with_code(question: str, retrieved_chunks: List[Dict], language: str = "C",
#                      model: str = "gpt-4o-mini", max_context_tokens: int = 25000) -> str:
#     context_text = "\n".join([c.get("text", "") for c in retrieved_chunks]) if retrieved_chunks else ""
#     safe_context = safe_trim_context(context_text, model=model, max_tokens=max_context_tokens)
#     prompt_text = (
#         f"Use ONLY the following context to answer the question and generate {language} code.\n"
#         f"Context:\n{safe_context}\n\nQuestion: {question}\n"
#         f"Generate working {language} code only."
#     )

#     messages = build_messages(prompt_text)
#     resp = _client.chat.completions.create(
#         model=model,
#         messages=messages,
#         temperature=0,
#         max_tokens=1000
#     )
#     raw_answer = resp.choices[0].message.content.strip()
#     return enforce_doc_only(raw_answer, safe_context) or "No code generated from provided documentation."

# # ---------------------------
# # Flowchart / Block Diagram
# # ---------------------------
# def answer_with_flowchart(question: str, retrieved_chunks: List[Dict], model: str = "gpt-4o-mini") -> str:
#     context_text = "\n".join([c.get("text", "") for c in retrieved_chunks]) if retrieved_chunks else ""
#     safe_context = safe_trim_context(context_text, model=model)
#     prompt_text = (
#         f"Use the following context to generate a DOT code for a flowchart or block diagram.\n"
#         f"{safe_context}\n\nQuestion: {question}\n"
#         f"Output ONLY valid Graphviz DOT code with nodes and edges, no explanations, no markdown."
#     )

#     messages = build_messages(prompt_text)
#     resp = _client.chat.completions.create(
#         model=model,
#         messages=messages,
#         temperature=0,
#         max_tokens=1000
#     )

#     dot_code = resp.choices[0].message.content.strip()
#     return validate_dot(dot_code, question)

# # ---------------------------
# # Structured JSON Answer
# # ---------------------------
# def answer_with_json(query: str, context_text: str = "", model: str = "gpt-4o-mini",
#                      max_context_tokens: int = 30000) -> dict:
#     modules = extract_module_from_query(query)
#     context_text = filter_context_by_module(context_text, modules)
#     safe_context = safe_trim_context_by_module(context_text, modules, model=model)
#     messages = build_messages(query, safe_context)

#     resp = _client.chat.completions.create(
#         model=model,
#         messages=messages,
#         temperature=0,
#         max_tokens=1500
#     )
#     raw_answer = resp.choices[0].message.content.strip()
#     filtered_answer = enforce_doc_only(raw_answer, safe_context)

#     return {
#         "module": ", ".join(modules),
#         "parameter": query,
#         "value": filtered_answer or "Not found in documentation",
#         "source_context": safe_context[:500]  # first 500 chars for reference
#     }
