"""
Celery tasks for background processing.
"""
import os
from typing import Dict, Any
from app.workers.celery_app import celery_app
from app.rag.ingestion.ingest import ingest_pdf
from app.core.logging import setup_logger

logger = setup_logger("INFO")

# In-memory job results store
job_results: Dict[str, Dict[str, Any]] = {}


@celery_app.task(bind=True, name="workers.tasks.ingest_pdf_task")
def ingest_pdf_task(
    self,
    file_path: str,
    source: str,
    chunk_size: int = 200,
    overlap: int = 50,
    exists_policy: str = "skip"
) -> Dict[str, Any]:
    """
    Background task to ingest a PDF file with enhanced metadata tracking.
    
    Args:
        file_path: Path to the PDF file
        source: Source identifier for the document
        chunk_size: Size of text chunks (default: 200)
        overlap: Overlap between chunks (default: 50)
        exists_policy: Policy for duplicates (skip/overwrite/version_as_new)
    
    Returns:
        Dictionary with job_id and ingestion summary including document_id
    """
    job_id = self.request.id
    
    try:
        logger.info(
            f"Starting PDF ingestion task {job_id} for {file_path} "
            f"(policy={exists_policy}, chunk_size={chunk_size}, overlap={overlap})"
        )
        
        # Update status to processing
        job_results[job_id] = {
            "status": "processing",
            "job_id": job_id,
            "file_path": file_path,
            "source": source,
            "chunk_size": chunk_size,
            "overlap": overlap,
            "exists_policy": exists_policy
        }
        
        # Call the enhanced ingest_pdf function
        result = ingest_pdf(
            file_path=file_path,
            source=source,
            chunk_size=chunk_size,
            overlap=overlap,
            exists_policy=exists_policy
        )
        
        # Handle different result statuses
        if result.get("status") == "skipped":
            job_results[job_id] = {
                "status": "skipped",
                "job_id": job_id,
                "file_path": file_path,
                "source": source,
                "document_id": result.get("document_id"),
                "reason": result.get("reason"),
                "pages_processed": result.get("pages", 0),
                "chunks_created": result.get("chunks", 0),
                "processing_time_ms": result.get("processing_time_ms", 0),
                "message": "Document skipped - duplicate already exists"
            }
            logger.info(f"PDF ingestion task {job_id} skipped (duplicate)")
        
        elif result.get("status") == "success":
            job_results[job_id] = {
                "status": "completed",
                "job_id": job_id,
                "file_path": file_path,
                "source": source,
                "document_id": result.get("document_id"),
                "pages_processed": result.get("pages", 0),
                "chunks_created": result.get("chunks", 0),
                "token_estimate": result.get("token_estimate", 0),
                "processing_time_ms": result.get("processing_time_ms", 0),
                "checksum": result.get("checksum"),
                "version": result.get("version", 1),
                "message": "PDF ingested successfully"
            }
            logger.info(f"PDF ingestion task {job_id} completed successfully")
        
        else:
            # Failed status
            job_results[job_id] = {
                "status": "failed",
                "job_id": job_id,
                "file_path": file_path,
                "source": source,
                "error": result.get("message", "Unknown error"),
                "processing_time_ms": result.get("processing_time_ms", 0)
            }
            logger.error(f"PDF ingestion task {job_id} failed: {result.get('message')}")
        
        # Clean up uploaded file after processing
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up uploaded file: {file_path}")
        
        return job_results[job_id]
        
    except Exception as e:
        error_msg = f"PDF ingestion failed: {str(e)}"
        logger.error(f"Task {job_id} failed: {error_msg}")
        
        job_results[job_id] = {
            "status": "failed",
            "job_id": job_id,
            "file_path": file_path,
            "source": source,
            "error": error_msg
        }
        
        # Clean up file on error too
        if os.path.exists(file_path):
            os.remove(file_path)
        
        raise


def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Get the status of a job.
    
    Args:
        job_id: The job ID to check
    
    Returns:
        Dictionary with job status and details
    """
    if job_id in job_results:
        return job_results[job_id]
    
    # Check if task exists in Celery
    from celery.result import AsyncResult
    task = AsyncResult(job_id, app=celery_app)
    
    if task.state == "PENDING":
        return {
            "status": "pending",
            "job_id": job_id,
            "message": "Task is waiting to be processed"
        }
    elif task.state == "STARTED":
        return {
            "status": "processing",
            "job_id": job_id,
            "message": "Task is currently being processed"
        }
    elif task.state == "SUCCESS":
        return task.result
    elif task.state == "FAILURE":
        return {
            "status": "failed",
            "job_id": job_id,
            "error": str(task.info)
        }
    else:
        return {
            "status": "unknown",
            "job_id": job_id,
            "message": f"Task state: {task.state}"
        }
