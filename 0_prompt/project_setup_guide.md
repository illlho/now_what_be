# 프로젝트 생성 지시문서

## 프로젝트 개요

파이썬을 이용한 백엔드 프로젝트를 개발합니다. LangGraph를 이용한 AI Agent 활용 프로젝트이며, 기본적인 필수 항목을 포함한 FastAPI POST 예제를 라우팅되는 구조로 만듭니다.

## 기술 스택

- **FastAPI**: 고성능 웹 프레임워크
- **LangGraph**: AI Agent 오케스트레이션
- **LangChain**: LLM 통합
- **OpenAI**: GPT 모델
- **Uvicorn**: ASGI 서버
- **Pydantic**: 데이터 검증 및 설정 관리

## 프로젝트 구조

```
프로젝트명/
├── app/
│   ├── __init__.py
│   ├── config.py              # 설정 관리 (환경 변수)
│   ├── agents/
│   │   ├── __init__.py
│   │   └── agent.py           # LangGraph Agent 구현
│   └── routers/
│       ├── __init__.py
│       ├── agent_router.py    # Agent 관련 라우터
│       └── health_router.py   # Health check 라우터
├── main.py                    # FastAPI 애플리케이션 진입점
├── requirements.txt           # Python 패키지 의존성
├── .env.example              # 환경 변수 예제
├── .gitignore                # Git 무시 파일
└── README.md                 # 프로젝트 문서
```

## 필수 파일 생성

### 1. requirements.txt

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
langgraph==0.0.20
langchain==0.1.0
langchain-openai==0.0.2
langchain-core==0.1.10
python-dotenv==1.0.0
python-multipart==0.0.6
```

### 2. app/config.py

```python
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """애플리케이션 설정"""
    openai_api_key: str
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
```

### 3. app/agents/agent.py

LangGraph를 사용한 AI Agent 구현:

```python
from typing import TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import operator
from app.config import settings


class AgentState(TypedDict):
    """Agent 상태 정의"""
    messages: Annotated[list, add_messages]
    user_query: str
    response: str


class LangGraphAgent:
    """LangGraph를 사용한 AI Agent"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.7,
            api_key=settings.openai_api_key
        )
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """LangGraph 그래프 구성"""
        workflow = StateGraph(AgentState)
        
        # 노드 추가
        workflow.add_node("process_query", self._process_query)
        workflow.add_node("generate_response", self._generate_response)
        
        # 엣지 추가
        workflow.set_entry_point("process_query")
        workflow.add_edge("process_query", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    def _process_query(self, state: AgentState) -> AgentState:
        """사용자 쿼리 처리"""
        # 쿼리 전처리 또는 검증 로직 추가 가능
        return state
    
    def _generate_response(self, state: AgentState) -> AgentState:
        """LLM을 사용한 응답 생성"""
        user_query = state.get("user_query", "")
        
        # LLM 호출
        response = self.llm.invoke(user_query)
        
        state["response"] = response.content if hasattr(response, 'content') else str(response)
        return state
    
    async def process(self, user_query: str) -> str:
        """Agent 실행"""
        initial_state = {
            "messages": [],
            "user_query": user_query,
            "response": ""
        }
        
        result = await self.graph.ainvoke(initial_state)
        return result.get("response", "")


# 싱글톤 인스턴스
agent = LangGraphAgent()
```

### 4. app/routers/agent_router.py

Agent 관련 POST 엔드포인트:

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.agents.agent import agent

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


class AgentRequest(BaseModel):
    """Agent 요청 모델"""
    query: str
    max_length: int = 500


class AgentResponse(BaseModel):
    """Agent 응답 모델"""
    response: str
    query: str
    success: bool = True


@router.post("/chat", response_model=AgentResponse)
async def chat_with_agent(request: AgentRequest):
    """
    AI Agent와 대화하는 엔드포인트
    
    - **query**: 사용자 질문 또는 요청
    - **max_length**: 최대 응답 길이 (기본값: 500)
    """
    try:
        if not request.query or len(request.query.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Query cannot be empty"
            )
        
        # Agent 실행
        response_text = await agent.process(request.query)
        
        # 응답 길이 제한
        if len(response_text) > request.max_length:
            response_text = response_text[:request.max_length] + "..."
        
        return AgentResponse(
            response=response_text,
            query=request.query,
            success=True
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent processing failed: {str(e)}"
        )


@router.post("/analyze", response_model=AgentResponse)
async def analyze_text(request: AgentRequest):
    """
    텍스트 분석을 위한 엔드포인트
    
    - **query**: 분석할 텍스트
    """
    try:
        analysis_query = f"다음 텍스트를 분석해주세요: {request.query}"
        response_text = await agent.process(analysis_query)
        
        return AgentResponse(
            response=response_text,
            query=request.query,
            success=True
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )
```

### 5. app/routers/health_router.py

Health check 라우터:

```python
from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health check 응답 모델"""
    status: str
    timestamp: str
    service: str


