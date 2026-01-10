"""ReAct Agent 라우터"""

import time
import logging
from fastapi import APIRouter, HTTPException
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

from app.schemas.orchestration_models import UserRequest
from app.schemas.agent_state import AgentState
from app.nodes.agent_node import agent_node, tool_node, should_continue

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


def create_agent_graph() -> StateGraph:
    """ReAct Agent 워크플로우 그래프 생성"""
    
    workflow = StateGraph(AgentState)
    
    # 노드 추가 (단 2개!)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    
    # 엔트리 포인트
    workflow.set_entry_point("agent")
    
    # 조건부 엣지: agent → tools or END
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )
    
    # tools → agent (순환)
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()


# Agent 그래프 인스턴스
agent_graph = create_agent_graph()


@router.post("/search")
async def agent_search(request: UserRequest):
    """
    ReAct Agent 맛집 검색 엔드포인트
    
    AI가 자율적으로 도구를 선택하고 실행합니다.
    
    Args:
        request: 사용자 요청 (쿼리 + 위치 좌표)
        
    Returns:
        Agent 실행 결과
    """
    try:
        logger.info("=" * 80)
        logger.info("🚀 ReAct Agent 시작")
        logger.info("=" * 80)
        
        # 초기 상태 구성
        initial_state: AgentState = {
            "messages": [],
            "user_query": request.query,
            "user_location": request.location.model_dump() if request.location else None,
            "places": [],
            "blog_links": {},
            "blog_contents": {},
            "analysis_results": {},
            "tool_call_count": 0,
            "start_time": time.time(),
            "done": False,
            "final_result": None
        }
        
        # Agent 실행
        logger.info(f"사용자 요청: {request.query}")
        result_state = await agent_graph.ainvoke(initial_state)
        
        # 결과 추출
        elapsed = time.time() - result_state.get("start_time", time.time())
        tool_count = result_state.get("tool_call_count", 0)
        
        logger.info("=" * 80)
        logger.info(f"✅ Agent 완료: {elapsed:.1f}초, {tool_count}회 도구 호출")
        logger.info("=" * 80)
        
        # 메시지 히스토리 정리
        messages = result_state.get("messages", [])
        message_summary = []
        for msg in messages:
            msg_type = msg.type if hasattr(msg, 'type') else type(msg).__name__
            content = msg.content[:100] if hasattr(msg, 'content') and msg.content else "(도구 호출)"
            message_summary.append({
                "type": msg_type,
                "content": content
            })
        
        return {
            "success": True,
            "query": request.query,
            "elapsed_time": f"{elapsed:.1f}초",
            "tool_call_count": tool_count,
            "messages": message_summary,
            "final_result": result_state.get("final_result"),
            "places": result_state.get("places"),
            "done": result_state.get("done", False)
        }
        
    except Exception as e:
        logger.error(f"❌ Agent 실행 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent 실행 중 오류 발생: {str(e)}")
