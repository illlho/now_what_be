"""워크플로우 노드 함수들

LangGraph 워크플로우에서 사용되는 노드 함수들을 정의합니다.
"""

import logging
from datetime import datetime
from typing import Dict, Any
from app.schemas.workflow_state import WorkflowState
from app.schemas.llm_response_models import QueryAnalysisResult
from app.utils.llm_utils import llm_call, LLMRequest
from app.utils.geocoding import reverse_geocode

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


async def analyze_user_query_node(state: WorkflowState) -> WorkflowState:
    """
    사용자 쿼리 분석 노드 (AI 노드)
    
    사용자의 질문을 분석하여:
    1. 맛집 검색과 관련된 질문인지 확인
    2. 위치 키워드와 음식 키워드 추출
    3. 위치 키워드가 없거나 '근처'인 경우 좌표로 주소 조회
    4. 최종 검색 쿼리 생성
    
    Args:
        state: 워크플로우 상태
        
    Returns:
        업데이트된 워크플로우 상태
    """
    user_query = state.get("user_query", "")
    user_location = state.get("user_location")
    
    logger.info("=" * 60)
    logger.info("🤖 사용자 쿼리 분석 시작")
    logger.info("=" * 60)
    
    try:
        # LLM을 통한 쿼리 분석 (프롬프트 300자 미만)
        system_prompt = "맛집 검색 쿼리 분석 AI. 위치(동명, 역명, 지역명 포함)와 음식 키워드를 정확히 추출."
        
        user_prompt = f"""질문: "{user_query}"

[중요] 관대한 정책: 맛집/음식/장소 관련이면 무조건 통과. 위치/음식 키워드 없어도 진행.
완전 무관한 경우에만 is_relevant=false (예: 날씨, 주식, 뉴스).

위치 키워드 추출 예시:
- "가능동 삼겹살" → location_keyword="가능동", food_keyword="삼겹살", needs_location_resolution=false
- "강남역 파스타" → location_keyword="강남역", food_keyword="파스타", needs_location_resolution=false
- "홍대 맛집" → location_keyword="홍대", food_keyword=null, needs_location_resolution=false
- "근처 카페" → location_keyword=null, food_keyword="카페", needs_location_resolution=true
- "맛집 추천" → location_keyword=null, food_keyword=null, needs_location_resolution=true
- "주변 맛집" → location_keyword=null, food_keyword=null, needs_location_resolution=true

분석:
1. 맛집/음식/장소 관련이면 is_relevant=true (관대하게)
2. 위치 키워드 추출 (동명, 역명, 지역명 모두 포함)
3. 음식/카테고리 키워드 추출
4. 위치 키워드 없거나 '근처'/'주변'이면 needs_location_resolution=true

완전 무관 예시: "오늘 날씨 어때?", "주식 시세", "뉴스 보여줘" → is_relevant=false

reason은 50자 이내로 간결하게 작성하세요."""
        
        llm_request: LLMRequest = {
            "user_prompt": user_prompt,
            "system_prompt": system_prompt
        }
        
        analysis_result, token_info = await llm_call(llm_request, QueryAnalysisResult)
        
        logger.info(f"분석 결과: 관련성={analysis_result.is_relevant}, "
                   f"위치={analysis_result.location_keyword}, "
                   f"음식={analysis_result.food_keyword}, "
                   f"needs_location_resolution={analysis_result.needs_location_resolution}")
        
        # 상태 업데이트
        state["is_relevant"] = analysis_result.is_relevant
        state["location_keyword"] = analysis_result.location_keyword
        state["food_keyword"] = analysis_result.food_keyword
        
        # 관련 없는 질문이면 종료
        if not analysis_result.is_relevant:
            logger.info("맛집 검색과 관련 없는 질문으로 판단. 워크플로우 종료.")
            state = _add_step(
                state=state,
                step_id="analyzeUserQuery",
                step_name="사용자 쿼리 분석",
                status="success",
                input_data={"query": user_query},
                output_data={
                    "is_relevant": False,
                    "reason": analysis_result.reason
                },
                message=analysis_result.reason
            )
            return state
        
        # 위치 키워드가 없거나 '근처'인 경우 좌표로 주소 조회
        resolved_location = None
        reverse_geocode_result = None
        if analysis_result.needs_location_resolution and user_location:
            latitude = user_location.get("latitude")
            longitude = user_location.get("longitude")
            
            if latitude and longitude:
                logger.info(f"좌표로 주소 조회 시작: ({latitude}, {longitude})")
                try:
                    geocode_result = await reverse_geocode(latitude, longitude)
                    
                    if geocode_result:
                        resolved_location = geocode_result.get("location_keyword")
                        reverse_geocode_result = geocode_result  # 전체 역지오코딩 결과 저장
                        logger.info(f"✅ 조회된 위치 키워드: {resolved_location}")
                        state["resolved_location"] = resolved_location
                        state["reverse_geocode_result"] = reverse_geocode_result
                    else:
                        logger.warning(f"⚠️  역지오코딩 결과가 None입니다.")
                except Exception as e:
                    logger.error(f"❌ 역지오코딩 중 오류 발생: {str(e)}", exc_info=True)
            else:
                logger.warning("위도 또는 경도가 없습니다.")
        else:
            if not analysis_result.needs_location_resolution:
                logger.info("needs_location_resolution이 false이므로 역지오코딩을 건너뜁니다.")
            if not user_location:
                logger.info("user_location이 없어서 역지오코딩을 건너뜁니다.")
        
        # 최종 위치 키워드 결정
        final_location = analysis_result.location_keyword or resolved_location
        
        # 음식 키워드 기본값 설정 (없으면 "음식점")
        final_food = analysis_result.food_keyword or "음식점"
        
        # 검색 쿼리 생성
        search_query_parts = []
        if final_location:
            search_query_parts.append(final_location)
        search_query_parts.append(final_food)  # 음식 키워드는 항상 포함 (기본값 있음)
        
        search_query = " ".join(search_query_parts)
        state["search_query"] = search_query
        
        logger.info(f"최종 검색 쿼리: {search_query}")
        logger.info(f"  - 위치: {final_location or '(좌표 기반)'}")
        logger.info(f"  - 음식: {final_food}{' (기본값)' if not analysis_result.food_keyword else ''}")
        logger.info("=" * 60)
        
        # 스텝 정보 기록
        state = _add_step(
            state=state,
            step_id="analyzeUserQuery",
            step_name="사용자 쿼리 분석",
            status="success",
            input_data={
                "query": user_query,
                "user_location": user_location
            },
            output_data={
                "is_relevant": analysis_result.is_relevant,
                "location_keyword": analysis_result.location_keyword,
                "food_keyword": analysis_result.food_keyword,
                "needs_location_resolution": analysis_result.needs_location_resolution,
                "resolved_location": resolved_location,
                "reverse_geocode_result": reverse_geocode_result,
                "search_query": search_query,
                "reason": analysis_result.reason,
                "token_usage": {
                    "input_tokens": token_info.input_tokens,
                    "output_tokens": token_info.output_tokens,
                    "total_tokens": token_info.total_tokens,
                    "cost_formatted": token_info.cost_formatted
                }
            },
            message=analysis_result.reason
        )
        
        return state
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"쿼리 분석 실패: {error_message}", exc_info=True)
        
        # API 키 관련 에러인지 확인
        is_api_key_error = "api_key" in error_message.lower() or "OPENAI_API_KEY" in error_message
        
        if is_api_key_error:
            error_message = "OpenAI API 키가 설정되지 않았습니다. .env 파일에 OPENAI_API_KEY를 설정해주세요."
            logger.error(error_message)
        
        state = _add_step(
            state=state,
            step_id="analyzeUserQuery",
            step_name="사용자 쿼리 분석",
            status="error",
            input_data={"query": user_query},
            error=error_message,
            message=f"쿼리 분석 실패: {error_message}"
        )
        # 에러 발생 시 관련 없는 것으로 처리하여 종료
        state["is_relevant"] = False
        return state
