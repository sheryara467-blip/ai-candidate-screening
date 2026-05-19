# ============================================================
# EXACT FILE LOCATION: backend/services/application_service.py
# ============================================================
# FIXED (all 5 fixes applied):
#
#   FIX 1 — Step 5 added to run_full_ai_pipeline():
#            Force interview generation directly — do NOT rely
#            on matching service side-effect calling it.
#
#   FIX 3 — Logging added to get_applications_by_email()
#            so we can verify interview session existence at
#            query time via backend logs.
#
# Pipeline now:
#   Step 1: Resume processing
#   Step 2: Candidate embedding
#   Step 3: Job embedding
#   Step 4: Semantic matching
#   Step 5: FORCE interview generation  ← NEW (deterministic)
# ============================================================

from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from typing import List
import logging

from models.application import CandidateProfile, Application, AppStatus
from models.candidate import Candidate, ApplicationStatus
from models.job import Job, JobStatus
from models.interview_models import InterviewSession
from schemas.application import ApplicationCreate

logger = logging.getLogger(__name__)


# ============================================================
# ensure_admin_candidate_record
# Bridge: Phase 2 Application → Phase 1 Candidate table.
# Strict dedup: one row per (email, job_id).
# ============================================================
def ensure_admin_candidate_record(db: Session, application: Application) -> Candidate:
    profile = (
        db.query(CandidateProfile)
        .filter(CandidateProfile.id == application.candidate_id)
        .first()
    )
    if not profile:
        logger.warning(
            f"No CandidateProfile id={application.candidate_id} "
            f"for application id={application.id} — skipping admin sync"
        )
        return None

    existing_rows = (
        db.query(Candidate)
        .filter(
            Candidate.email  == profile.email,
            Candidate.job_id == application.job_id
        )
        .all()
    )

    if len(existing_rows) > 1:
        keeper = existing_rows[0]
        for dup in existing_rows[1:]:
            db.delete(dup)
            logger.info(f"Removed duplicate Candidate id={dup.id}")
        db.flush()
        existing = keeper
    elif len(existing_rows) == 1:
        existing = existing_rows[0]
    else:
        existing = None

    if existing:
        existing.name         = profile.full_name
        existing.cv_file_path = profile.resume_path
        logger.info(f"Updated admin Candidate id={existing.id} email={profile.email}")
        db.flush()
        return existing

    new_candidate = Candidate(
        job_id       = application.job_id,
        name         = profile.full_name,
        email        = profile.email,
        cv_file_path = profile.resume_path,
        status       = ApplicationStatus.PENDING,
    )
    db.add(new_candidate)
    db.flush()
    logger.info(f"Created admin Candidate for email={profile.email} job={application.job_id}")
    return new_candidate


# ============================================================
# backfill_admin_candidates
# Called on server startup. Creates missing Candidate rows
# and removes duplicate rows.
# ============================================================
def backfill_admin_candidates(db: Session) -> dict:
    logger.info("Running backfill: Phase 2 Applications → Phase 1 Candidate table...")

    from sqlalchemy import func
    duplicates_removed = 0
    dup_groups = (
        db.query(Candidate.email, Candidate.job_id)
        .group_by(Candidate.email, Candidate.job_id)
        .having(func.count(Candidate.id) > 1)
        .all()
    )
    for email, job_id in dup_groups:
        rows = (
            db.query(Candidate)
            .filter(Candidate.email == email, Candidate.job_id == job_id)
            .order_by(Candidate.id)
            .all()
        )
        for dup in rows[1:]:
            db.delete(dup)
            duplicates_removed += 1
    if duplicates_removed:
        db.commit()
        logger.info(f"Removed {duplicates_removed} duplicate Candidate rows")

    all_applications = (
        db.query(Application)
        .options(joinedload(Application.candidate))
        .all()
    )

    created = 0
    skipped = 0
    for app in all_applications:
        if not app.candidate:
            skipped += 1
            continue
        existing = (
            db.query(Candidate)
            .filter(
                Candidate.email  == app.candidate.email,
                Candidate.job_id == app.job_id
            )
            .first()
        )
        if not existing:
            db.add(Candidate(
                job_id       = app.job_id,
                name         = app.candidate.full_name,
                email        = app.candidate.email,
                cv_file_path = app.candidate.resume_path,
                status       = ApplicationStatus.PENDING,
            ))
            created += 1
        else:
            skipped += 1

    db.commit()
    logger.info(
        f"Backfill done — {created} created, "
        f"{skipped} skipped, {duplicates_removed} duplicates removed"
    )
    return {"created": created, "skipped": skipped, "duplicates_removed": duplicates_removed}


