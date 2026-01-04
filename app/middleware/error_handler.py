"""전역 예외 핸들러"""

import logging
import traceback
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.exceptions import BaseAPIException, APIKeyError, ConfigurationError, ValidationError
from app.schemas.error import ErrorResponse, ValidationErrorResponse, ErrorDetail, ValidationErrorDetail
from app.constants.error_codes import ErrorCode

logger = logging.getLogger(__name__)


async def base_exception_handler(request: Request, exc: BaseAPIException):
    """커스텀 예외 핸들러"""
    logger.error(
        f"API Error: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    # Pydantic 모델을 사용한 에러 응답 생성
    error_detail = ErrorDetail(
        code=exc.error_code,
        message=exc.message,
        type=exc.__class__.__name__,
        details=None
    )
    error_response = ErrorResponse(success=False, error=error_detail)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Pydantic 검증 에러 핸들러"""
    errors = exc.errors()
    error_messages = []
    
    for error in errors:
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        error_messages.append(f"{field}: {message}")
    
    error_message = "입력 검증 실패: " + ", ".join(error_messages)
    
    logger.warning(
        f"Validation Error: {error_message}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": errors
        }
    )
    
    # Pydantic 모델을 사용한 검증 에러 응답 생성
    error_detail = ValidationErrorDetail(
        code=ErrorCode.VALIDATION_ERROR,
        message=error_message,
        details=errors
    )
    error_response = ValidationErrorResponse(success=False, error=error_detail)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump()
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP 예외 핸들러"""
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    # Pydantic 모델을 사용한 HTTP 에러 응답 생성
    error_detail = ErrorDetail(
        code=ErrorCode.http_error(exc.status_code),
        message=exc.detail,
        type="HTTPException",
        details=None
    )
    error_response = ErrorResponse(success=False, error=error_detail)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 핸들러 (예상치 못한 에러)"""
    error_traceback = traceback.format_exc()
    
    logger.error(
        f"Unexpected Error: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "traceback": error_traceback
        },
        exc_info=True
    )
    
    # 프로덕션 환경에서는 상세 에러 정보를 숨김
    error_message = "서버 내부 오류가 발생했습니다."
    error_details = None
    try:
        # app.state에서 설정 가져오기 (없으면 기본값 사용)
        app_settings = getattr(request.app.state, 'settings', None)
        if app_settings and getattr(app_settings, 'debug', False):
            error_message = f"서버 내부 오류: {str(exc)}"
            error_details = {"traceback": error_traceback}
    except Exception:
        # 설정 접근 실패 시 기본 메시지 사용
        pass
    
    # Pydantic 모델을 사용한 일반 에러 응답 생성
    error_detail = ErrorDetail(
        code=ErrorCode.INTERNAL_SERVER_ERROR,
        message=error_message,
        type=exc.__class__.__name__,
        details=error_details
    )
    error_response = ErrorResponse(success=False, error=error_detail)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump()
    )

