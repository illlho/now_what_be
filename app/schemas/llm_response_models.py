"""LLM 응답 모델들

워크플로우 노드에서 LLM 호출 시 사용하는 Pydantic 응답 모델들을 정의합니다.
with_structured_output을 사용하여 타입 안전한 응답을 보장합니다.
"""

from typing import Optional
from pydantic import BaseModel, Field


class QueryEvaluationResult(BaseModel):
    """쿼리 평가 결과 모델
    
    사용자 입력이 맛집 검색 서비스에 적합한지 판단한 결과를 담는 모델입니다.
    """
    is_valid: bool = Field(..., description="맛집 검색에 적합한 쿼리인지 (다음 단계 진행 가능 여부)")
    is_inappropriate: bool = Field(default=False, description="부적절하거나 맛집 검색과 무관한 질문인지")
    missing_info: list[str] = Field(default_factory=list, description="부족한 정보 리스트 (예: ['위치', '음식종류'])")
    location: Optional[str] = Field(None, description="추출된 위치 정보 (있으면)")
    search_item: Optional[str] = Field(None, description="추출된 음식 종류 (있으면)")
    reasoning: str = Field(..., description="판단 이유")

