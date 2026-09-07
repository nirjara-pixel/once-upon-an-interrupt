"""Environment-driven configuration. Secrets come from .env / env vars only."""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.fish_audio_api_key: str = os.getenv("FISH_AUDIO_API_KEY", "")
        self.huggingface_api_key: str = os.getenv("HUGGINGFACE_API_KEY", "")
        self.groq_api_key: str = os.getenv("GROQ_API_KEY", "")
        self.groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.hf_model: str = os.getenv(
            "HF_MODEL", "meta-llama/Llama-3.1-8B-Instruct"
        )
        self.fish_tts_model: str = os.getenv("FISH_TTS_MODEL", "s1")
        # "Sarah" — Fish marketplace "Gentle Hindi Female" (hi+en, Indian accent)
        self.fish_default_voice_id: str = os.getenv(
            "FISH_DEFAULT_VOICE_ID", "fc53c5a8a3fd4e2aaa1d4b7eded7ef3f"
        )
        self.app_env: str = os.getenv("APP_ENV", "development")

    @property
    def has_fish(self) -> bool:
        return bool(self.fish_audio_api_key) and self.fish_audio_api_key != "replace_me"

    @property
    def has_hf(self) -> bool:
        return bool(self.huggingface_api_key) and self.huggingface_api_key != "replace_me"

    @property
    def has_groq(self) -> bool:
        return bool(self.groq_api_key) and self.groq_api_key != "replace_me"


settings = Settings()
