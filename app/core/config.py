import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
    OPENROUTER_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./recovery.db")
    MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", 3))
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", 0.70))
    ALLOWED_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
        if origin.strip()
    ]


    # Rough per-action cost in INR, used for net-recovery economics
    ACTION_COST = {
        "retry_immediate": 0.0,
        "retry_in_24h": 0.0,
        "send_nudge": 0.50,       # SMS cost
        "request_new_method": 0.50,
        "escalate_human": 50.0,
        "give_up": 0.0,
    }


settings = Settings()
