"""오케스트레이션 API 모델들

오케스트레이션 라우터에서 사용하는 요청/응답 모델들을 정의합니다.
"""

from typing import Optional
from pydantic import BaseModel, Field


class UserLocation(BaseModel):
    """사용자 위치 좌표 모델"""
    latitude: float = Field(..., description="위도", example=37.74608637371771)
    longitude: float = Field(..., description="경도", example=127.03254389562254)
    
    class Config:
        json_schema_extra = {
            "example": {
                "latitude": 37.74608637371771,
                "longitude": 127.03254389562254
            }
        }


class UserRequest(BaseModel):
    """유저의 요청 모델"""
    query: str = Field(..., min_length=1, description="유저가 요청한 내용", example="가능동 삼겹살")
    location: Optional[UserLocation] = Field(
        None,
        description="사용자 위치 좌표 (선택)",
        example={"latitude": 37.74608637371771, "longitude": 127.03254389562254}
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "가능동 삼겹살",
                "location": {
                    "latitude": 37.74608637371771,
                    "longitude": 127.03254389562254
                }
            }
        }


class TokenUsageSummary(BaseModel):
    """토큰 사용량 요약"""
    total_input_tokens: int = Field(..., description="전체 입력 토큰 수")
    total_output_tokens: int = Field(..., description="전체 출력 토큰 수")
    total_tokens: int = Field(..., description="전체 토큰 수")
    total_cost_krw: float = Field(..., description="총 비용 (원)")
    total_cost_formatted: str = Field(..., description="총 비용 포맷 (예: 0.02원(2340 tokens))")
    node_breakdown: list[dict] = Field(default_factory=list, description="노드별 토큰 사용량 상세")


class ReverseGeocodeResult(BaseModel):
    """역지오코딩 결과 모델"""
    location_keyword: Optional[str] = Field(None, description="위치 키워드 (예: 명동, 강남구)")
    depth_1: Optional[str] = Field(None, description="시/도 (예: 서울특별시)")
    depth_2: Optional[str] = Field(None, description="시/군/구 (예: 중구)")
    depth_3: Optional[str] = Field(None, description="읍/면/동 (예: 명동)")
    depth_4: Optional[str] = Field(None, description="상세 지역 (예: 태평로1가)")
    address: Optional[str] = Field(None, description="전체 주소")


class OrchestrationResponse(BaseModel):
    """오케스트레이션 응답 모델"""
    result_dict: dict = Field(..., description="평가 결과 (dict 형태)")
    query: str
    success: bool = True
    token_usage: Optional[TokenUsageSummary] = Field(None, description="토큰 사용량 및 비용 정보")
    reverse_geocode_result: Optional[ReverseGeocodeResult] = Field(None, description="역지오코딩 결과")
