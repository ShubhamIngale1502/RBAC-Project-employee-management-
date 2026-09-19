"""
The Self-RAG "reflection" components.

Self-RAG = the model grades its own retrieval and its own answer:
  1. retrieval grader    -> is this chunk relevant to the question?
  2. hallucination grader-> is the verdict grounded in the retrieved chunks?
  3. usefulness grader   -> does the verdict actually answer the screening ask?
  4. query rewriter      -> if retrieval was weak, rewrite and try again.
"""
from typing import List, Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from .llm import get_llm


# --------------------------- structured outputs ---------------------------
class RelevanceGrade(BaseModel):
    binary_score: Literal["yes", "no"] = Field(description="'yes' if the chunk helps answer the question")
    reason: str = Field(default="", description="One short sentence")


class GroundednessGrade(BaseModel):
    binary_score: Literal["yes", "no"] = Field(description="'yes' if every claim is supported by the resume excerpts")
    unsupported_claims: List[str] = Field(default_factory=list)


class UsefulnessGrade(BaseModel):
    binary_score: Literal["yes", "no"]
    missing: str = Field(default="")


class RewrittenQuery(BaseModel):
    query: str


class ScreeningVerdict(BaseModel):
    match_score: int = Field(ge=0, le=100, description="Fit against the job requirements")
    recommendation: Literal["SHORTLIST", "REJECT", "HOLD"]
    summary: str = Field(description="3-4 sentences, recruiter readable")
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list, description="Short quotes from the resume excerpts")


# ------------------------------- graders ----------------------------------
def grade_relevance(question: str, chunk: str) -> RelevanceGrade:
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You grade whether a resume excerpt is relevant to a recruiter's screening "
         "question. Be lenient: keyword or semantic overlap is enough. Answer yes or no."),
        ("human", "Screening question:\n{question}\n\nResume excerpt:\n{chunk}"),
    ])
    chain = prompt | get_llm().with_structured_output(RelevanceGrade)
    return chain.invoke({"question": question, "chunk": chunk})


def grade_groundedness(context: str, generation: str) -> GroundednessGrade:
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You check for hallucination. Given resume excerpts and a screening verdict, "
         "answer 'yes' only if every factual claim in the verdict is supported by the "
         "excerpts. List any unsupported claims."),
        ("human", "Resume excerpts:\n{context}\n\nVerdict:\n{generation}"),
    ])
    chain = prompt | get_llm().with_structured_output(GroundednessGrade)
    return chain.invoke({"context": context, "generation": generation})


def grade_usefulness(question: str, generation: str) -> UsefulnessGrade:
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "Decide whether the verdict answers the recruiter's screening question with a "
         "score, a recommendation and concrete strengths/gaps. Answer yes or no."),
        ("human", "Question:\n{question}\n\nVerdict:\n{generation}"),
    ])
    chain = prompt | get_llm().with_structured_output(UsefulnessGrade)
    return chain.invoke({"question": question, "generation": generation})


def rewrite_query(question: str, job_context: str) -> str:
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "Rewrite the screening question so it retrieves better from a resume vector "
         "store. Use concrete role titles, tools and skill nouns that would literally "
         "appear in a resume. Return the query only."),
        ("human", "Job context:\n{job_context}\n\nCurrent question:\n{question}"),
    ])
    chain = prompt | get_llm(temperature=0.2).with_structured_output(RewrittenQuery)
    return chain.invoke({"question": question, "job_context": job_context}).query


def generate_verdict(job_context: str, context: str, question: str,
                     feedback: str = "") -> ScreeningVerdict:
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are an HR screening assistant. Judge the candidate ONLY from the resume "
         "excerpts provided. Never invent employers, dates or skills. If evidence for a "
         "requirement is missing, list it as a gap. Do not consider name, gender, age, "
         "religion, marital status or photo - score on skills and experience only. "
         "{feedback}"),
        ("human",
         "Job requirements:\n{job_context}\n\nResume excerpts:\n{context}\n\n"
         "Screening ask:\n{question}"),
    ])
    chain = prompt | get_llm().with_structured_output(ScreeningVerdict)
    return chain.invoke({
        "job_context": job_context,
        "context": context,
        "question": question,
        "feedback": feedback,
    })