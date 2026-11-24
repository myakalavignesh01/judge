from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "JudgeX API"
    environment: str = "development"
    database_url: str = "sqlite:///./judgex.db"
    jwt_secret: str = "replace-this-with-a-long-random-secret"
    access_token_minutes: int = 60
    frontend_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    public_base_url: str = ""
    upload_root: str = ""
    allow_organizer_signup: bool = False
    bootstrap_organizer_name: str = ""
    bootstrap_organizer_email: str = ""
    bootstrap_organizer_institution: str = "JudgeX"
    bootstrap_organizer_password: str = ""
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_text_model: str = "gpt-6.2-astra"
    openai_transcription_model: str = "gpt-transcribe"
    openai_embedding_model: str = "text-embedding-3-small"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_starttls: bool = True
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://127.0.0.1:8000/api/v1/auth/google/callback"
    github_token: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]

    @property
    def effective_google_redirect_uri(self) -> str:
        if self.public_base_url:
            return f"{self.public_base_url.rstrip('/')}/api/v1/auth/google/callback"
        return self.google_redirect_uri


settings = Settings()
