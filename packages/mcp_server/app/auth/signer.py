"""
Reusable HMAC signing utility for internal API-to-MCP communication.
Constructs canonical signed headers according to Phase 0 v1.7.0 specification.
"""

import hashlib
import hmac
import json
from typing import Dict, Union

from app.auth.models import CallerIdentity


def create_internal_auth_headers(
    identity: Union[CallerIdentity, Dict[str, str]],
    secret: str,
) -> Dict[str, str]:
    """
    Constructs the approved internal identity headers:
    - X-Internal-Identity: Canonical JSON string representation of the identity payload
    - X-Internal-Signature: Hex-encoded HMAC-SHA256 signature computed over X-Internal-Identity bytes
    """
    if not secret or not secret.strip():
        raise ValueError("HMAC signing secret must be a non-empty string.")

    if isinstance(identity, CallerIdentity):
        identity_json = identity.model_dump_json()
    elif isinstance(identity, dict):
        identity_json = json.dumps(identity, separators=(",", ":"))
    else:
        raise TypeError("identity must be a CallerIdentity instance or a dictionary.")

    raw_bytes = identity_json.encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()

    return {
        "X-Internal-Identity": identity_json,
        "X-Internal-Signature": signature,
    }
