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


# Initialize on import
db = init_firebase()


def get_document(collection: str, doc_id: str):
    doc = db.collection(collection).document(doc_id).get()
    if doc.exists:
        return {"id": doc.id, **doc.to_dict()}
    return None


def set_document(collection: str, doc_id: str, data: dict):
    db.collection(collection).document(doc_id).set(data)


def update_document(collection: str, doc_id: str, data: dict):
    db.collection(collection).document(doc_id).update(data)


def add_document(collection: str, data: dict):
    doc_ref = db.collection(collection).add(data)
    return doc_ref[1].id


def query_collection(collection: str, filters: list):
    ref = db.collection(collection)
    for field, op, value in filters:
        ref = ref.where(field, op, value)
    docs = ref.stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


def delete_document(collection: str, doc_id: str):
    db.collection(collection).document(doc_id).delete()