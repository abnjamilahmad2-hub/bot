from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    discord_token: str = ""
    discord_client_id: str = ""
    discord_client_secret: str = ""
    
    # Use PostgreSQL by default, fallback to SQLite for local/dev environments
    database_url: str = "sqlite+aiosqlite:///./bot.db"
    redis_url: str = "redis://localhost:6379/0"
    
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8000
    secret_key: str = ""
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
