"""오케스트레이션 라우터

여러 Agent 작업을 조율하고 워크플로우를 관리하는 중앙 라우터
"""

from fastapi import APIRouter, HTTPException
from langgraph.graph import StateGraph, END
import logging

from app.schemas.orchestration_models import UserRequest, OrchestrationResponse
from app.schemas.workflow_state import WorkflowState
from app.nodes.workflow_nodes import receive_user_input_node

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/orchestration", tags=["orchestration"])


# LangGraph 워크플로우 그래프 구성
def create_workflow_graph() -> StateGraph:
    """워크플로우 그래프 생성"""
    workflow = StateGraph(WorkflowState)
    
    # 노드 추가
    workflow.add_node("receiveUserInput", receive_user_input_node)
    
    # 엔트리 포인트 설정
    workflow.set_entry_point("receiveUserInput")
    
    # 엔드 포인트 연결
    workflow.add_edge("receiveUserInput", END)
    
    return workflow.compile()


# 워크플로우 그래프 인스턴스 생성
workflow_graph = create_workflow_graph()


@router.post("/search", response_model=OrchestrationResponse)
async def orchestrate_search(request: UserRequest):
    """맛집 검색 오케스트레이션 엔드포인트
    
    사용자 입력과 위치 좌표를 받아 워크플로우를 실행합니다.
    
    Args:
        request: 사용자 요청 (쿼리 + 위치 좌표)
        
    Returns:
        OrchestrationResponse: 검색 결과
    """
    try:
        # 워크플로우 초기 상태 구성
        initial_state: WorkflowState = {
            "user_query": request.query,
            "user_location": request.location.model_dump() if request.location else None,
            "steps": [],  # 스텝 기록 초기화
        }
        
        # 워크플로우 실행
        result_state = await workflow_graph.ainvoke(initial_state)
        
        # 응답 생성
        return OrchestrationResponse(
            result_dict={
                "message": "워크플로우 실행 완료",
                "user_query": result_state.get("user_query"),
                "user_location": result_state.get("user_location"),
                "steps": result_state.get("steps", []),  # 스텝별 처리 결과 포함
                "total_steps": len(result_state.get("steps", [])),
            },
            query=result_state.get("user_query", ""),
            success=True,
        )
        
    except Exception as e:
        logger.error(f"워크플로우 실행 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"워크플로우 실행 중 오류가 발생했습니다: {str(e)}")
