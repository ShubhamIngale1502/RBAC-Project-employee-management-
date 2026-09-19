"""
Step 1 of the RAG pipeline: resume -> text -> chunks -> embeddings -> DB.

Called from tasks.ingest_resume_task (Celery) whenever a Candidate is created
or the resume file is replaced.
"""
import logging
import re

import docx
import pdfplumber
from django.db import transaction
from django.utils import timezone
from langchain_text_splitters import RecursiveCharacterTextSplitter

from autohire.models import Candidate, ResumeChunk
from .llm import get_embeddings

logger = logging.getLogger(__name__)

SECTION_HINTS = (
    "experience", "employment", "education", "skills", "projects",
    "certification", "summary", "objective", "achievements",
)


def extract_text(file_field) -> str:
    """Supports .pdf, .docx, .txt. Falls back to raw decode for anything else.

    NOTE: these must be .endswith(...) checks, not .startswith(...) - a
    startswith check against a file extension can never match a real
    filename (e.g. "resume.pdf".startswith(".pdf") is always False), which
    silently sends every PDF/DOCX resume down the raw-byte-decode fallback
    below and corrupts the extracted text.
    """
    name = (file_field.name or "").lower()
    file_field.open("rb")
    try:
        if name.endswith(".pdf"):
            with pdfplumber.open(file_field) as pdf:
                pages = [(page.extract_text() or "") for page in pdf.pages]
            return "\n".join(pages)
        if name.endswith(".docx"):
            document = docx.Document(file_field)
            return "\n".join(p.text for p in document.paragraphs)
        return file_field.read().decode("utf-8", errors="ignore")
    finally:
        file_field.close()


def clean_text(raw: str) -> str:
    raw = raw.replace("\x00", " ")
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    return raw.strip()


def guess_section(chunk: str) -> str:
    head = chunk[:120].lower()
    for hint in SECTION_HINTS:
        if hint in head:
            return hint
    return ""


@transaction.atomic
def index_candidate(candidate_id: int) -> int:
    """(Re)build the vector index for one candidate. Returns chunk count."""
    candidate = Candidate.objects.select_for_update().get(pk=candidate_id)

    text = clean_text(extract_text(candidate.resume_file))
    if not text:
        logger.warning("Empty resume text for candidate %s", candidate_id)
        return 0

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = [c for c in splitter.split_text(text) if len(c.strip()) > 40]

    vectors = get_embeddings().embed_documents(chunks)

    candidate.chunks.all().delete()
    ResumeChunk.objects.bulk_create([
        ResumeChunk(
            candidate=candidate,
            chunk_index=i,
            section=guess_section(chunk),
            content=chunk,
            embedding=vector,
        )
        for i, (chunk, vector) in enumerate(zip(chunks, vectors))
    ])

    candidate.resume_text = text
    candidate.is_indexed = True
    candidate.indexed_at = timezone.now()
    candidate.save(update_fields=["resume_text", "is_indexed", "indexed_at", "updated_at"])
    return len(chunks)