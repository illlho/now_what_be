from pydantic_settings import BaseSettings
from typing import Optional
from app.exceptions import APIKeyError


class Settings(BaseSettings):
    """애플리케이션 설정"""
    openai_api_key: Optional[str] = None
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def validate_openai_key(self) -> str:
        """OpenAI API 키 검증 및 반환"""
        if not self.openai_api_key:
            raise APIKeyError(
                "OPENAI_API_KEY가 설정되지 않았습니다. "
                ".env 파일을 생성하고 OPENAI_API_KEY를 설정하세요. "
                ".env.example 파일을 참고하세요."
            )
        return self.openai_api_key


settings = Settings()