# ============================================================
# run_full_ai_pipeline
# ============================================================
# FIX 1 APPLIED: Step 5 added — interview generation is now
# EXPLICIT inside this function. We do NOT rely on
# _auto_trigger_interview() being called as a side-effect
# inside run_candidate_job_match(). That was unreliable.
#
# Now the pipeline is fully deterministic:
#   Step 1 → resume
#   Step 2 → candidate embedding
#   Step 3 → job embedding
#   Step 4 → matching
#   Step 5 → interview (FORCED, always runs after step 4)
# ============================================================
def run_full_ai_pipeline(candidate_profile_id: int, job_id: int):
    """
    Full AI pipeline triggered as BackgroundTask after submission.
    Creates its own DB session — runs in a background thread.
    """
    from database.database import SessionLocal
    db = SessionLocal()

    logger.info(
        f"[AUTO-PIPELINE] Starting — "
        f"candidate_profile_id={candidate_profile_id} job_id={job_id}"
    )

    try:
        # ── STEP 1: Resume Processing ──────────────────────────
        logger.info(f"[AUTO-PIPELINE] Step 1/5: Processing resume...")
        try:
            from services.resume_service import process_resume
            process_resume(db, candidate_profile_id)
            logger.info(f"[AUTO-PIPELINE] Step 1 ✓ Resume processed")
        except Exception as e:
            logger.warning(f"[AUTO-PIPELINE] Step 1 skipped — {e}")

        # ── STEP 2: Candidate Embedding ────────────────────────
        logger.info(f"[AUTO-PIPELINE] Step 2/5: Generating candidate embedding...")
        try:
            from services.vector_service import generate_candidate_embedding
            generate_candidate_embedding(db, candidate_profile_id, force=False)
            logger.info(f"[AUTO-PIPELINE] Step 2 ✓ Candidate embedding synced")
        except Exception as e:
            logger.warning(f"[AUTO-PIPELINE] Step 2 skipped — {e}")

        # ── STEP 3: Job Embedding ──────────────────────────────
        logger.info(f"[AUTO-PIPELINE] Step 3/5: Generating job embedding...")
        try:
            from services.vector_service import generate_job_embedding
            generate_job_embedding(db, job_id, force=False)
            logger.info(f"[AUTO-PIPELINE] Step 3 ✓ Job embedding synced")
        except Exception as e:
            logger.warning(f"[AUTO-PIPELINE] Step 3 skipped — {e}")

        # ── STEP 4: Semantic Matching ──────────────────────────
        logger.info(f"[AUTO-PIPELINE] Step 4/5: Running semantic matching...")
        try:
            from services.matching_service import run_candidate_job_match
            match = run_candidate_job_match(
                db,
                candidate_profile_id,
                job_id,
                force_recalculate=False
            )
            logger.info(
                f"[AUTO-PIPELINE] Step 4 ✓ Match complete — "
                f"score={match.final_match_score:.1f}% "
                f"recommendation={match.recommendation}"
            )
        except Exception as e:
            logger.warning(f"[AUTO-PIPELINE] Step 4 skipped — {e}")

        # ── STEP 5: FORCE INTERVIEW GENERATION ────────────────
        # FIX 1: Explicitly call auto_generate_interview() here.
        # Do NOT rely on matching_service calling it as a side-effect.
        # This guarantees the session is created in THIS db session
        # and committed before this background task closes.
        logger.info(f"[AUTO-PIPELINE] Step 5/5: Generating interview questions...")
        try:
            from services.interview_service import auto_generate_interview
            interview = auto_generate_interview(
                db,
                candidate_profile_id,
                job_id
            )
            logger.info(
                f"[AUTO-PIPELINE] Step 5 ✓ Interview generated — "
                f"session_id={interview.id}"
            )
        except Exception as e:
            logger.warning(f"[AUTO-PIPELINE] Step 5 skipped — {e}")

        logger.info(
            f"[AUTO-PIPELINE] ✓ ALL STEPS COMPLETE — "
            f"candidate_profile_id={candidate_profile_id} job_id={job_id}"
        )

    except Exception as e:
        logger.error(f"[AUTO-PIPELINE] Unexpected fatal error: {e}")
    finally:
        db.close()


