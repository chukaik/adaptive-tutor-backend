import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routes import onboarding, quiz, adaptive, chat, progress, lesson
from services.auth import get_current_uid
from services.llm_json import ModelReplyError
from services.firebase_service import get_db

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to Firebase when the server starts, as the app did before
    # the connection was made lazy, so bad credentials fail at startup.
    get_db()
    yield


app = FastAPI(title="Adaptive Tutor API", version="1.0.0", lifespan=lifespan)

# Comma-separated list, e.g. "https://app.example.com,http://localhost:8081".
# Unset means no browser origin is allowed. Credentials are off because the
# Firebase token travels in the Authorization header, not in cookies.
allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all route modules. Every route in them requires a valid
# Firebase ID token; only /health below is public.
auth_required = [Depends(get_current_uid)]

app.include_router(onboarding.router, prefix="/onboarding", tags=["Onboarding"], dependencies=auth_required)
app.include_router(quiz.router,       prefix="/quiz",       tags=["Quiz"],       dependencies=auth_required)
app.include_router(adaptive.router,   prefix="/adaptive",   tags=["Adaptive"],   dependencies=auth_required)
app.include_router(chat.router,       prefix="/chat",       tags=["Chat"],       dependencies=auth_required)
app.include_router(progress.router,   prefix="/progress",   tags=["Progress"],   dependencies=auth_required)
app.include_router(lesson.router,     prefix="/lesson",     tags=["Lesson"],     dependencies=auth_required)

@app.exception_handler(ModelReplyError)
def model_reply_error_handler(request: Request, exc: ModelReplyError):
    # The language model (an upstream service) gave an unusable reply twice.
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}