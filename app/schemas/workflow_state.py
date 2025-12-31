"""워크플로우 상태 정의

LangGraph 워크플로우에서 사용되는 상태 타입을 정의합니다.
"""

from typing import TypedDict


class WorkflowState(TypedDict):
    """워크플로우 상태 정의"""
    queries: list[str]  # 쿼리 리스트 (0번: 최초 사용자 입력, 이후: rewrite된 쿼리들)
    steps: list[str]  # 거쳐간 단계 리스트 (병렬 처리 시 여러 단계 저장)
    result_dict: dict  # 최종 결과 (dict 형태)
    metadata: dict  # 추가 메타데이터
    token_usage_list: list[dict]  # 각 노드별 토큰 사용량 리스트
    token_usage_total: dict  # 누적 토큰 사용량 및 비용 (total_input_tokens, total_output_tokens, total_tokens, total_cost_krw, total_cost_formatted)

