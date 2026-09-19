"""
Self-RAG screening graph (LangGraph).

           +-------------+
           |  retrieve   |<-------------------+
           +------+------+                    |
                  |                           |
        +---------v---------+                 |
        |  grade_documents  |                 |
        +---------+---------+                 |
                  |                           |
      relevant?   |  no / too few             |
        +---------+--------+          +-------+--------+
        |                  +--------->|  rewrite_query |
        v                             +----------------+
   +----+-----+                                ^
   | generate |                                |
   +----+-----+                                |
        |                                      |
  +-----v---------------+   not grounded       |
  | grade_hallucination +----------------------+ (regenerate)
  +-----+---------------+
        | grounded
  +-----v-----------+   not useful
  | grade_usefulness+---------------------------> rewrite_query
  +-----+-----------+
        | useful
       END
"""
import time
from typing import Any, Callable, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from . import graders
from .retriever import keyword_fallback, retrieve_chunks

MAX_RETRIEVAL_LOOPS = 2
MAX_GENERATION_LOOPS = 2
MIN_RELEVANT_CHUNKS = 2


class ScreeningState(TypedDict, total=False):
    candidate_id: int
    job_context: str
    question: str
    original_question: str
    documents: List[Dict[str, Any]]
    generation: Optional[Dict[str, Any]]
    feedback: str
    retrieval_loops: int
    generation_loops: int
    used_fallback: bool
    recorder: Callable[[str, dict, int], None]


def _record(state, node, detail, started):
    recorder = state.get("recorder")
    if recorder:
        recorder(node, detail, int((time.time() - started) * 1000))


# ------------------------------- nodes ------------------------------------
def retrieve(state: ScreeningState) -> ScreeningState:
    started = time.time()
    docs = retrieve_chunks(state["candidate_id"], state["question"], k=6)
    used_fallback = False
    if not docs:  # corrective step: lexical sweep before giving up
        docs = keyword_fallback(state["candidate_id"], state["question"])
        used_fallback = bool(docs)
    _record(state, "retrieve", {
        "query": state["question"],
        "hits": len(docs),
        "fallback": used_fallback,
        "chunk_ids": [d["id"] for d in docs],
    }, started)
    return {**state, "documents": docs, "used_fallback": used_fallback}


def grade_documents(state: ScreeningState) -> ScreeningState:
    started = time.time()
    kept, log = [], []
    for doc in state.get("documents", []):
        grade = graders.grade_relevance(state["question"], doc["content"])
        log.append({"chunk_id": doc["id"], "score": grade.binary_score, "reason": grade.reason})
        if grade.binary_score == "yes":
            kept.append(doc)
    _record(state, "grade_documents", {"kept": len(kept), "grades": log}, started)
    return {**state, "documents": kept}


def rewrite_query(state: ScreeningState) -> ScreeningState:
    started = time.time()
    new_q = graders.rewrite_query(state["question"], state["job_context"])
    loops = state.get("retrieval_loops", 0) + 1
    _record(state, "rewrite_query", {"from": state["question"], "to": new_q, "loop": loops}, started)
    return {**state, "question": new_q, "retrieval_loops": loops}


def generate(state: ScreeningState) -> ScreeningState:
    started = time.time()
    context = "\n\n---\n\n".join(
        f"[chunk {d['id']}{(' | ' + d['section']) if d['section'] else ''}]\n{d['content']}"
        for d in state.get("documents", [])
    ) or "NO RELEVANT RESUME CONTENT WAS RETRIEVED."
    verdict = graders.generate_verdict(
        job_context=state["job_context"],
        context=context,
        question=state.get("original_question", state["question"]),
        feedback=state.get("feedback", ""),
    )
    payload = verdict.model_dump()
    _record(state, "generate", {
        "match_score": payload["match_score"],
        "recommendation": payload["recommendation"],
        "chunks_used": [d["id"] for d in state.get("documents", [])],
    }, started)
    return {**state, "generation": payload, "_context": context}


def grade_hallucination(state: ScreeningState) -> ScreeningState:
    started = time.time()
    grade = graders.grade_groundedness(
        state.get("_context", ""), str(state.get("generation")),
    )
    feedback = ""
    if grade.binary_score == "no":
        feedback = (
            "Your previous verdict contained claims not supported by the excerpts: "
            + "; ".join(grade.unsupported_claims)
            + ". Rewrite it using only supported facts."
        )
    _record(state, "grade_hallucination", {
        "grounded": grade.binary_score,
        "unsupported": grade.unsupported_claims,
    }, started)
    return {
        **state,
        "feedback": feedback,
        "_grounded": grade.binary_score == "yes",
        "generation_loops": state.get("generation_loops", 0) + (0 if grade.binary_score == "yes" else 1),
    }


def grade_usefulness(state: ScreeningState) -> ScreeningState:
    started = time.time()
    grade = graders.grade_usefulness(
        state.get("original_question", state["question"]), str(state.get("generation")),
    )
    _record(state, "grade_usefulness", {"useful": grade.binary_score, "missing": grade.missing}, started)
    return {**state, "_useful": grade.binary_score == "yes"}


# ------------------------------- edges ------------------------------------
def decide_after_grading(state: ScreeningState) -> str:
    enough = len(state.get("documents", [])) >= MIN_RELEVANT_CHUNKS
    exhausted = state.get("retrieval_loops", 0) >= MAX_RETRIEVAL_LOOPS
    if enough or exhausted:
        return "generate"
    return "rewrite_query"


def decide_after_hallucination(state: ScreeningState) -> str:
    if state.get("_grounded"):
        return "grade_usefulness"
    if state.get("generation_loops", 0) >= MAX_GENERATION_LOOPS:
        return "grade_usefulness" 
    return "generate"


def decide_after_usefulness(state: ScreeningState) -> str:
    if state.get("_useful") or state.get("retrieval_loops", 0) >= MAX_RETRIEVAL_LOOPS:
        return END
    return "rewrite_query"


def build_screening_graph():
    graph = StateGraph(ScreeningState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("grade_documents", grade_documents)
    graph.add_node("rewrite_query", rewrite_query)
    graph.add_node("generate", generate)
    graph.add_node("grade_hallucination", grade_hallucination)
    graph.add_node("grade_usefulness", grade_usefulness)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "grade_documents")
    graph.add_conditional_edges("grade_documents", decide_after_grading,
                                {"generate": "generate", "rewrite_query": "rewrite_query"})
    graph.add_edge("rewrite_query", "retrieve")
    graph.add_edge("generate", "grade_hallucination")
    graph.add_conditional_edges("grade_hallucination", decide_after_hallucination,
                                {"generate": "generate", "grade_usefulness": "grade_usefulness"})
    graph.add_conditional_edges("grade_usefulness", decide_after_usefulness,
                                {"rewrite_query": "rewrite_query", END: END})
    return graph.compile()


SCREENING_GRAPH = build_screening_graph()