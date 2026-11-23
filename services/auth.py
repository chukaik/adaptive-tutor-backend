"""
Request authentication.

Every client request carries "Authorization: Bearer <Firebase ID token>".
get_current_uid verifies that token with Firebase and returns the caller's
uid; require_same_user rejects requests that name a different user.
"""
import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth

from services.firebase_service import get_db

logger = logging.getLogger(__name__)

# auto_error=False so that a missing header gives our own 401 (HTTPBearer
# would otherwise answer 403).
_bearer = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_uid(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Return the uid from a valid Firebase ID token, or answer 401."""
    if credentials is None or not credentials.credentials:
        raise _unauthorized("Missing bearer token.")

    # verify_id_token needs the Firebase app to be initialised.
    get_db()

    try:
        decoded = auth.verify_id_token(credentials.credentials)
    except (auth.InvalidIdTokenError, ValueError) as exc:
        # InvalidIdTokenError covers expired and revoked tokens too.
        logger.info("Rejected ID token: %s", exc)
        raise _unauthorized("Invalid or expired token.")
    except auth.CertificateFetchError:
        logger.exception("Could not fetch Firebase public keys")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not verify token right now. Try again shortly.",
        )

    uid = decoded.get("uid")
    if not uid:
        raise _unauthorized("Invalid or expired token.")
    return uid


def require_same_user(user_id: str, uid: str) -> None:
    """Answer 403 if the request names a user other than the caller."""
    if user_id != uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own data.",
        )
