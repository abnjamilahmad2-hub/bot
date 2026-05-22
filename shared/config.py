from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    discord_token: str
    discord_client_id: str
    discord_client_secret: str
    
    database_url: str
    redis_url: str
    
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8000
    secret_key: str
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
