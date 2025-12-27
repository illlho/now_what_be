import logging
from pydantic_settings import BaseSettings
from typing import Optional, Literal
from app.exceptions import APIKeyError


# 로그 레벨 타입 정의
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """애플리케이션 설정"""
    openai_api_key: Optional[str] = None
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    log_level: Optional[str] = None  # 환경 변수에서 읽어옴
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def get_log_level(self) -> int:
        """로그 레벨을 반환 (기본값: ERROR)"""
        if not self.log_level:
            return logging.ERROR
        
        # 대소문자 구분 없이 처리
        log_level_upper = self.log_level.upper()
        
        # 유효한 로그 레벨 매핑
        log_levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        
        # 유효하지 않은 값이면 ERROR 반환
        return log_levels.get(log_level_upper, logging.ERROR)
    
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

