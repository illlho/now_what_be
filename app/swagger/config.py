"""Swagger UI 설정 및 커스터마이징"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html


# OpenAPI 태그 메타데이터 정의
TAGS_METADATA = [
    {
        "name": "health",
        "description": "서비스 상태 확인 및 헬스 체크 엔드포인트",
    },
    {
        "name": "agent",
        "description": "LangGraph를 활용한 AI Agent 관련 엔드포인트. AI 대화 및 텍스트 분석 기능을 제공합니다.",
    },
    {
        "name": "orchestration",
        "description": "여러 Agent 작업을 조율하고 워크플로우를 관리하는 오케스트레이션 엔드포인트. 순차/병렬 작업 실행, 배치 처리 등을 지원합니다.",
    },
]

# 서버 정보 설정
SERVERS = [
    {
        "url": "http://localhost:8000",
        "description": "로컬 개발 서버"
    },
    {
        "url": "http://127.0.0.1:8000",
        "description": "로컬 개발 서버 (127.0.0.1)"
    },
    {
        "url": "https://api.example.com",
        "description": "프로덕션 서버 (예시)"
    },
]

# Swagger UI 파라미터 설정
SWAGGER_UI_PARAMETERS = {
    "defaultModelsExpandDepth": 1,
    "defaultModelExpandDepth": 1,
    "docExpansion": "list",  # "none", "list", "full"
    "filter": True,
    "showExtensions": True,
    "showCommonExtensions": True,
    "tryItOutEnabled": True,
    "syntaxHighlight": {
        "activate": True,
        "theme": "agate"
    },
    "displayRequestDuration": True,
    "requestSnippetsEnabled": True,
    "requestSnippets": {
        "generators": {
            "curl_bash": {
                "title": "cURL (bash)"
            },
            "curl_powershell": {
                "title": "cURL (PowerShell)"
            },
            "curl_cmd": {
                "title": "cURL (CMD)"
            }
        }
    }
}

# 커스텀 CSS 스타일
CUSTOM_CSS = """
<style>
/* Swagger UI 컴팩트 스타일 */
.swagger-ui {
    font-size: 14px;
}

/* 헤더 영역 컴팩트 */
.swagger-ui .topbar {
    padding: 10px 0;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.swagger-ui .topbar-wrapper img {
    max-height: 40px;
}

/* 정보 섹션 컴팩트 */
.swagger-ui .info {
    margin: 20px 0;
}

.swagger-ui .info .title {
    font-size: 28px;
    margin-bottom: 10px;
    color: #3b4151;
}

.swagger-ui .info .description {
    font-size: 14px;
    line-height: 1.6;
    margin-bottom: 15px;
}

/* 서버 선택 컴팩트 */
.swagger-ui .scheme-container {
    margin: 15px 0;
    padding: 10px;
    background: #f7f7f7;
    border-radius: 4px;
}

/* 태그 컴팩트 */
.swagger-ui .opblock-tag {
    font-size: 16px;
    padding: 8px 15px;
    margin: 5px 0;
    border-radius: 4px;
    background: #fafafa;
    border-left: 4px solid #667eea;
}

.swagger-ui .opblock-tag:hover {
    background: #f0f0f0;
}

/* 엔드포인트 컴팩트 */
.swagger-ui .opblock {
    margin: 8px 0;
    border-radius: 4px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

.swagger-ui .opblock.opblock-post {
    border-color: #49cc90;
    background: rgba(73, 204, 144, 0.1);
}

.swagger-ui .opblock.opblock-get {
    border-color: #61affe;
    background: rgba(97, 175, 254, 0.1);
}

.swagger-ui .opblock-summary {
    padding: 10px 15px;
}

.swagger-ui .opblock-summary-method {
    font-size: 12px;
    padding: 4px 8px;
    min-width: 60px;
    text-align: center;
}

.swagger-ui .opblock-summary-path {
    font-size: 14px;
    font-weight: 600;
}

/* 파라미터 섹션 컴팩트 */
.swagger-ui .parameters-container {
    padding: 15px;
}

.swagger-ui .parameter__name {
    font-size: 13px;
    font-weight: 600;
}

.swagger-ui .parameter__type {
    font-size: 12px;
}

/* 응답 섹션 컴팩트 */
.swagger-ui .response-col_status {
    font-size: 13px;
}

.swagger-ui .response-col_description {
    font-size: 13px;
}

/* 코드 블록 컴팩트 */
.swagger-ui .highlight-code {
    font-size: 12px;
    line-height: 1.4;
}

/* Try it out 버튼 스타일 */
.swagger-ui .btn.try-out__btn {
    background: #667eea;
    border-color: #667eea;
    color: white;
    padding: 6px 12px;
    font-size: 12px;
}

.swagger-ui .btn.try-out__btn:hover {
    background: #5568d3;
    border-color: #5568d3;
}

/* Execute 버튼 스타일 */
.swagger-ui .btn.execute {
    background: #49cc90;
    border-color: #49cc90;
}

.swagger-ui .btn.execute:hover {
    background: #3fb883;
    border-color: #3fb883;
}

/* 스크롤바 스타일 */
.swagger-ui ::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

.swagger-ui ::-webkit-scrollbar-track {
    background: #f1f1f1;
}

.swagger-ui ::-webkit-scrollbar-thumb {
    background: #888;
    border-radius: 4px;
}

.swagger-ui ::-webkit-scrollbar-thumb:hover {
    background: #555;
}

/* 모델 스키마 컴팩트 */
.swagger-ui .model-box {
    font-size: 12px;
}

.swagger-ui .model-title {
    font-size: 14px;
}

/* 필터 입력 컴팩트 */
.swagger-ui .filter-container {
    padding: 10px 0;
}

.swagger-ui .filter-container input {
    padding: 6px 10px;
    font-size: 13px;
    border-radius: 4px;
}
</style>
"""


def custom_openapi(app: FastAPI):
    """OpenAPI 스키마 커스터마이징"""
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
        servers=app.servers,
    )
    
    # Swagger UI 설정 추가
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png",
        "altText": "Now What API"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def custom_swagger_ui_html(app: FastAPI):
    """커스터마이징된 Swagger UI HTML 생성"""
    html_response = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        swagger_ui_parameters=SWAGGER_UI_PARAMETERS,
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
    )
    
    # HTML에 CSS 삽입
    html_content = html_response.body.decode() if isinstance(html_response.body, bytes) else html_response.body
    modified_html = html_content.replace('</head>', CUSTOM_CSS + '</head>')
    
    return HTMLResponse(content=modified_html)

