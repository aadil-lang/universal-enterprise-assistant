"""
Document validation service for enterprise policy files.
Validates file extensions, magic bytes, structure, and integrity before processing.
"""

import hashlib
import io
import zipfile
from typing import Set, Tuple


class DocumentValidationError(Exception):
    """Base exception for document validation failures."""
    pass


class UnsupportedFormatError(DocumentValidationError):
    """Raised when file extension or MIME type is not supported."""
    pass


class EmptyDocumentError(DocumentValidationError):
    """Raised when uploaded file contains zero bytes or only whitespace."""
    pass


class MalformedDocumentError(DocumentValidationError):
    """Raised when file content does not match its declared format or is corrupt."""
    pass


SUPPORTED_EXTENSIONS: Set[str] = {".pdf", ".docx", ".md"}
SUPPORTED_CATEGORIES: Set[str] = {"HR", "IT"}
MAX_FILE_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB


def compute_sha256(content: bytes) -> str:
    """Computes deterministic SHA-256 hex digest of file bytes."""
    return hashlib.sha256(content).hexdigest()


def validate_document_file(filename: str, content: bytes, category: str = "HR") -> Tuple[str, str]:
    """
    Validates document filename, content bytes, and category.
    Returns (cleaned_extension, sha256_checksum).

    Raises:
        EmptyDocumentError: If content is empty (0 bytes).
        UnsupportedFormatError: If file extension is unsupported or category is invalid.
        MalformedDocumentError: If magic bytes or structural verification fails.
    """
    if not filename or "." not in filename:
        raise UnsupportedFormatError(f"Filename '{filename}' is missing a valid extension.")

    ext = "." + filename.rsplit(".", 1)[-1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFormatError(
            f"File extension '{ext}' is not supported. Supported extensions: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    norm_category = category.strip().upper()
    if norm_category not in SUPPORTED_CATEGORIES:
        raise UnsupportedFormatError(
            f"Category '{category}' is invalid. Supported categories: {sorted(SUPPORTED_CATEGORIES)}"
        )

    if not content or len(content) == 0:
        raise EmptyDocumentError(f"Document '{filename}' is empty (0 bytes).")

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise DocumentValidationError(
            f"Document exceeds maximum allowable size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
        )

    # Magic byte and structural format verification
    if ext == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise MalformedDocumentError(f"File '{filename}' claims to be PDF but lacks '%PDF-' signature.")
    elif ext == ".docx":
        if not content.startswith(b"PK\x03\x04"):
            raise MalformedDocumentError(f"File '{filename}' claims to be DOCX but lacks ZIP archive signature.")
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                # Check for standard WordprocessingML document XML
                namelist = z.namelist()
                if "word/document.xml" not in namelist:
                    raise MalformedDocumentError(
                        f"DOCX file '{filename}' does not contain expected 'word/document.xml'."
                    )
        except zipfile.BadZipFile as err:
            raise MalformedDocumentError(f"DOCX file '{filename}' is a corrupted ZIP archive.") from err
    elif ext == ".md":
        try:
            decoded = content.decode("utf-8")
            if not decoded.strip():
                raise EmptyDocumentError(f"Document '{filename}' contains only whitespace.")
        except UnicodeDecodeError as err:
            # Fallback check with latin-1 or report malformed UTF-8
            try:
                content.decode("latin-1")
            except Exception as inner_err:
                raise MalformedDocumentError(f"Text document '{filename}' is not valid text encoding.") from inner_err

    checksum = compute_sha256(content)
    return ext, checksum
