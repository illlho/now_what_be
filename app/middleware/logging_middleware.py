"""요청/응답 로깅 미들웨어"""

import uuid
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """요청/응답 로깅 미들웨어
    
    모든 HTTP 요청과 응답을 로깅하며, 요청 ID를 생성하여 추적 가능하게 합니다.
    """
    
    async def dispatch(self, request: Request, call_next):
        # 요청 ID 생성
        request_id = str(uuid.uuid4())[:8]  # 짧은 형식 (8자리)
        
        # 요청 시작 시간
        start_time = time.time()
        
        # 요청 정보 로깅
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        origin = request.headers.get("origin", "none")
        
        logger.info(
            f"[{request_id}] {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "origin": origin,
            }
        )
        
        # OPTIONS 요청의 경우 Origin 헤더를 명시적으로 로깅
        if request.method == "OPTIONS":
            logger.debug(
                f"[{request_id}] OPTIONS preflight request - Origin: {origin}",
                extra={"request_id": request_id, "origin": origin}
            )
        
        # 요청 본문 로깅 (선택적, 큰 요청은 제외)
        # 주의: body를 읽으면 스트림이 소비되므로, 실제로는 헤더 정보만 로깅
        content_type = request.headers.get("content-type", "")
        content_length = request.headers.get("content-length", "0")
        
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                content_length_int = int(content_length) if content_length.isdigit() else 0
                if content_length_int > 0 and content_length_int < 1000:  # 1KB 이하만 상세 로깅
                    logger.debug(
                        f"[{request_id}] Request content-type: {content_type}, "
                        f"content-length: {content_length}",
                        extra={
                            "request_id": request_id,
                            "content_type": content_type,
                            "content_length": content_length_int
                        }
                    )
            except Exception as e:
                logger.debug(
                    f"[{request_id}] Failed to parse content-length: {str(e)}",
                    extra={"request_id": request_id}
                )
        
        # 다음 미들웨어/라우터 실행
        try:
            response = await call_next(request)
        except Exception as e:
            # 예외 발생 시 로깅
            process_time = time.time() - start_time
            logger.error(
                f"[{request_id}] {request.method} {request.url.path} "
                f"Exception: {str(e)} Time: {process_time:.3f}s",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": process_time,
                    "exception": str(e),
                },
                exc_info=True
            )
            raise
        
        # 응답 시간 계산
        process_time = time.time() - start_time
        
        # 응답 정보 로깅
        status_code = response.status_code
        log_level = "error" if status_code >= 500 else "warning" if status_code >= 400 else "info"
        
        log_message = (
            f"[{request_id}] {request.method} {request.url.path} "
            f"Status: {status_code} Time: {process_time:.3f}s"
        )
        
        log_extra = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "process_time": process_time,
        }
        
        # 응답 크기 정보 추가 (가능한 경우)
        if hasattr(response, "body"):
            try:
                response_size = len(response.body) if response.body else 0
                log_extra["response_size"] = response_size
            except Exception:
                pass
        
        # 로그 레벨에 따라 출력
        if log_level == "error":
            logger.error(log_message, extra=log_extra)
        elif log_level == "warning":
            logger.warning(log_message, extra=log_extra)
        else:
            logger.info(log_message, extra=log_extra)
        
        # 응답 헤더에 요청 ID 추가
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.3f}"
        
        return response

