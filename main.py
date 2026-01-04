import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.routers import orchestration_router
from app.config import settings
from app.exceptions import (
    BaseAPIException,
    APIKeyError,
    ConfigurationError,
    ValidationError
)
from app.middleware.error_handler import (
    base_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from app.middleware.logging_middleware import LoggingMiddleware

# 로깅 설정 (환경 변수 LOG_LEVEL 사용, 없으면 ERROR)
log_level = settings.get_log_level()
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# 로그 레벨 정보 출력
log_level_name = logging.getLevelName(log_level)
logger.info(f"로그 레벨: {log_level_name} (LOG_LEVEL={settings.log_level or '미설정 (기본값: ERROR)'})")

# Swagger 설정 import
from app.swagger.config import TAGS_METADATA, SERVERS, custom_openapi, custom_swagger_ui_html


# Lifespan 이벤트 핸들러
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작 및 종료 시 실행되는 이벤트 핸들러"""
    # 시작 시 실행
    logger.info("🚀 Now What Backend API 서버가 시작되었습니다.")
    logger.info(f"📚 API 문서: http://{settings.host}:{settings.port}/docs")
    
    # API 키 설정 확인 (경고만 표시, 서버는 시작)
    if not settings.openai_api_key:
        logger.warning(
            "⚠️  OPENAI_API_KEY가 설정되지 않았습니다. "
            "LLM 기능을 사용하려면 .env 파일에 OPENAI_API_KEY를 설정하세요."
        )
    else:
        logger.info("✓ OpenAI API 키가 설정되었습니다.")
    
    yield  # 여기서 애플리케이션이 실행됨
    
    # 종료 시 실행
    logger.info("👋 Now What Backend API 서버가 종료되었습니다.")


# FastAPI 앱 생성
app = FastAPI(
    title="Now What Backend API",
    description="""
    맛집 검색 백엔드 서비스
    
    ## 주요 기능
    
    * **맛집 검색**: 네이버 블로그 기반 맛집 검색 및 평가
    
    ## 인증
    
    현재는 인증이 필요하지 않습니다.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=TAGS_METADATA,
    servers=SERVERS,
    lifespan=lifespan,
)

# 설정을 app state에 저장 (에러 핸들러에서 사용)
app.state.settings = settings

# CORS 허용 오리진 설정
# 참고: Postman, cURL 등 브라우저가 아닌 도구는 CORS 정책의 영향을 받지 않습니다.
# 아래 설정은 브라우저 기반 클라이언트(웹 앱, Swagger UI 등)를 위한 것입니다.
ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React 기본 포트
    "http://localhost:5173",  # Vite 기본 포트
    "http://localhost:8080",  # Vue 기본 포트
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
    "http://localhost:8000",  # Swagger UI
    "http://127.0.0.1:8000",  # Swagger UI
]

# 개발 환경에서는 모든 Origin 허용 (디버그 모드일 때)
# 프로덕션에서는 ALLOWED_ORIGINS만 허용
if settings.debug:
    logger.info("🔓 개발 모드: CORS가 모든 Origin을 허용합니다.")
    cors_origins = ["*"]  # 개발 환경에서는 모든 Origin 허용
else:
    cors_origins = ALLOWED_ORIGINS
    logger.info(f"🔒 프로덕션 모드: CORS가 {len(ALLOWED_ORIGINS)}개의 Origin만 허용합니다.")

# CORS 설정 (가장 먼저 등록하여 OPTIONS 요청을 먼저 처리)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,  # 개발/프로덕션에 따라 다르게 설정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 로깅 미들웨어 등록 (CORS 이후에 실행)
app.add_middleware(LoggingMiddleware)

# 예외 핸들러 등록
app.add_exception_handler(BaseAPIException, base_exception_handler)
app.add_exception_handler(APIKeyError, base_exception_handler)
app.add_exception_handler(ConfigurationError, base_exception_handler)
app.add_exception_handler(ValidationError, base_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# 라우터 등록
app.include_router(orchestration_router.router)


# Swagger UI 커스터마이징 적용
app.openapi = lambda: custom_openapi(app)


@app.get("/docs", include_in_schema=False)
async def swagger_ui_html():
    """커스터마이징된 Swagger UI HTML"""
    return custom_swagger_ui_html(app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

