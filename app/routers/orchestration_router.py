"""오케스트레이션 라우터

여러 Agent 작업을 조율하고 워크플로우를 관리하는 중앙 라우터
"""

from typing import Optional, TypedDict
from fastapi import APIRouter
from pydantic import BaseModel, Field
import logging
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=".env", override=True)

from langgraph.graph import StateGraph, END

# 노드 함수 import
from app.nodes.workflow_nodes import evaluate_query_node

# 유틸리티 함수 import
from app.utils.llm_utils import LLMRequest, llm_call

# 워크플로우 상태 정의
class WorkflowState(TypedDict):
    """워크플로우 상태 정의"""
    user_query: str  # 사용자 쿼리
    current_step: str  # 현재 실행 중인 단계
    result_dict: dict  # 최종 결과 (dict 형태)
    metadata: dict  # 추가 메타데이터

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/orchestration", tags=["orchestration"])

# 유저의 요청
class UserRequest(BaseModel):
    query: str = Field(..., min_length=1, description="유저가 요청한 내용")

# 오케스트레이션 응답
class OrchestrationResponse(BaseModel):
    result_dict: dict = Field(..., description="평가 결과 (dict 형태)")
    query: str
    success: bool = True

@router.post("/start-foodie-workflow", response_model=OrchestrationResponse, summary="맛집 탐색 워크플로우 시작")
async def start_foodie_workflow(request: UserRequest):
    try:
        # 그래프 생성
        graph = StateGraph(WorkflowState)
        
        # 노드 추가
        graph.add_node("workflow_start", evaluate_query_node)
        
        # 엔트리 포인트 설정
        graph.set_entry_point("workflow_start")

        # 엣지 추가
        graph.add_edge("workflow_start", END)

        # 그래프 컴파일
        compiled_graph = graph.compile()
        
        # 초기 상태 설정
        initial_state: WorkflowState = {
            "user_query": request.query,
            "current_step": "workflow_start",
            "result_dict": {},
            "metadata": {}
        }

        # 워크플로우 실행
        logger.info("워크플로우 실행 중...")
        result_state = await compiled_graph.ainvoke(initial_state)
        
        logger.info(f"워크플로우 결과: {result_state}")

        # 결과 추출
        final_result = result_state.get("result_dict", {})
        metadata = result_state.get("metadata", {})
        success = metadata.get("status") == "completed" if metadata else True
        
        logger.info(f"워크플로우 완료: 성공={success}, 결과 타입={type(final_result)}")
        
        return OrchestrationResponse(
            result_dict=final_result,
            query=request.query,
            success=success
        )
    except Exception as e:
        logger.error(f"워크플로우 실행 실패: {str(e)}", exc_info=True)
        
        return OrchestrationResponse(
            result_dict={"error": f"워크플로우 실행 중 오류 발생: {str(e)}"},
            query=request.query,
            success=False
        )