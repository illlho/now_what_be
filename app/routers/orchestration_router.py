"""오케스트레이션 라우터

여러 Agent 작업을 조율하고 워크플로우를 관리하는 중앙 라우터
"""

from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/orchestration", tags=["orchestration"])

# TODO: 네이버 블로그 검색 기반 워크플로우 구현 예정