@router.get("/health")
async def health_check():
    """
    서비스 상태 확인 엔드포인트
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        service="now_what_be"
    )


@router.get("/")
async def root():
    """
    루트 엔드포인트
    """
    return {
        "message": "Welcome to Now What Backend API",
        "version": "1.0.0",
        "docs": "/docs"
    }
```

### 6. main.py

FastAPI 애플리케이션 진입점:

```python
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
```

### 7. __init__.py 파일들

모든 패키지 디렉토리에 빈 `__init__.py` 파일 생성:
- `app/__init__.py`
- `app/agents/__init__.py`
- `app/routers/__init__.py`

### 8. .env.example

```env
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=True
```

## 핵심 요구사항

### 1. LangGraph를 이용한 AI Agent
- `StateGraph`를 사용한 워크플로우 구성
- 노드 기반 처리 파이프라인
- 비동기 처리 지원

### 2. FastAPI POST 예제
- `/api/v1/agent/chat` - AI Agent와 대화
- `/api/v1/agent/analyze` - 텍스트 분석
- Pydantic 모델을 사용한 요청/응답 검증

### 3. 라우팅 구조
- 모듈화된 라우터 구조 (`app/routers/`)
- 각 라우터는 독립적인 모듈로 관리
- `main.py`에서 통합 등록

### 4. 기본 필수 항목
- 환경 변수 관리 (Pydantic Settings)
- CORS 설정
- Health check 엔드포인트
- 에러 핸들링
- API 문서 자동 생성 (Swagger UI)

## 실행 방법

1. 가상환경 생성 및 활성화:
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate  # Windows
```

2. 패키지 설치:
```bash
pip install -r requirements.txt
```

3. 환경 변수 설정:
`.env` 파일을 생성하고 `OPENAI_API_KEY`를 설정

4. 서버 실행:
```bash
python main.py
```

## API 엔드포인트

### POST /api/v1/agent/chat
AI Agent와 대화하는 엔드포인트

**Request Body:**
```json
{
  "query": "안녕하세요",
  "max_length": 500
}
```

**Response:**
```json
{
  "response": "안녕하세요! 무엇을 도와드릴까요?",
  "query": "안녕하세요",
  "success": true
}
```

### POST /api/v1/agent/analyze
텍스트 분석 엔드포인트

**Request Body:**
```json
{
  "query": "분석할 텍스트"
}
```

### GET /health
서비스 상태 확인

### GET /
루트 엔드포인트

## 참고사항

- 모든 라우터는 `app/routers/` 디렉토리에 모듈화되어 있음
- Agent는 `app/agents/agent.py`에 싱글톤 패턴으로 구현
- 설정은 `app/config.py`에서 중앙 관리
- CORS는 브라우저 기반 클라이언트를 위해 설정 (Postman은 영향 없음)

