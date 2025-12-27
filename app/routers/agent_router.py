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

