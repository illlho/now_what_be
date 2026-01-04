"""워크플로우 상태 정의

LangGraph 워크플로우에서 사용되는 상태 타입을 정의합니다.
"""

from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime


class WorkflowState(TypedDict, total=False):
    """워크플로우 상태 정의
    
    LangGraph 워크플로우에서 사용되는 상태 정보를 담는 TypedDict입니다.
    """
    # 사용자 입력
    user_query: str  # 사용자가 입력한 검색 쿼리
    user_location: Optional[dict]  # 사용자 위치 좌표 (latitude, longitude를 포함한 dict)
    
    # 워크플로우 실행 스텝 기록
    steps: List[Dict[str, Any]]  # 각 노드의 처리 결과를 스텝별로 기록
