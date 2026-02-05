"""
FastAPI application for Legal Tabular Review system.
Provides REST API endpoints for all core operations.
"""

import logging
from typing import Optional, List, Dict, Any
import os
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.models.schema import (
    ProjectCreateRequest, ProjectUpdateRequest, ProjectResponse,
    DocumentUploadRequest, DocumentResponse, ComparisonTableResponse,
    ExtractionUpdateRequest, TaskStatusResponse, EvaluationMetrics,
    EvaluationReportResponse, FieldTemplateCreate, FieldTemplateResponse,
)
from src.storage.repository import DatabaseRepository
from src.services.service_orchestrator import (
    ProjectService, DocumentService, ExtractionService,
    ReviewService, ComparisonService, EvaluationService, TaskService,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Legal Tabular Review API",
    description="System for extracting key fields from legal documents and presenting them in structured tables",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database and services
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./legal_review.db")
repo = DatabaseRepository(DATABASE_URL)

project_service = ProjectService(repo)
document_service = DocumentService(repo)
extraction_service = ExtractionService(repo)
review_service = ReviewService(repo)
comparison_service = ComparisonService(repo)
evaluation_service = EvaluationService(repo)
task_service = TaskService(repo)


# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ==================== PROJECT ENDPOINTS ====================

@app.post("/projects", response_model=ProjectResponse)
async def create_project(request: ProjectCreateRequest):
    """Create a new project."""
    try:
        project = project_service.create_project(
            name=request.name,
            description=request.description,
            field_template_id=request.field_template_id,
        )
        return project
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get project information."""
    try:
        project = project_service.get_project_info(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
    except Exception as e:
        logger.error(f"Error getting project: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/projects")
async def list_projects(skip: int = 0, limit: int = 100):
    """List all projects."""
    try:
        projects = project_service.list_projects(skip, limit)
        return {
            "projects": projects,
            "total": len(projects),
        }
    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, request: ProjectUpdateRequest):
    """Update project."""
    try:
        project = project_service.update_project(
            project_id=project_id,
            name=request.name,
            description=request.description,
            field_template_id=request.field_template_id,
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
    except Exception as e:
        logger.error(f"Error updating project: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== DOCUMENT ENDPOINTS ====================

@app.post("/projects/{project_id}/documents/upload", response_model=DocumentResponse)
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
):
    """Upload document to project."""
    try:
        # Save file temporarily
        file_path = f"/tmp/{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # Ingest document
        document = document_service.ingest_document(
            project_id=project_id,
            filename=file.filename,
            file_path=file_path,
        )
        return document
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/projects/{project_id}/documents")
async def list_project_documents(project_id: str):
    """List documents in project."""
    try:
        documents = document_service.list_project_documents(project_id)
        return {
            "documents": documents,
            "total": len(documents),
        }
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== FIELD TEMPLATE ENDPOINTS ====================

@app.post("/field-templates", response_model=FieldTemplateResponse)
async def create_field_template(request: FieldTemplateCreate):
    """Create field template."""
    try:
        fields = [field.dict() for field in request.fields]
        template = repo.create_field_template(
            name=request.name,
            description=request.description,
            fields=fields,
        )
        return {
            'id': template.id,
            'name': template.name,
            'description': template.description,
            'version': template.version,
            'fields': template.fields,
            'created_at': template.created_at,
            'updated_at': template.updated_at,
            'is_active': template.is_active,
        }
    except Exception as e:
        logger.error(f"Error creating field template: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/field-templates")
async def list_field_templates():
    """List field templates."""
    try:
        templates = repo.list_field_templates()
        return {
            "templates": [
                {
                    'id': t.id,
                    'name': t.name,
                    'version': t.version,
                    'fields_count': len(t.fields),
                    'created_at': t.created_at,
                }
                for t in templates
            ],
            "total": len(templates),
        }
    except Exception as e:
        logger.error(f"Error listing field templates: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== EXTRACTION ENDPOINTS ====================

@app.post("/projects/{project_id}/extract")
async def extract_fields(
    project_id: str,
    document_id: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
):
    """Extract fields from documents."""
    try:
        # Get project and template
        project = repo.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if not project.field_template_id:
            raise HTTPException(status_code=400, detail="Project has no field template")

        template = repo.get_field_template(project.field_template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Field template not found")

        field_definitions = template.fields

        # Create task
        task = task_service.create_task("extract", project_id)

        # Run extraction in background
        if background_tasks:
            background_tasks.add_task(
                _run_extraction,
                project_id,
                document_id,
                field_definitions,
                task['task_id'],
            )

        return {
            "task_id": task['task_id'],
            "status": "started",
            "message": "Extraction started in background",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting fields: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


def _run_extraction(
    project_id: str,
    document_id: Optional[str],
    field_definitions: List[Dict[str, Any]],
    task_id: str,
):
    """Background task for field extraction."""
    try:
        task_service.repo.update_task(task_id, status='PROCESSING')

        if document_id:
            result = extraction_service.extract_fields_for_document(
                project_id, document_id, field_definitions
            )
        else:
            result = extraction_service.extract_all_documents(project_id, field_definitions)

        task_service.repo.update_task(
            task_id,
            status='COMPLETED',
            result=result,
        )
    except Exception as e:
        logger.error(f"Error in extraction background task: {str(e)}")
        task_service.repo.update_task(
            task_id,
            status='FAILED',
            error_message=str(e),
        )


# ==================== REVIEW ENDPOINTS ====================

@app.put("/extractions/{extraction_id}/review")
async def review_extraction(
    extraction_id: str,
    request: ExtractionUpdateRequest,
):
    """Review and update extraction."""
    try:
        result = review_service.update_extraction_review(
            extraction_id=extraction_id,
            status=request.status.value,
            manual_value=request.manual_value,
            reviewer_notes=request.reviewer_notes,
        )
        return result
    except Exception as e:
        logger.error(f"Error reviewing extraction: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/projects/{project_id}/reviews/pending")
async def get_pending_reviews(project_id: str):
    """Get pending reviews for project."""
    try:
        reviews = review_service.get_pending_reviews(project_id)
        return {
            "reviews": reviews,
            "total": len(reviews),
        }
    except Exception as e:
        logger.error(f"Error getting pending reviews: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== COMPARISON TABLE ENDPOINTS ====================

@app.get("/projects/{project_id}/table")
async def get_comparison_table(project_id: str):
    """Get comparison table for project."""
    try:
        table = comparison_service.generate_comparison_table(project_id)
        return table
    except Exception as e:
        logger.error(f"Error generating comparison table: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/projects/{project_id}/table/export-csv")
async def export_table_to_csv(project_id: str):
    """Export comparison table to CSV."""
    try:
        import csv
        import io

        table = comparison_service.generate_comparison_table(project_id)

        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Headers
        headers = ["Field Name", "Field Type"]
        headers.extend([doc['filename'] for doc in table.get('documents', [])])
        writer.writerow(headers)

        # Rows
        for row in table.get('rows', []):
            row_data = [row['field_name'], row['field_type']]
            for doc in table.get('documents', []):
                doc_id = doc['id']
                result = row['document_results'].get(doc_id, {})
                value = result.get('extracted_value', 'N/A')
                row_data.append(value)
            writer.writerow(row_data)

        csv_content = output.getvalue()
        return {
            "format": "csv",
            "content": csv_content,
            "filename": f"legal_review_{project_id}.csv",
        }

    except Exception as e:
        logger.error(f"Error exporting table: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== EVALUATION ENDPOINTS ====================

@app.post("/projects/{project_id}/evaluate")
async def evaluate_project(
    project_id: str,
    evaluation_data: Dict[str, Any],
    background_tasks: BackgroundTasks = None,
):
    """Evaluate extraction quality."""
    try:
        # Create task
        task = task_service.create_task("evaluate", project_id)

        # Run evaluation in background
        if background_tasks:
            background_tasks.add_task(
                _run_evaluation,
                project_id,
                evaluation_data,
                task['task_id'],
            )

        return {
            "task_id": task['task_id'],
            "status": "started",
            "message": "Evaluation started in background",
        }

    except Exception as e:
        logger.error(f"Error starting evaluation: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


def _run_evaluation(
    project_id: str,
    evaluation_data: Dict[str, Any],
    task_id: str,
):
    """Background task for evaluation."""
    try:
        task_service.repo.update_task(task_id, status='PROCESSING')

        for item in evaluation_data.get('items', []):
            evaluation_service.evaluate_extraction(
                project_id=project_id,
                document_id=item.get('document_id'),
                field_name=item.get('field_name'),
                human_value=item.get('human_value'),
            )

        report = evaluation_service.generate_evaluation_report(project_id)
        task_service.repo.update_task(
            task_id,
            status='COMPLETED',
            result=report,
        )

    except Exception as e:
        logger.error(f"Error in evaluation background task: {str(e)}")
        task_service.repo.update_task(
            task_id,
            status='FAILED',
            error_message=str(e),
        )


@app.get("/projects/{project_id}/evaluation-report")
async def get_evaluation_report(project_id: str):
    """Get evaluation report for project."""
    try:
        report = evaluation_service.generate_evaluation_report(project_id)
        return report
    except Exception as e:
        logger.error(f"Error getting evaluation report: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== TASK ENDPOINTS ====================

@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get async task status."""
    try:
        status = task_service.get_task_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail="Task not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== ERROR HANDLERS ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
