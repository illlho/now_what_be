"""LLM 응답 모델들

워크플로우 노드에서 LLM 호출 시 사용하는 Pydantic 응답 모델들을 정의합니다.
with_structured_output을 사용하여 타입 안전한 응답을 보장합니다.
"""

from pydantic import BaseModel, Field


class BlogItemEvaluation(BaseModel):
    """개별 블로그 항목 평가 결과"""
    link: str = Field(..., description="블로그 링크 (고유 식별자)")
    is_relevant: bool = Field(..., description="사용자 질문과 연관성이 있는지")
    reasoning: str = Field(..., description="평가 이유 (최대 50자)")


class BlogItemsEvaluationResult(BaseModel):
    """여러 블로그 항목 평가 결과 모델"""
    items: list[BlogItemEvaluation] = Field(..., description="각 항목별 평가 결과 리스트")
