"""
Text normalization service for extracted document contents.
Cleans control artifacts, normalizes Unicode, and regularizes whitespace while preserving structure.
"""

import re
import unicodedata


def normalize_text(text: str) -> str:
    """
    Applies standard enterprise text normalization:
    1. Unicode canonical composition (NFC).
    2. Replacement of non-breaking and zero-width spaces with standard spaces.
    3. Normalization of varied bullet characters to standard bullets.
    4. Collapse of multiple consecutive empty lines to a maximum of two.
    5. Trimming of redundant whitespace per line without destroying markdown table or list indentation.
    """
    if not text:
        return ""

    # 1. Unicode NFC normalization
    normalized = unicodedata.normalize("NFC", text)

    # 2. Replace non-standard whitespace characters (NBSP, em-space, etc.)
    normalized = re.sub(r"[\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000]", " ", normalized)
    normalized = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", normalized)

    # 3. Normalize bullet characters (â€¢, â—, â–ª) to standard hyphen bullet
    normalized = re.sub(r"^[\s]*[â€¢â—â–ªâ—¦]\s*", "- ", normalized, flags=re.MULTILINE)

    # 4. Normalize line endings to \n
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

    # 5. Collapse excessive whitespace across lines
    lines = [line.rstrip() for line in normalized.split("\n")]
    cleaned_text = "\n".join(lines)

    # 6. Collapse 3 or more consecutive newlines into 2
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

    return cleaned_text.strip()
