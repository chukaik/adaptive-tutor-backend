"""
Model settings for every OpenAI call, in one place.

The model name can be overridden with the OPENAI_MODEL environment
variable; temperatures and token limits are fixed per task.
"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "gpt-4o-mini"
MODEL = os.getenv("OPENAI_MODEL") or DEFAULT_MODEL


@dataclass(frozen=True)
class CallSettings:
    temperature: float
    max_tokens: int


HINT        = CallSettings(temperature=0.5, max_tokens=150)
EXPLANATION = CallSettings(temperature=0.5, max_tokens=200)
GRADING     = CallSettings(temperature=0.1, max_tokens=100)
CHAT        = CallSettings(temperature=0.7, max_tokens=500)
QUIZ        = CallSettings(temperature=0.8, max_tokens=3000)
LESSON      = CallSettings(temperature=0.6, max_tokens=6000)
