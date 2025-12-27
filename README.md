# Now What Backend API

LangGraph를 활용한 AI Agent 백엔드 서비스

## 프로젝트 구조

```
now_what_be/
├── app/
│   ├── __init__.py
│   ├── config.py              # 설정 관리
│   ├── agents/
│   │   ├── __init__.py
│   │   └── agent.py           # LangGraph Agent 구현
│   └── routers/
│       ├── __init__.py
│       ├── agent_router.py    # Agent 관련 라우터
│       └── health_router.py   # Health check 라우터
├── main.py                    # FastAPI 애플리케이션 진입점
├── requirements.txt           # Python 패키지 의존성
├── run_api_server.sh          # Conda 환경 자동 설정 및 서버 실행 스크립트
├── .env.example              # 환경 변수 예제
└── README.md
```

## 설치 및 실행

### 방법 1: 자동 스크립트 사용 (권장)

Conda를 사용한 자동 환경 설정 및 서버 실행:

```bash
./run_api_server.sh
```

이 스크립트는 다음을 자동으로 수행합니다:
- Conda 설치 확인
- 가상환경 존재 여부 확인
- 없으면 Python 3.10으로 가상환경 생성
- 있으면 가상환경 활성화
- LangGraph, LangChain 최신 버전 포함 패키지 설치
- API 서버 실행

### 방법 2: 수동 설정

#### 1. Conda 가상환경 생성 및 활성화

```bash
# Python 3.10 이상으로 가상환경 생성
conda create -n now_what_be_env python=3.10 -y
conda activate now_what_be_env
```

#### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

#### 3. 환경 변수 설정

`.env` 파일을 생성하고 필요한 환경 변수를 설정하세요.

```bash
# .env 파일 생성
touch .env
```

`.env` 파일 예시:
```env
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Log Level Configuration
# 가능한 값: DEBUG, INFO, WARNING, ERROR, CRITICAL
# 값이 없거나 유효하지 않으면 ERROR 레벨이 기본값으로 사용됩니다.
LOG_LEVEL=ERROR
```

**로그 레벨 설명:**
- `DEBUG`: 모든 로그 출력 (개발 환경)
- `INFO`: 정보성 로그 이상 출력 (기본 운영 환경)
- `WARNING`: 경고 로그 이상 출력
- `ERROR`: 에러 로그만 출력 (기본값, 값이 없을 때)
- `CRITICAL`: 치명적 에러만 출력

#### 4. 서버 실행

```bash
python main.py
```

또는 uvicorn을 직접 사용:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API 엔드포인트

### Health Check

- `GET /health` - 서비스 상태 확인
- `GET /` - 루트 엔드포인트

### Agent

- `POST /api/v1/agent/chat` - AI Agent와 대화
  - Request Body:
    ```json
    {
      "query": "안녕하세요",
      "max_length": 500
    }
    ```
  
- `POST /api/v1/agent/analyze` - 텍스트 분석
  - Request Body:
    ```json
    {
      "query": "분석할 텍스트"
    }
    ```

## API 문서

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 예제 요청

### cURL

```bash
# Chat 엔드포인트
curl -X POST "http://localhost:8000/api/v1/agent/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "파이썬에 대해 설명해주세요",
    "max_length": 500
  }'

# Analyze 엔드포인트
curl -X POST "http://localhost:8000/api/v1/agent/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "이 텍스트를 분석해주세요"
  }'
```

### Python

```python
import requests

url = "http://localhost:8000/api/v1/agent/chat"
payload = {
    "query": "안녕하세요",
    "max_length": 500
}

response = requests.post(url, json=payload)
print(response.json())
```

## 기술 스택

- **FastAPI**: 고성능 웹 프레임워크
- **LangGraph**: AI Agent 오케스트레이션
- **LangChain**: LLM 통합
- **OpenAI**: GPT 모델
- **Uvicorn**: ASGI 서버

## 개발

프로젝트는 모듈화된 구조로 설계되어 있어 새로운 라우터나 Agent를 쉽게 추가할 수 있습니다.

### 새로운 라우터 추가

1. `app/routers/` 디렉토리에 새 라우터 파일 생성
2. `main.py`에서 라우터 등록

### Agent 확장

`app/agents/agent.py`에서 LangGraph 그래프를 수정하여 Agent 동작을 커스터마이징할 수 있습니다.

