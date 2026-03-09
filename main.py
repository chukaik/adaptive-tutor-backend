from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.firebase_service import get_document

app = FastAPI(title="Adaptive Tutor API", version="1.0.0")

# Allow FlutterFlow to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/test-firebase")
def test_firebase():
    # This will try to read from your users collection
    result = get_document("users", "testUserId")
    return {"firebase_connected": True, "test_result": result}