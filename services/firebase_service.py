import firebase_admin
from firebase_admin import credentials, firestore
import os
import json


def init_firebase():
    if firebase_admin._apps:
        return firestore.client()

    # Production: service account loaded from environment variable
    service_account_env = os.getenv("FIREBASE_SERVICE_ACCOUNT")

    if service_account_env:
        service_account_dict = json.loads(service_account_env)
        cred = credentials.Certificate(service_account_dict)
    else:
        # Local development: load from file
        cred = credentials.Certificate("serviceAccountKey.json")

    firebase_admin.initialize_app(cred)
    return firestore.client()


# Connect on first use rather than on import, so that importing the app
# (for example in tests) does not need credentials. main.py still calls
# get_db() at startup, so a running server connects when it starts.
_db = None


def get_db():
    """Return the Firestore client, initialising Firebase the first time."""
    global _db
    if _db is None:
        _db = init_firebase()
    return _db


def get_document(collection: str, doc_id: str):
    doc = get_db().collection(collection).document(doc_id).get()
    if doc.exists:
        return {"id": doc.id, **doc.to_dict()}
    return None


def set_document(collection: str, doc_id: str, data: dict):
    get_db().collection(collection).document(doc_id).set(data)


def update_document(collection: str, doc_id: str, data: dict):
    get_db().collection(collection).document(doc_id).update(data)


def add_document(collection: str, data: dict):
    doc_ref = get_db().collection(collection).add(data)
    return doc_ref[1].id


def query_collection(collection: str, filters: list):
    ref = get_db().collection(collection)
    for field, op, value in filters:
        ref = ref.where(field, op, value)
    docs = ref.stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


def delete_document(collection: str, doc_id: str):
    get_db().collection(collection).document(doc_id).delete()
