from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import onboarding, quiz, adaptive, chat, progress, lesson

app = FastAPI(title="Adaptive Tutor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all route modules
app.include_router(onboarding.router, prefix="/onboarding", tags=["Onboarding"])
app.include_router(quiz.router,       prefix="/quiz",       tags=["Quiz"])
app.include_router(adaptive.router,   prefix="/adaptive",   tags=["Adaptive"])
app.include_router(chat.router,       prefix="/chat",       tags=["Chat"])
app.include_router(progress.router,   prefix="/progress",   tags=["Progress"])
app.include_router(lesson.router,     prefix="/lesson",     tags=["Lesson"])

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}