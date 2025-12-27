from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8'
    )
    env: str = 'local'
    database_url: str
    cors_origins: str = 'http://localhost:5173'
    jwt_secret: str
    jwt_algorithm: str = 'HS256'
    access_token_exp_mins: int = 60

settings = Settings()