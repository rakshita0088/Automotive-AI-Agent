# # LLM_Handler.py (with doc-only enforcement)
# import os
# from openai import OpenAI
# import tiktoken
# from typing import List, Dict
# import config
# from graphviz import Digraph
# import re
 
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
 
# # ---------------------------
# # Doc-only Enforcement
# # ---------------------------
# def enforce_doc_only(answer: str, context_text: str) -> str:
#     """
#     Ensure APIs mentioned in the answer exist in the retrieved context.
#     If unknown APIs appear, replace with doc-only warning.
#     """
#     # Extract all potential API-like tokens (e.g., Rte_, PduR_, Com_)
#     api_pattern = r"\b(?:Rte|PduR|Com|CanIf|Dcm|CanTp)_[A-Za-z0-9_]+\b"
#     apis_in_answer = re.findall(api_pattern, answer)
 
#     # Check against context
#     enforced_answer = answer
#     for api in apis_in_answer:
#         if api not in context_text:
#             enforced_answer = enforced_answer.replace(
#                 api,
#                 f"{api}"
#             )
#     return enforced_answer
 
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
#             "- Extract ONLY the exact steps and parameters, containers, sub-containers, and references "
#             "from the sequence diagram or figure context.\n"
#             "- Preserve numbering, API names, and order.\n"
#             "- Do NOT summarize, generalize, or reword.\n"
#             "- Use context strictly as-is."
#         )
#     elif "parameter" in user_query.lower() or "config" in user_query.lower():
#         clarification = (
#             "Important:\n"
#             "- Extract and list ALL configuration parameters, containers, sub-containers, and references "
#             "from the provided AUTOSAR documentation.\n"
#             "- Do NOT skip, summarize, or combine parameters.\n"
#             "- Preserve exact naming, order, and hierarchy as given in the documents.\n"
#             "- Answer must include the FULL set of parameters present in context, not just a subset."
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
#     safe_context = safe_trim_context(context_text, model=model, max_tokens=max_context_tokens)
#     messages = build_messages(query, safe_context, figure_only=figure_only)
 
#     resp = _client.chat.completions.create(
#         model=model,
#         messages=messages,
#         temperature=0,
#         max_tokens=1000
#     )
#     raw_answer = resp.choices[0].message.content.strip()
#     return enforce_doc_only(raw_answer, safe_context)
 
# # ---------------------------
# # Code Generation
# # ---------------------------
# def answer_with_code(question: str, retrieved_chunks: List[Dict], language: str = "C",
#                      model: str = "gpt-4o-mini", max_context_tokens: int = 25000) -> str:
#     context_text = "\n".join([c.get("text", "") for c in retrieved_chunks]) if retrieved_chunks else ""
#     if context_text:
#         safe_context = safe_trim_context(context_text, model=model, max_tokens=max_context_tokens)
#         prompt_text = (
#             f"Use ONLY the following context to answer the question and generate {language} code.\n"
#             f"Context:\n{safe_context}\n\nQuestion: {question}\n"
#             f"Generate working {language} code only."
#         )
#     else:
#         prompt_text = f"Question: {question}\nGenerate working {language} code only."
    
#     messages = build_messages(prompt_text)
#     resp = _client.chat.completions.create(
#         model=model,
#         messages=messages,
#         temperature=0,
#         max_tokens=800
#     )
#     raw_answer = resp.choices[0].message.content.strip()
#     return enforce_doc_only(raw_answer, context_text)
 
# # ---------------------------
# # Flowchart / Block Diagram
# # ---------------------------
# def answer_with_flowchart(question: str, retrieved_chunks: List[Dict], model: str = "gpt-4o-mini") -> str:
#     context_text = "\n".join([c.get("text", "") for c in retrieved_chunks]) if retrieved_chunks else ""
#     prompt_text = (
#         f"Use the following context to generate a DOT code for a flowchart or block diagram.\n"
#         f"{context_text}\n\nQuestion: {question}\n"
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
def enforce_doc_only(answer: str, context_text: str) -> str:
    """
    Ensure the answer contains ONLY containers/sub-containers and parameters
    that exist in the context. Any container not present in the context is removed.
    """

    # Extract all container/sub-container names from the context
    container_pattern = r"\b[A-Z][A-Za-z0-9_-]+\b"
    context_containers = set(re.findall(container_pattern, context_text))

    # Filter answer lines
    filtered_lines = []
    include_line = False
    for line in answer.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Always include description lines
        if stripped.lower().startswith("description:"):
            if include_line:
                filtered_lines.append(stripped)
            continue

        # Check if this line mentions a container/sub-container
        tokens = re.findall(container_pattern, stripped)
        # Only include lines where at least one token exists in context
        if any(token in context_containers for token in tokens):
            filtered_lines.append(stripped)
            include_line = True
        else:
            include_line = False  # skip lines not in context

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

    if figure_only:
        clarification = (
            "Important:\n"
            "- Extract ONLY the exact steps and parameters, containers, sub-containers, and references "
            "from the sequence diagram or figure context.\n"
            "- Preserve numbering, API names, and order.\n"
            "- Do NOT summarize, generalize, or reword.\n"
            "- Use context strictly as-is."
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
    safe_context = safe_trim_context(context_text, model=model, max_tokens=max_context_tokens)
    messages = build_messages(query, safe_context, figure_only=figure_only)

    resp = _client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
        max_tokens=1500
    )
    raw_answer = resp.choices[0].message.content.strip()
    return enforce_doc_only(raw_answer, safe_context)

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
