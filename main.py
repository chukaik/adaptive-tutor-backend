from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import onboarding, quiz, adaptive, chat, progress, lesson
from services.auth import get_current_uid

app = FastAPI(title="Adaptive Tutor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}