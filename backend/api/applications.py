# ============================================================
# EXACT FILE LOCATION: backend/api/applications.py
# ============================================================
# UPDATED — /portal/apply now fires the full AI pipeline
# as a BackgroundTask after saving the application.
#
# This means:
#   - Candidate gets their confirmation response IMMEDIATELY
#   - AI pipeline runs BEHIND THE SCENES automatically:
#       resume processing → embeddings → matching → interview
# ============================================================

from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from database.database import get_db
from schemas.application import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationStatusResponse,
    CVUploadResponse,
    PublicJobResponse,
)
import services.application_service as app_svc
from utils.file_handler import save_cv_file

router = APIRouter(prefix="/portal", tags=["Candidate Portal"])


# ============================================================
# GET /portal/jobs
# Returns all OPEN jobs for the careers page
# ============================================================
@router.get("/jobs", response_model=List[PublicJobResponse])
def list_open_jobs(db: Session = Depends(get_db)):
    """Fetch all jobs where status = OPEN."""
    return app_svc.get_open_jobs(db)


# ============================================================
# GET /portal/jobs/{job_id}
# Returns full detail for one job
# ============================================================
@router.get("/jobs/{job_id}", response_model=PublicJobResponse)
def get_job_detail(job_id: int, db: Session = Depends(get_db)):
    """Fetch one job by ID for the careers detail page."""
    return app_svc.get_public_job(db, job_id)


# ============================================================
# POST /portal/upload-cv
# Step 1 of application — upload PDF before submitting form
# ============================================================
@router.post("/upload-cv", response_model=CVUploadResponse)
async def upload_cv(file: UploadFile = File(...)):
    """
    Upload a PDF resume.
    Validates: extension, MIME type, size (max 5MB), PDF header.
    Returns resume_path to include in the apply form payload.
    """
    resume_path = await save_cv_file(file)
    return CVUploadResponse(
        message     = "CV uploaded successfully",
        resume_path = resume_path,
        filename    = file.filename or "cv.pdf"
    )


# ============================================================
# POST /portal/apply
# ============================================================
# Step 2 — submit the application form.
#
# FLOW:
#   1. Save Application + CandidateProfile to SQLite  (fast)
#   2. Return confirmation response to candidate       (immediate)
#   3. Fire run_full_ai_pipeline() as BackgroundTask   (automatic)
#        → resume processing
#        → candidate embedding
#        → job embedding
#        → semantic matching
#        → interview question generation  ← auto-triggered
#           inside run_candidate_job_match()
# ============================================================
@router.post("/apply", response_model=ApplicationResponse, status_code=201)
def submit_application(
    data             : ApplicationCreate,
    background_tasks : BackgroundTasks,
    db               : Session = Depends(get_db)
):
    """
    Submit a job application.
    Returns confirmation immediately.
    Triggers full AI pipeline automatically in the background.
    """
    # Save application to SQLite (fast — no AI calls here)
    application = app_svc.submit_application(db, data)

    # ── FIRE AI PIPELINE AS BACKGROUND TASK ──────────────────
    # add_task() returns instantly. The pipeline runs after the
    # HTTP response has been sent to the candidate.
    # run_full_ai_pipeline() creates its own DB session internally.
    background_tasks.add_task(
        app_svc.run_full_ai_pipeline,
        candidate_profile_id = application.candidate_id,   # Phase 2 profile ID
        job_id               = application.job_id
    )

    return application


# ============================================================
# GET /portal/applications/{email}
# Candidate checks all their applications + interview status
# ============================================================
@router.get("/applications/{email}", response_model=List[ApplicationStatusResponse])
def get_my_applications(email: str, db: Session = Depends(get_db)):
    """
    Returns all applications for this email.
    Each entry includes interview_session_id if generated.
    """
    return app_svc.get_applications_by_email(db, email)


# ============================================================
# GET /portal/applications/detail/{application_id}
# Full application detail — used on confirmation page
# ============================================================
@router.get(
    "/applications/detail/{application_id}",
    response_model=ApplicationResponse
)
def get_application_detail(application_id: int, db: Session = Depends(get_db)):
    """Fetch one application by ID including candidate + job info."""
    return app_svc.get_application_by_id(db, application_id)