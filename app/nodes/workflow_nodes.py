"""워크플로우 노드 함수들

LangGraph 워크플로우에서 사용되는 노드 함수들을 정의합니다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import logging

# 순환 import 방지를 위한 TYPE_CHECKING 사용
if TYPE_CHECKING:
    from app.routers.orchestration_router import WorkflowState

logger = logging.getLogger(__name__)


# 노드 함수: 쿼리 평가
async def evaluate_query_node(state: WorkflowState) -> WorkflowState:
    """
    쿼리 평가 노드
    
    사용자 쿼리를 평가하고 초기 결과를 생성합니다.
    
    Args:
        state: 현재 워크플로우 상태
        
    Returns:
        수정된 워크플로우 상태
    """
    user_query = state.get("user_query", "")
    
    logger.info(f"쿼리 평가 노드 실행: {user_query}")
    
    
    
    # 상태 업데이트
    state["current_step"] = "evaluate_query"
    state["result"] = f"쿼리 평가 완료: {user_query}"
    state["metadata"] = {
        "step": "evaluate_query",
        "status": "completed"
    }
    
    return state

