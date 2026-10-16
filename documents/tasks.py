import logging
import time
from typing import Any

from celery import shared_task

from documents.models import Document

logger = logging.getLogger("django.access")

@shared_task(bind=True, max_retries=3)  # type: ignore[misc]
def process_document_export(
    self: Any,
    document_id: str
) -> dict[str, str]:
    """Simulate background export generation for document ."""
    try:
        doc = Document.objects.get(id=document_id)
        logger.info(
            "document_export_started",
            extra={"document": str(doc.id), "document_title": doc.title}
        )

        #simulate heavy I/O workload
        time.sleep(3)

        return {
            "status": "completed",
            "document_id": str(doc.id),
            "export_url": f"https://storage.cdn.company.internal/exports/{doc.id}.pdf"
        }
    except Document.DoesNotExist:
        logger.warning(
            "document_export_failed_not_found",
            extra={"document_id": document_id}
        )
        return {"status": "failed", "reason": "document not found"}
