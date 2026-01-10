"""ReAct Agent 상태 정의"""

from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """ReAct Agent 상태
    
    messages: LangChain 메시지 리스트 (Agent ↔ Tools 대화)
    user_query: 사용자 원본 요청
    user_location: 사용자 위치 좌표 {latitude, longitude}
    
    # 수집 데이터
    places: 검색된 장소 목록
    blog_links: {place_name: [blog_urls]}
    blog_contents: {blog_url: content}
    analysis_results: {place_name: analysis_dict}
    
    # 실행 제어
    tool_call_count: 도구 호출 횟수
    start_time: 시작 시간 (타임스탬프)
    done: 완료 여부
    
    # 최종 결과
    final_result: 최종 결과 딕셔너리
    """
    
    # 대화 메시지 (LangChain 표준)
    messages: Annotated[List, add_messages]
    
    # 사용자 요청 정보
    user_query: str
    user_location: Optional[Dict[str, float]]  # {latitude: float, longitude: float}
    
    # Agent 수집 데이터
    places: List[Dict[str, Any]]
    blog_links: Dict[str, List[str]]
    blog_contents: Dict[str, str]
    analysis_results: Dict[str, Dict[str, Any]]
    
    # 실행 제어
    tool_call_count: int
    start_time: float
    done: bool
    
    # 최종 결과
    final_result: Optional[Dict[str, Any]]
