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
    
    # 쿼리 분석 결과
    is_relevant: bool  # 맛집 검색과 관련된 질문인지 여부
    location_keyword: Optional[str]  # 추출된 위치 키워드
    food_keyword: Optional[str]  # 추출된 음식/카테고리 키워드
    resolved_location: Optional[str]  # 좌표로부터 조회한 위치 키워드
    reverse_geocode_result: Optional[Dict[str, Any]]  # 역지오코딩 전체 결과 (주소 정보 포함)
    search_query: Optional[str]  # 최종 검색용 쿼리
    
    # 워크플로우 실행 스텝 기록
    steps: List[Dict[str, Any]]  # 각 노드의 처리 결과를 스텝별로 기록
