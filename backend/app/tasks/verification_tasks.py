import logging

from app.extensions import celery_app
from app.services.verification_service import dedupe_face_embeddings

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.verification_tasks.dedupe_face_embeddings")
def dedupe_face_embeddings_task() -> dict:
    flagged = dedupe_face_embeddings()
    return {"duplicates_flagged": len(flagged), "details": flagged}
