"""
Test setup. Runs before any test module imports the app.

The app initialises Firebase and builds an OpenAI client when its modules
are imported. Here those are replaced with stand-ins so that no test needs
credentials or contacts Firebase or OpenAI.
"""
import os
import sys
from unittest.mock import MagicMock

# Make the project root importable (main, routes, services, models).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# A dummy key: the OpenAI client is constructed at import but never called.
# load_dotenv() does not override variables that are already set.
os.environ["OPENAI_API_KEY"] = "test-key-not-used"
os.environ.pop("FIREBASE_SERVICE_ACCOUNT", None)

import firebase_admin  # noqa: E402
from firebase_admin import credentials, firestore  # noqa: E402

credentials.Certificate = lambda *args, **kwargs: MagicMock(name="Certificate")
firebase_admin.initialize_app = lambda *args, **kwargs: MagicMock(name="App")
firestore.client = lambda *args, **kwargs: MagicMock(name="FirestoreClient")
