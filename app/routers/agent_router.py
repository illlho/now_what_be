from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.agents.agent import agent
from app.exceptions import ValidationError

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


class AgentRequest(BaseModel):
    """Agent 요청 모델"""
    query: str = Field(..., min_length=1, description="사용자 질문 또는 요청")
    max_length: int = Field(default=500, ge=1, le=5000, description="최대 응답 길이")


class AgentResponse(BaseModel):
    """Agent 응답 모델"""
    response: str
    query: str
    success: bool = True


@router.post("/chat", response_model=AgentResponse)
async def chat_with_agent(request: AgentRequest):
    """
    AI Agent와 대화하는 엔드포인트
    
    - **query**: 사용자 질문 또는 요청 (필수, 최소 1자)
    - **max_length**: 최대 응답 길이 (기본값: 500, 최대: 5000)
    """
    # Agent 실행 (에러는 전역 핸들러에서 처리)
    response_text = await agent.process(request.query)
    
    # 응답 길이 제한
    if len(response_text) > request.max_length:
        response_text = response_text[:request.max_length] + "..."
    
    return AgentResponse(
        response=response_text,
        query=request.query,
        success=True
    )


@router.post("/analyze", response_model=AgentResponse)
async def analyze_text(request: AgentRequest):
    """
    텍스트 분석을 위한 엔드포인트
    
    - **query**: 분석할 텍스트 (필수, 최소 1자)
    """
    analysis_query = f"다음 텍스트를 분석해주세요: {request.query}"
    response_text = await agent.process(analysis_query)
    
    return AgentResponse(
        response=response_text,
        query=request.query,
        success=True
    )

