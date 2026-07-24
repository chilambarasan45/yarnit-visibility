from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:admin123@localhost:5432/yarnit"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # API Keys
    SERP_API_KEY:   str = ""
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    API_SECRET_KEY: str = ""
    # Model names — as instructed by JD: Gemini 3.1 Flash-Lite + GPT-5.4 Mini
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"
    OPENAI_MODEL: str = "gpt-5.4-mini"

    # App settings
    APP_NAME: str = "Yarnit AI Visibility Platform"
    DEBUG:    bool = True

    class Config:
        env_file = ".env"

settings = Settings()