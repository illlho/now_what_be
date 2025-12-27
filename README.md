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
├── .env.example              # 환경 변수 예제
└── README.md
```

## 설치 및 실행

### 1. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate  # Windows
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env.example` 파일을 참고하여 `.env` 파일을 생성하고 OpenAI API 키를 설정하세요.

```bash
cp .env.example .env
# .env 파일을 열어 OPENAI_API_KEY를 설정
```

### 4. 서버 실행

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

