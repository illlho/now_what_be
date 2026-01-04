"""오케스트레이션 라우터

여러 Agent 작업을 조율하고 워크플로우를 관리하는 중앙 라우터
"""

from fastapi import APIRouter, HTTPException
from langgraph.graph import StateGraph, END
import logging

from app.schemas.orchestration_models import UserRequest, OrchestrationResponse
from app.schemas.workflow_state import WorkflowState
from app.nodes.workflow_nodes import receive_user_input_node, analyze_user_query_node

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/orchestration", tags=["orchestration"])


# LangGraph 워크플로우 그래프 구성
def create_workflow_graph() -> StateGraph:
    """워크플로우 그래프 생성"""
    workflow = StateGraph(WorkflowState)
    
    # 노드 추가
    workflow.add_node("receiveUserInput", receive_user_input_node)
    workflow.add_node("analyzeUserQuery", analyze_user_query_node)
    
    # 엔트리 포인트 설정
    workflow.set_entry_point("receiveUserInput")
    
    # 엣지 연결
    workflow.add_edge("receiveUserInput", "analyzeUserQuery")
    
    # 조건부 엣지: 관련 없는 질문이면 종료
    def should_continue(state: WorkflowState) -> str:
        """워크플로우 계속 진행 여부 결정"""
        is_relevant = state.get("is_relevant", True)
        if not is_relevant:
            return "end"
        return "continue"
    
    workflow.add_conditional_edges(
        "analyzeUserQuery",
        should_continue,
        {
            "end": END,
            "continue": END  # TODO: 다음 노드로 연결 (현재는 종료)
        }
    )
    
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
        is_relevant = result_state.get("is_relevant", True)
        steps = result_state.get("steps", [])
        
        # 에러가 발생한 스텝이 있는지 확인
        has_error = any(step.get("status") == "error" for step in steps)
        error_message = None
        if has_error:
            # 마지막 에러 스텝의 에러 메시지 가져오기
            error_steps = [step for step in steps if step.get("status") == "error"]
            if error_steps:
                error_message = error_steps[-1].get("error") or error_steps[-1].get("message")
        
        # 메시지 결정
        if has_error:
            message = f"워크플로우 실행 중 오류 발생: {error_message}" if error_message else "워크플로우 실행 중 오류 발생"
        elif not is_relevant:
            message = "맛집 검색과 관련 없는 질문입니다"
        else:
            message = "워크플로우 실행 완료"
        
        result_dict = {
            "message": message,
            "user_query": result_state.get("user_query"),
            "user_location": result_state.get("user_location"),
            "is_relevant": is_relevant,
            "has_error": has_error,
            "steps": steps,  # 스텝별 처리 결과 포함
            "total_steps": len(steps),
        }
        
        # 관련 있는 질문이고 에러가 없는 경우 분석 결과 포함
        if is_relevant and not has_error:
            result_dict.update({
                "location_keyword": result_state.get("location_keyword"),
                "food_keyword": result_state.get("food_keyword"),
                "resolved_location": result_state.get("resolved_location"),
                "search_query": result_state.get("search_query"),
            })
        
        return OrchestrationResponse(
            result_dict=result_dict,
            query=result_state.get("user_query", ""),
            success=not has_error,  # 에러가 있으면 success=False
        )
        
    except Exception as e:
        logger.error(f"워크플로우 실행 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"워크플로우 실행 중 오류가 발생했습니다: {str(e)}")
