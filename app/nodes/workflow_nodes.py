"""워크플로우 노드 함수들

LangGraph 워크플로우에서 사용되는 노드 함수들을 정의합니다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import logging
from app.utils.llm_utils import evaluate_user_input

# 순환 import 방지를 위한 TYPE_CHECKING 사용
if TYPE_CHECKING:
    from app.routers.orchestration_router import WorkflowState

logger = logging.getLogger(__name__)


# 노드 함수: 쿼리 평가
async def evaluate_query_node(state: WorkflowState) -> WorkflowState:
    user_query = state.get("user_query", "")
    
    logger.info(f"쿼리 평가 노드 실행: {user_query}")
    
    result_dict = await evaluate_user_input(user_query)
    logger.info(f"쿼리 평가 완료: {result_dict}")
    
    # 상태 업데이트
    state["current_step"] = "evaluate_query"
    state["result_dict"] = result_dict
    state["metadata"] = {
        "step": "evaluate_query",
        "status": "completed"
    }
    
    return state

