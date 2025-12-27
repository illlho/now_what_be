from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health check 응답 모델"""
    status: str
    timestamp: str
    service: str


@router.get("/health")
async def health_check():
    """
    서비스 상태 확인 엔드포인트
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        service="now_what_be"
    )


@router.get("/")
async def root():
    """
    루트 엔드포인트
    """
    return {
        "message": "Welcome to Now What Backend API",
        "version": "1.0.0",
        "docs": "/docs"
    }