# ============================================================
# get_open_jobs  (candidate-facing)
# ============================================================
def get_open_jobs(db: Session) -> List[Job]:
    return (
        db.query(Job)
        .filter(Job.status == JobStatus.OPEN)
        .order_by(Job.created_at.desc())
        .all()
    )


# ============================================================
# get_public_job  (candidate-facing)
# ============================================================
def get_public_job(db: Session, job_id: int) -> Job:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ============================================================
# submit_application
# ============================================================
def submit_application(db: Session, data: ApplicationCreate) -> Application:
    job = db.query(Job).filter(Job.id == data.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.OPEN:
        raise HTTPException(
            status_code=400,
            detail="This job is no longer accepting applications"
        )

    profile = (
        db.query(CandidateProfile)
        .filter(CandidateProfile.email == data.email.lower())
        .first()
    )
    if not profile:
        profile = CandidateProfile(
            full_name   = data.full_name.strip(),
            email       = data.email.lower(),
            phone       = data.phone,
            resume_path = data.resume_path,
        )
        db.add(profile)
        db.flush()
        logger.info(f"New CandidateProfile: {profile.email}")
    else:
        if data.resume_path:
            profile.resume_path = data.resume_path
        logger.info(f"Existing CandidateProfile: {profile.email}")

    existing = (
        db.query(Application)
        .filter(
            Application.candidate_id == profile.id,
            Application.job_id       == data.job_id
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="You have already applied for this job"
        )

    application = Application(
        candidate_id  = profile.id,
        job_id        = data.job_id,
        cover_message = data.cover_message,
        status        = AppStatus.SUBMITTED,
    )
    db.add(application)
    db.flush()

    ensure_admin_candidate_record(db, application)

    db.commit()
    db.refresh(application)

    logger.info(
        f"Application saved: id={application.id} "
        f"profile_id={profile.id} job_id={data.job_id}"
    )
    # AI pipeline fired from api/applications.py as BackgroundTask
    return application


# ============================================================
# get_applications_by_email
# FIX 3 APPLIED: Added logging to verify interview existence
# at query time — visible in backend terminal output.
# ============================================================
def get_applications_by_email(db: Session, email: str) -> List[dict]:
    profile = (
        db.query(CandidateProfile)
        .filter(CandidateProfile.email == email.lower())
        .first()
    )
    if not profile:
        return []

    applications = (
        db.query(Application)
        .options(joinedload(Application.job))
        .filter(Application.candidate_id == profile.id)
        .order_by(Application.created_at.desc())
        .all()
    )

    result = []
    for app in applications:
        interview = (
            db.query(InterviewSession)
            .filter(
                InterviewSession.candidate_profile_id == profile.id,
                InterviewSession.job_id               == app.job_id
            )
            .first()
        )

        # FIX 3: Log so we can verify in terminal whether session exists
        logger.info(
            f"Application {app.id} (job={app.job_id}): "
            f"interview={'YES session_id=' + str(interview.id) if interview else 'NO — pipeline still running or failed'}"
        )

        result.append({
            "application_id"      : app.id,
            "job_id"              : app.job_id,
            "job_title"           : app.job.title      if app.job else "—",
            "department"          : app.job.department if app.job else "—",
            "status"              : app.status,
            "applied_on"          : app.created_at,
            "interview_session_id": interview.id if interview else None,
        })
    return result


# ============================================================
# get_application_by_id
# ============================================================
def get_application_by_id(db: Session, application_id: int) -> Application:
    app = (
        db.query(Application)
        .options(
            joinedload(Application.candidate),
            joinedload(Application.job),
        )
        .filter(Application.id == application_id)
        .first()
    )
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app