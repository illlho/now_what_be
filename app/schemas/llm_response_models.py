"""LLM 응답 모델들

워크플로우 노드에서 LLM 호출 시 사용하는 Pydantic 응답 모델들을 정의합니다.
with_structured_output을 사용하여 타입 안전한 응답을 보장합니다.
"""

from typing import Optional
from pydantic import BaseModel, Field


class BlogItemEvaluation(BaseModel):
    """개별 블로그 항목 평가 결과"""
    link: str = Field(..., description="블로그 링크 (고유 식별자)")
    is_relevant: bool = Field(..., description="사용자 질문과 연관성이 있는지")
    reasoning: str = Field(..., description="평가 이유 (최대 50자)")


class BlogItemsEvaluationResult(BaseModel):
    """여러 블로그 항목 평가 결과 모델"""
    items: list[BlogItemEvaluation] = Field(..., description="각 항목별 평가 결과 리스트")


class QueryAnalysisResult(BaseModel):
    """사용자 쿼리 분석 결과"""
    is_relevant: bool = Field(..., description="맛집 검색과 관련된 질문인지 여부")
    location_keyword: Optional[str] = Field(
        None, 
        description="추출된 위치 키워드. 예: '강남역', '홍대', '가능동', '역삼동', '서울', '부산' 등 지역명, 동명, 역명, 지명 모두 포함"
    )
    food_keyword: Optional[str] = Field(
        None, 
        description="추출된 음식/카테고리 키워드. 예: '파스타', '한식', '삼겹살', '카페', '치킨' 등"
    )
    needs_location_resolution: bool = Field(
        False, 
        description="좌표를 통해 위치를 조회해야 하는지. '근처', '주변', '여기' 등 위치 키워드가 없을 때만 true"
    )
    reason: str = Field(..., description="분석 이유 (최대 50자)")
