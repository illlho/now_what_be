"""오케스트레이션 API 모델들

오케스트레이션 라우터에서 사용하는 요청/응답 모델들을 정의합니다.
"""

from typing import Optional
from pydantic import BaseModel, Field


class UserRequest(BaseModel):
    """유저의 요청 모델"""
    query: str = Field(default="가능동 삼겹살", min_length=1, description="유저가 요청한 내용")


class TokenUsageSummary(BaseModel):
    """토큰 사용량 요약"""
    total_input_tokens: int = Field(..., description="전체 입력 토큰 수")
    total_output_tokens: int = Field(..., description="전체 출력 토큰 수")
    total_tokens: int = Field(..., description="전체 토큰 수")
    total_cost_krw: float = Field(..., description="총 비용 (원)")
    total_cost_formatted: str = Field(..., description="총 비용 포맷 (예: 0.02원(2340 tokens))")
    node_breakdown: list[dict] = Field(default_factory=list, description="노드별 토큰 사용량 상세")


class OrchestrationResponse(BaseModel):
    """오케스트레이션 응답 모델"""
    result_dict: dict = Field(..., description="평가 결과 (dict 형태)")
    query: str
    success: bool = True
    token_usage: Optional[TokenUsageSummary] = Field(None, description="토큰 사용량 및 비용 정보")


class GraphVisualizationResponse(BaseModel):
    """그래프 시각화 응답 모델"""
    mermaid_code: str = Field(..., description="Mermaid 다이어그램 코드")
    ascii_art: str = Field(..., description="ASCII 아트 표현")

