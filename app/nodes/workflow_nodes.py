"""워크플로우 노드 함수들

LangGraph 워크플로우에서 사용되는 노드 함수들을 정의합니다.
"""

import logging
from datetime import datetime
from typing import Dict, Any
from app.schemas.workflow_state import WorkflowState

logger = logging.getLogger(__name__)


def _add_step(
    state: WorkflowState,
    step_id: str,
    step_name: str,
    status: str = "success",
    input_data: Dict[str, Any] = None,
    output_data: Dict[str, Any] = None,
    message: str = None,
    error: str = None
) -> WorkflowState:
    """
    워크플로우 상태에 스텝 정보를 추가하는 헬퍼 함수
    
    Args:
        state: 워크플로우 상태
        step_id: 스텝 식별자 (노드 이름)
        step_name: 스텝 이름 (한글 설명)
        status: 상태 ("success" 또는 "error")
        input_data: 입력 데이터
        output_data: 출력 데이터
        message: 처리 메시지
        error: 에러 메시지 (status가 "error"일 때)
        
    Returns:
        업데이트된 워크플로우 상태
    """
    # steps 리스트 초기화 (없으면)
    if "steps" not in state:
        state["steps"] = []
    
    step_info = {
        "step_id": step_id,
        "step_name": step_name,
        "status": status,
        "timestamp": datetime.now().isoformat(),
    }
    
    if input_data is not None:
        step_info["input"] = input_data
    
    if output_data is not None:
        step_info["output"] = output_data
    
    if message:
        step_info["message"] = message
    
    if error:
        step_info["error"] = error
    
    state["steps"].append(step_info)
    
    return state


async def receive_user_input_node(state: WorkflowState) -> WorkflowState:
    """
    사용자 입력 수신 노드 (첫 번째 노드)
    
    프론트엔드에서 전달된 사용자 입력과 위치 좌표를 로그로 출력합니다.
    
    Args:
        state: 워크플로우 상태
        
    Returns:
        업데이트된 워크플로우 상태
    """
    user_query = state.get("user_query", "")
    user_location = state.get("user_location")
    
    logger.info("=" * 60)
    logger.info("📥 사용자 입력 수신")
    logger.info("=" * 60)
    logger.info(f"사용자 입력: {user_query}")
    
    if user_location:
        latitude = user_location.get("latitude")
        longitude = user_location.get("longitude")
        logger.info(f"사용자 위치 좌표: 위도={latitude}, 경도={longitude}")
    else:
        logger.info("사용자 위치 좌표: 없음")
    
    logger.info("=" * 60)
    
    # 스텝 정보 기록
    state = _add_step(
        state=state,
        step_id="receiveUserInput",
        step_name="사용자 입력 수신",
        status="success",
        input_data={
            "query": user_query,
            "location": user_location
        },
        output_data={
            "query": user_query,
            "location_provided": user_location is not None
        },
        message=f"사용자 입력 '{user_query}' 수신 완료"
    )
    
    return state
