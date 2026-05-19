# ============================================================
# utils/file_handler.py  —  NEW in Phase 2
# Handles CV/resume PDF upload validation and secure storage.
#
# Workflow:
#   1. Receive UploadFile from FastAPI endpoint
#   2. Validate it is a PDF (by extension + MIME type)
#   3. Generate a unique filename to prevent collisions
#   4. Save file to /uploads directory
#   5. Return the stored file path
# ============================================================

import os
import uuid
import logging
from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)

# Directory where uploaded CVs are saved (relative to backend root)
UPLOAD_DIR = "uploads"

# Maximum allowed file size: 5 MB
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024

# Allowed MIME types for CV upload
ALLOWED_MIME_TYPES = {"application/pdf"}
ALLOWED_EXTENSIONS = {".pdf"}


# ============================================================
# Ensure the uploads directory exists at startup
# ============================================================
def ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    logger.info(f"Upload directory ready: {UPLOAD_DIR}/")


# ============================================================
# Validate and save an uploaded CV file
# Returns the relative file path on success
# Raises HTTPException on validation failure
# ============================================================
async def save_cv_file(file: UploadFile) -> str:
    # Validate file extension
    _, ext = os.path.splitext(file.filename or "")
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed. Please upload a .pdf file."
        )

    # Validate MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Only PDF is accepted."
        )

    # Read file content and check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum allowed size is 5 MB."
        )

    # Check PDF magic bytes (first 4 bytes should be %PDF)
    if not content.startswith(b"%PDF"):
        raise HTTPException(
            status_code=400,
            detail="File does not appear to be a valid PDF."
        )

    # Generate a unique filename to prevent overwriting existing files
    # Format: <uuid>_<original_sanitized_name>.pdf
    safe_original = "".join(
        c for c in (file.filename or "cv") if c.isalnum() or c in ("_", "-", ".")
    )
    unique_filename = f"{uuid.uuid4().hex}_{safe_original}"

    # Build full save path
    ensure_upload_dir()
    save_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Write file to disk
    with open(save_path, "wb") as f:
        f.write(content)

    logger.info(f"CV saved: {save_path} ({len(content)} bytes)")

    # Return relative path (stored in DB, served via static files)
    return save_path