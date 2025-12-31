"""워크플로우 상태 정의

LangGraph 워크플로우에서 사용되는 상태 타입을 정의합니다.
"""

from typing import TypedDict


class WorkflowState(TypedDict):
    """워크플로우 상태 정의"""
    user_query: str  # 사용자 쿼리
    current_step: str  # 현재 실행 중인 단계
    result_dict: dict  # 최종 결과 (dict 형태)
    metadata: dict  # 추가 메타데이터

