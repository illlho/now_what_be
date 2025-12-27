"""에러 응답 스키마 정의"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """에러 상세 정보 모델"""
    code: str = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    type: str = Field(..., description="예외 타입")
    details: Optional[Dict[str, Any]] = Field(None, description="추가 상세 정보")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "API_KEY_ERROR",
                "message": "API 키가 설정되지 않았습니다.",
                "type": "APIKeyError",
                "details": None
            }
        }


class ErrorResponse(BaseModel):
    """표준 에러 응답 모델"""
    success: bool = Field(False, description="요청 성공 여부")
    error: ErrorDetail = Field(..., description="에러 상세 정보")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "API_KEY_ERROR",
                    "message": "API 키가 설정되지 않았습니다.",
                    "type": "APIKeyError",
                    "details": None
                }
            }
        }


class ValidationErrorDetail(BaseModel):
    """검증 에러 상세 정보 모델"""
    code: str = Field("VALIDATION_ERROR", description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    details: Optional[List[Dict[str, Any]]] = Field(None, description="검증 실패 상세 목록")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "VALIDATION_ERROR",
                "message": "입력 검증 실패: body -> query: ensure this value has at least 1 characters",
                "details": [
                    {
                        "loc": ["body", "query"],
                        "msg": "ensure this value has at least 1 characters",
                        "type": "value_error.any_str.min_length"
                    }
                ]
            }
        }


class ValidationErrorResponse(BaseModel):
    """검증 에러 응답 모델"""
    success: bool = Field(False, description="요청 성공 여부")
    error: ValidationErrorDetail = Field(..., description="검증 에러 상세 정보")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "입력 검증 실패: body -> query: ensure this value has at least 1 characters",
                    "details": [
                        {
                            "loc": ["body", "query"],
                            "msg": "ensure this value has at least 1 characters",
                            "type": "value_error.any_str.min_length"
                        }
                    ]
                }
            }
        }

