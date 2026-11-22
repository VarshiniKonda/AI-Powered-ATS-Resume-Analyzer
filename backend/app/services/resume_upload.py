"""Securely read and parse uploaded resume files without retaining the originals."""

import re
from pathlib import PurePath

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.services.resume_parser import (
    DocumentTooLargeError,
    extract_document_text,
)


async def extract_uploaded_resume(file: UploadFile) -> tuple[str, str]:
    """Return a safe display filename and extracted text, then close the upload."""
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    try:
        if file.size is not None and file.size > max_bytes:
            raise DocumentTooLargeError("Resume exceeds the upload size limit.")
        content = await file.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise DocumentTooLargeError("Resume exceeds the upload size limit.")

        filename = re.sub(
            r"[^A-Za-z0-9._ -]",
            "_",
            PurePath(file.filename or "resume").name,
        )[:255]
        text = await run_in_threadpool(
            extract_document_text,
            filename,
            content,
            file.content_type,
        )
        return filename, text
    finally:
        await file.close()
