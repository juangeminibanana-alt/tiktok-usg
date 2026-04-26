"""
firebase_config.py
──────────────────
Initializes the Firebase Admin SDK using a service-account key file.
All other modules import `init_firebase()` and call it once at startup.
"""

import os
import logging
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
_SERVICE_ACCOUNT_PATH = Path(
    os.environ.get("FIREBASE_SA_KEY", "serviceAccountKey.json")
)
_PROJECT_ID = "e-book-21589"
_DATABASE_URL = os.environ.get(
    "FIREBASE_DATABASE_URL",
    f"https://{_PROJECT_ID}-default-rtdb.firebaseio.com",
)

# ── Public API ─────────────────────────────────────────────────────────────────

def init_firebase() -> firebase_admin.App:
    """
    Initializes the Firebase Admin SDK exactly once (idempotent).
    Supports both Service Account Key files and Application Default Credentials (ADC).
    """
    # Guard: already initialised
    if firebase_admin._apps:
        logger.debug("Firebase already initialised — skipping.")
        return firebase_admin.get_app()

    # Determine credentials
    try:
        if _SERVICE_ACCOUNT_PATH.exists():
            logger.info(f"Using Service Account Key from: {_SERVICE_ACCOUNT_PATH}")
            cred = credentials.Certificate(str(_SERVICE_ACCOUNT_PATH))
        else:
            logger.info("Service account key not found. Attempting Application Default Credentials (ADC)...")
            cred = credentials.ApplicationDefault()
    except Exception as e:
        raise RuntimeError(
            f"Failed to initialize Firebase credentials. "
            f"Please ensure {_SERVICE_ACCOUNT_PATH} exists OR run 'gcloud auth application-default login'. "
            f"Error: {e}"
        )

    # Validate database URL
    if not _DATABASE_URL or "<YOUR-PROJECT-ID>" in _DATABASE_URL:
        raise ValueError(
            "FIREBASE_DATABASE_URL is not configured correctly. "
            "Set the environment variable to your real Realtime Database URL."
        )

    app = firebase_admin.initialize_app(
        cred,
        options={
            "databaseURL": _DATABASE_URL,
            "projectId": _PROJECT_ID
        },
    )

    logger.info(
        "Firebase initialised. Project: %s | DB: %s",
        app.project_id,
        _DATABASE_URL,
    )
    return app


def get_db_ref(path: str) -> db.Reference:
    """
    Convenience wrapper that returns a Firebase Realtime Database reference.

    Parameters
    ----------
    path : str
        Absolute Firebase path, e.g. '/sessions/abc123/agent_0'.

    Returns
    -------
    firebase_admin.db.Reference
    """
    return db.reference(path)
