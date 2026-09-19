"""Vector retrieval scoped to a single candidate's resume."""
from pgvector.django import CosineDistance

from autohire.models import ResumeChunk
from .llm import get_embeddings


def retrieve_chunks(candidate_id: int, query: str, k: int = 5, max_distance: float = 0.60):
    """Return [{'id','section','content','distance'}] ordered by similarity."""
    vector = get_embeddings().embed_query(query)
    qs = (
        ResumeChunk.objects
        .filter(candidate_id=candidate_id)
        .annotate(distance=CosineDistance("embedding", vector))
        .order_by("distance")[:k]
    )
    return [
        {
            "id": chunk.id,
            "section": chunk.section,
            "content": chunk.content,
            "distance": float(chunk.distance),
        }
        for chunk in qs
        if float(chunk.distance) <= max_distance
    ]


def keyword_fallback(candidate_id: int, query: str, k: int = 5):
    """Corrective-RAG style fallback when vector recall is empty.

    We deliberately do NOT hit the public web for resumes (PII), so the
    'external search' branch of CRAG becomes a lexical sweep over the whole
    resume text instead.
    """
    terms = [t for t in query.replace(",", " ").split() if len(t) > 3][:6]
    qs = ResumeChunk.objects.filter(candidate_id=candidate_id)
    for term in terms:
        hits = list(qs.filter(content__icontains=term)[:k])
        if hits:
            return [
                {"id": c.id, "section": c.section, "content": c.content, "distance": 1.0}
                for c in hits
            ]
    return []