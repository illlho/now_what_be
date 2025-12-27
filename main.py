from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import agent_router, health_router
from app.config import settings

# FastAPI 앱 생성
app = FastAPI(
    title="Now What Backend API",
    description="LangGraph를 활용한 AI Agent 백엔드 서비스",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

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
]

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # 브라우저 기반 클라이언트용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(health_router.router)
app.include_router(agent_router.router)


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    print("🚀 Now What Backend API 서버가 시작되었습니다.")
    print(f"📚 API 문서: http://{settings.host}:{settings.port}/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행"""
    print("👋 Now What Backend API 서버가 종료되었습니다.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

