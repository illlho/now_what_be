"""워크플로우 노드 함수들

LangGraph 워크플로우에서 사용되는 노드 함수들을 정의합니다.
"""

from __future__ import annotations

import asyncio
import logging
from app.utils.llm_utils import llm_call, LLMRequest, TokenUsageInfo, calculate_cost
from app.schemas.workflow_state import WorkflowState
from app.schemas.llm_response_models import QueryEvaluationResult, QueryRewriteResult

logger = logging.getLogger(__name__)


def _update_token_usage(state: WorkflowState, step_name: str, token_info: TokenUsageInfo) -> None:
    """
    WorkflowState의 토큰 사용량 리스트와 누적 값을 업데이트합니다.
    
    Args:
        state: 워크플로우 상태
        step_name: 현재 단계 이름
        token_info: 토큰 사용량 정보
    """
    # token_usage_list 초기화 (없으면)
    if "token_usage_list" not in state:
        state["token_usage_list"] = []
    
    # 현재 노드의 토큰 사용량을 리스트에 추가
    state["token_usage_list"].append({
        "step": step_name,
        "input_tokens": token_info.input_tokens,
        "output_tokens": token_info.output_tokens,
        "total_tokens": token_info.total_tokens,
        "cost_krw": token_info.cost_krw,
        "cost_formatted": token_info.cost_formatted
    })
    
    # token_usage_total 초기화 (없으면)
    if "token_usage_total" not in state:
        state["token_usage_total"] = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "total_cost_krw": 0.0,
            "total_cost_formatted": "0.00원(0 tokens)"
        }
    
    # 누적 값 업데이트
    total = state["token_usage_total"]
    total["total_input_tokens"] += token_info.input_tokens
    total["total_output_tokens"] += token_info.output_tokens
    total["total_tokens"] += token_info.total_tokens
    total["total_cost_krw"] += token_info.cost_krw
    
    # 총 비용 포맷팅
    total_cost_krw, total_cost_formatted = calculate_cost(
        total["total_input_tokens"],
        total["total_output_tokens"]
    )
    total["total_cost_krw"] = total_cost_krw
    total["total_cost_formatted"] = total_cost_formatted


# 노드 함수: 쿼리 평가
async def evaluate_query_node(state: WorkflowState) -> WorkflowState:
    """
    쿼리 평가 노드
    
    사용자 입력이 맛집 검색 서비스에 적합한지 판단합니다.
    - 적합한 경우: 다음 노드(rewrite_query_and_extract_keywords)로 진행
    - 부적절하거나 정보 부족한 경우: END로 이동하여 사용자에게 이유와 함께 반환
    
    이후 플로우:
    - valid → rewrite_query_and_extract_keywords → hybrid_search → ...
    - invalid → END (사용자에게 부족한 정보와 이유 반환)
    """
    # queries 리스트에서 최초 사용자 입력 가져오기 (0번 인덱스)
    queries = state.get("queries", [])
    if not queries:
        logger.error("queries가 비어있습니다. 최소한 하나의 쿼리가 필요합니다.")
        state["steps"] = state.get("steps", []) + ["evaluate_query"]
        state["result_dict"] = {
            "is_valid": False,
            "is_inappropriate": False,
            "missing_info": ["시스템 오류"],
            "reasoning": "queries가 비어있습니다."
        }
        return state
    
    user_query = queries[0]  # 최초 사용자 입력
    
    logger.info(f"쿼리 평가 노드 실행: {user_query}")
    
    # 시스템 프롬프트 (300자 이내 요약)
    # 역할: 맛집 검색 서비스 적합성 판단 및 필수 정보 확인
    system_prompt = """맛집 검색 쿼리 평가 전문 AI. 사용자 입력이 맛집 검색 서비스에 적합한지 판단: 1)맛집 관련성 체크(맛집/음식/식당 관련인지) 2)부적절성 검사(욕설/무관한 질문인지) 3)필수 정보 확인(위치/음식종류 존재 여부). 정보 부족시 부족한 항목과 이유 명시. JSON 응답: is_valid(다음 단계 진행 가능 여부), is_inappropriate(부적절 여부), missing_info(부족한 정보 리스트, 예:["위치","음식종류"]), location(있으면 추출), search_item(있으면 추출), reasoning(판단 이유). is_inappropriate=true면 is_valid=false."""
    
    # 사용자 프롬프트
    user_prompt = f'다음 사용자 입력을 평가하고 JSON 형식으로 응답하세요:\n\n사용자 입력: "{user_query}"\n\n맛집 검색에 적합한지, 필요한 정보(위치, 음식 종류)가 충분한지 판단하세요. 부족하면 missing_info에 부족한 항목을 리스트로 명시하세요.'
    
    # LLM 호출 (with_structured_output 사용)
    llm_request: LLMRequest = {
        "user_prompt": user_prompt,
        "system_prompt": system_prompt
    }
    
    try:
        # Pydantic 모델로 구조화된 응답 받기 (토큰 정보 포함)
        result, token_info = await llm_call(llm_request, QueryEvaluationResult)
        logger.info(
            f"쿼리 평가 완료: is_valid={result.is_valid}, missing_info={result.missing_info} | "
            f"비용: {token_info.cost_formatted}"
        )
        
        # is_valid와 is_inappropriate 일관성 확인
        if result.is_inappropriate:
            result.is_valid = False
        
        # Pydantic 모델을 dict로 변환하여 state에 저장
        result_dict = result.model_dump()
        
        # 토큰 사용량 업데이트
        _update_token_usage(state, "evaluate_query", token_info)
        
        # 상태 업데이트
        steps = state.get("steps", [])
        state["steps"] = steps + ["evaluate_query"]
        state["result_dict"] = result_dict
        state["metadata"] = {
            "step": "evaluate_query",
            "status": "completed"
        }
    except Exception as e:
        logger.error(f"쿼리 평가 실패: {str(e)}", exc_info=True)
        # 에러 발생 시 기본값 설정 (invalid로 처리)
        steps = state.get("steps", [])
        state["steps"] = steps + ["evaluate_query"]
        state["result_dict"] = {
            "is_valid": False,
            "is_inappropriate": False,
            "missing_info": ["시스템 오류"],
            "location": None,
            "search_item": None,
            "reasoning": f"쿼리 평가 중 오류 발생: {str(e)}"
        }
        state["metadata"] = {
            "step": "evaluate_query",
            "status": "error"
        }
    
    return state


# ============================================================================
# 노드 함수들
# ============================================================================

async def rewrite_query_and_extract_keywords_node(state: WorkflowState) -> WorkflowState:
    """
    쿼리 재작성 및 키워드 추출 노드
    
    사용자 쿼리를 검색에 최적화된 형태로 재작성하고, 위치, 음식 종류, 키워드를 추출합니다.
    """
    # queries 리스트에서 마지막 쿼리 가져오기 (없으면 result_dict에서)
    queries = state.get("queries", [])
    if queries:
        original_query = queries[-1]  # 마지막 쿼리 사용
    else:
        # queries가 없으면 result_dict에서 가져오기 시도
        result_dict = state.get("result_dict", {})
        original_query = result_dict.get("rewritten_query") or state.get("queries", [""])[0] if state.get("queries") else ""
    
    if not original_query:
        logger.error("재작성할 쿼리가 없습니다.")
        steps = state.get("steps", [])
        state["steps"] = steps + ["rewrite_query_and_extract_keywords"]
        state["result_dict"] = {
            "error": "재작성할 쿼리가 없습니다."
        }
        return state
    
    logger.info(f"쿼리 재작성 및 키워드 추출 노드 실행: {original_query}")
    
    # 시스템 프롬프트 (300자 이내)
    system_prompt = """맛집 검색 쿼리 재작성 전문 AI. 사용자 쿼리를 검색에 최적화: 1)불필요한 수식어 제거("맛있는","좋은" 등) 2)핵심 키워드 추출(위치, 음식종류) 3)검색 최적화된 간결한 쿼리 생성. JSON 응답: rewritten_query(재작성된 쿼리), location(위치), food_type(음식종류), keywords(키워드 리스트), reasoning(재작성 이유)."""
    
    # 사용자 프롬프트
    user_prompt = f'다음 쿼리를 검색에 최적화된 형태로 재작성하고 키워드를 추출하세요:\n\n원본 쿼리: "{original_query}"\n\n불필요한 수식어를 제거하고, 위치와 음식 종류를 명확히 추출하여 검색에 최적화된 쿼리로 재작성하세요.'
    
    # LLM 호출
    llm_request: LLMRequest = {
        "user_prompt": user_prompt,
        "system_prompt": system_prompt
    }
    
    try:
        # Pydantic 모델로 구조화된 응답 받기
        result, token_info = await llm_call(llm_request, QueryRewriteResult)
        logger.info(
            f"쿼리 재작성 완료: rewritten_query={result.rewritten_query} | "
            f"비용: {token_info.cost_formatted}"
        )
        
        # 토큰 사용량 업데이트
        _update_token_usage(state, "rewrite_query_and_extract_keywords", token_info)
        
        # 재작성된 쿼리를 queries 리스트에 추가
        queries = state.get("queries", [])
        state["queries"] = queries + [result.rewritten_query]
        
        # Pydantic 모델을 dict로 변환하여 state에 저장
        result_dict = result.model_dump()
        
        # 기존 result_dict와 병합 (기존 정보 유지)
        existing_result_dict = state.get("result_dict", {})
        existing_result_dict.update(result_dict)
        
        # 상태 업데이트
        steps = state.get("steps", [])
        state["steps"] = steps + ["rewrite_query_and_extract_keywords"]
        state["result_dict"] = existing_result_dict
        state["metadata"] = {
            "step": "rewrite_query_and_extract_keywords",
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"쿼리 재작성 실패: {str(e)}", exc_info=True)
        # 에러 발생 시 원본 쿼리 사용
        steps = state.get("steps", [])
        state["steps"] = steps + ["rewrite_query_and_extract_keywords"]
        state["result_dict"] = {
            "error": f"쿼리 재작성 중 오류 발생: {str(e)}",
            "rewritten_query": original_query,  # 원본 쿼리 사용
            "location": None,
            "food_type": None,
            "keywords": []
        }
        state["metadata"] = {
            "step": "rewrite_query_and_extract_keywords",
            "status": "error"
        }
    
    return state


async def hybrid_search_node(state: WorkflowState) -> WorkflowState:
    """
    하이브리드 검색 노드
    
    현재는 검색 결과가 부족한 상태로 설정하여, 검색 결과 평가에서 'invalid'가 반환되도록 합니다.
    추후 VectorDB 및 검색 엔진 연동 시 실제 검색 로직을 구현합니다.
    """
    logger.info("하이브리드 검색 노드 실행")
    
    # 검색 결과를 빈 상태로 저장 (invalid 반환을 위해)
    # 추후 실제 검색 로직 구현 시 이 부분을 교체
    result_dict = state.get("result_dict", {})
    result_dict["search_results"] = {
        "documents": [],  # 빈 문서 리스트
        "scores": [],
        "search_metadata": {
            "result_count": 0,
            "search_type": "hybrid",
            "status": "no_results"
        }
    }
    
    # 상태 업데이트
    steps = state.get("steps", [])
    state["steps"] = steps + ["hybrid_search"]
    state["result_dict"] = result_dict
    state["metadata"] = {
        "step": "hybrid_search",
        "status": "completed"
    }
    
    return state


async def evaluate_search_results_node(state: WorkflowState) -> WorkflowState:
    """
    검색 결과 평가 노드
    
    검색 결과를 평가하여 충분한지 판단합니다.
    현재는 하이브리드 검색 결과가 빈 상태이므로 항상 'invalid'로 평가됩니다.
    
    TODO : 
    구현 필요 사항:
    1. state에서 검색 결과 가져오기
    2. LLM을 사용하여 검색 결과 평가
       - 검색 결과가 원래 질문과 연관성이 있는지 평가
       - 문서 수가 충분한지 평가 (최소 문서 수 기준)
       - 검색 결과의 품질 평가
    3. 평가 결과를 구조화하여 저장
       - is_relevant: 연관성 여부
       - is_sufficient: 문서 수 충분 여부
       - quality_score: 품질 점수
       - reasoning: 평가 사고 과정
    4. state의 result_dict에 평가 결과 저장
    5. steps에 현재 단계 추가 및 metadata 업데이트
    """
    logger.info("검색 결과 평가 노드 실행")
    
    result_dict = state.get("result_dict", {})
    search_results = result_dict.get("search_results", {})
    documents = search_results.get("documents", [])
    result_count = search_results.get("search_metadata", {}).get("result_count", 0)
    
    # 검색 결과 평가 (현재는 빈 결과이므로 invalid로 설정)
    is_relevant = len(documents) > 0
    is_sufficient = result_count >= 3  # 최소 3개 이상의 문서 필요
    
    # 평가 결과 저장
    result_dict["search_evaluation"] = {
        "is_relevant": is_relevant,
        "is_sufficient": is_sufficient,
        "quality_score": 0.0 if not is_sufficient else 0.5,
        "reasoning": f"검색 결과: {result_count}개 문서. {'충분함' if is_sufficient else '부족함'}"
    }
    
    # 상태 업데이트
    steps = state.get("steps", [])
    state["steps"] = steps + ["evaluate_search_results"]
    state["result_dict"] = result_dict
    state["metadata"] = {
        "step": "evaluate_search_results",
        "status": "completed"
    }
    
    return state


async def generate_final_response_node(state: WorkflowState) -> WorkflowState:
    """
    최종 응답 생성 노드
    
    구현 필요 사항:
    1. state에서 모든 검색 결과와 평가 정보 가져오기
    2. LLM을 사용하여 최종 응답 생성
       - 검색된 문서들을 종합하여 답변 생성
       - 사용자 질문에 대한 명확하고 유용한 답변 제공
       - 맛집 정보, 위치, 추천 이유 등을 포함
    3. 생성된 응답을 구조화하여 저장
       - final_answer: 최종 답변 텍스트
       - restaurants: 추천 맛집 리스트 (있는 경우)
       - sources: 참고한 문서/소스 정보
    4. state의 result_dict에 최종 응답 저장
    5. steps에 현재 단계 추가 및 metadata 업데이트 (status: "completed")
    """
    logger.info("최종 응답 생성 노드 실행")
    # TODO: 구현 필요
    steps = state.get("steps", [])
    state["steps"] = steps + ["generate_final_response"]
    state["metadata"]["status"] = "completed"
    return state


async def parallel_search_node(state: WorkflowState) -> WorkflowState:
    """
    병렬 검색 노드 (네이버지도, 네이버블로그, 덕덕고 웹 검색)
    
    세 가지 검색 소스를 병렬로 검색하여 결과를 통합합니다.
    """
    logger.info("병렬 검색 노드 실행")
    
    # 검색 쿼리 가져오기 (queries 리스트의 마지막 쿼리 또는 result_dict에서)
    queries = state.get("queries", [])
    result_dict = state.get("result_dict", {})
    
    # 검색 쿼리 결정: queries의 마지막 쿼리 또는 result_dict의 rewritten_query
    search_queries = []
    if queries:
        # queries 리스트의 마지막 쿼리 사용
        search_queries = [queries[-1]]
    elif result_dict.get("rewritten_query"):
        search_queries = [result_dict["rewritten_query"]]
    else:
        logger.warning("검색할 쿼리가 없습니다.")
        steps = state.get("steps", [])
        state["steps"] = steps + ["parallel_search"]
        state["result_dict"] = {
            **result_dict,
            "parallel_search_results": {
                "naver_map_results": {"queries": [], "count": 0, "hits": []},
                "naver_blog_results": {"queries": [], "count": 0, "hits": []},
                "web_search_results": {"queries": [], "count": 0, "hits": []},
                "combined_results": []
            }
        }
        return state
    
    # 검색 함수 import
    from app.utils.search.naver_blog_search import search_naver_blog
    from app.utils.search.naver_map_search import search_naver_map
    from app.utils.search.duckduckgo_search import search_duckduckgo
    
    try:
        # 세 가지 검색 소스를 병렬로 실행
        naver_blog_task = search_naver_blog(search_queries)
        naver_map_task = search_naver_map(search_queries)
        duckduckgo_search_task = search_duckduckgo(search_queries)
        
        # 병렬 실행
        naver_blog_result, naver_map_result, duckduckgo_search_result = await asyncio.gather(
            naver_blog_task,
            naver_map_task,
            duckduckgo_search_task,
            return_exceptions=True
        )
        
        # 예외 처리
        if isinstance(naver_blog_result, Exception):
            logger.error(f"네이버 블로그 검색 실패: {str(naver_blog_result)}")
            naver_blog_result = {"queries": search_queries, "count": 0, "hits": []}
        
        if isinstance(naver_map_result, Exception):
            logger.error(f"네이버 지도 검색 실패: {str(naver_map_result)}")
            naver_map_result = {"queries": search_queries, "count": 0, "hits": []}
        
        if isinstance(duckduckgo_search_result, Exception):
            logger.error(f"DuckDuckGo 검색 실패: {str(duckduckgo_search_result)}")
            duckduckgo_search_result = {"queries": search_queries, "count": 0, "hits": []}
        
        # 검색 결과 통합
        combined_results = []
        
        # 네이버 지도 결과 추가
        if naver_map_result.get("hits"):
            combined_results.extend([
                {
                    "source": "naver_map",
                    "title": hit.get("title", ""),
                    "link": hit.get("link"),
                    "category": hit.get("category"),
                    "description": hit.get("description"),
                    "telephone": hit.get("telephone"),
                    "address": hit.get("address"),
                    "roadAddress": hit.get("roadAddress"),
                }
                for hit in naver_map_result["hits"]
            ])
        
        # 네이버 블로그 결과 추가
        if naver_blog_result.get("hits"):
            combined_results.extend([
                {
                    "source": "naver_blog",
                    "title": hit.get("title", ""),
                    "link": hit.get("link", ""),
                    "description": hit.get("description", ""),
                    "bloggername": hit.get("bloggername"),
                    "postdate": hit.get("postdate"),
                }
                for hit in naver_blog_result["hits"]
            ])
        
        # DuckDuckGo 검색 결과 추가
        if duckduckgo_search_result.get("hits"):
            combined_results.extend([
                {
                    "source": "duckduckgo",
                    **hit
                }
                for hit in duckduckgo_search_result["hits"]
            ])
        
        # 결과 저장
        result_dict["parallel_search_results"] = {
            "naver_map_results": naver_map_result,
            "naver_blog_results": naver_blog_result,
            "duckduckgo_search_results": duckduckgo_search_result,
            "combined_results": combined_results
        }
        
        logger.info(
            f"병렬 검색 완료: "
            f"지도={naver_map_result.get('count', 0)}개, "
            f"블로그={naver_blog_result.get('count', 0)}개, "
            f"DuckDuckGo={duckduckgo_search_result.get('count', 0)}개"
        )
        
    except Exception as e:
        logger.error(f"병렬 검색 실패: {str(e)}", exc_info=True)
        # 에러 발생 시 빈 결과 저장
        result_dict["parallel_search_results"] = {
            "naver_map_results": {"queries": search_queries, "count": 0, "hits": []},
            "naver_blog_results": {"queries": search_queries, "count": 0, "hits": []},
            "duckduckgo_search_results": {"queries": search_queries, "count": 0, "hits": []},
            "combined_results": [],
            "error": f"병렬 검색 중 오류 발생: {str(e)}"
        }
    
    # 상태 업데이트
    steps = state.get("steps", [])
    state["steps"] = steps + ["parallel_search"]
    state["result_dict"] = result_dict
    state["metadata"] = {
        "step": "parallel_search",
        "status": "completed"
    }
    
    return state


async def evaluate_relevance_node(state: WorkflowState) -> WorkflowState:
    """
    연관성 평가 노드
    
    구현 필요 사항:
    1. state에서 병렬 검색 결과 가져오기
    2. LLM을 사용하여 검색 결과와 쿼리의 연관성 평가
       - 각 검색 결과가 원래 질문과 얼마나 관련이 있는지 평가
       - 검색 결과의 신뢰도 평가
       - 검색 결과가 충분한 정보를 제공하는지 평가
    3. 평가 결과를 구조화하여 저장
       - relevance_score: 연관성 점수
       - is_relevant: 연관성 여부
       - needs_rewrite: 쿼리 재작성 필요 여부
       - reasoning: 평가 사고 과정
    4. state의 result_dict에 연관성 평가 결과 저장
    5. steps에 현재 단계 추가 및 metadata 업데이트
    """
    logger.info("연관성 평가 노드 실행")
    # TODO: 구현 필요
    steps = state.get("steps", [])
    state["steps"] = steps + ["evaluate_relevance"]
    return state


async def rewrite_query_with_context_node(state: WorkflowState) -> WorkflowState:
    """
    컨텍스트 기반 쿼리 재작성 노드
    
    구현 필요 사항:
    1. state에서 다음 정보 가져오기
       - 초기 질문 (queries[0])
       - 이전 검색 쿼리
       - 검색된 문서들
    2. LLM을 사용하여 컨텍스트를 고려한 쿼리 재작성
       - 검색된 문서를 분석하여 부족한 정보 파악
       - 초기 질문의 의도를 더 명확히 반영
       - 검색에 더 적합한 키워드로 재작성
    3. 재작성된 쿼리를 저장
       - rewritten_query: 재작성된 쿼리
       - rewrite_reason: 재작성 이유
       - extracted_keywords: 새로 추출된 키워드
    4. state의 result_dict에 재작성된 쿼리 저장
    5. steps에 현재 단계 추가 및 metadata 업데이트
    6. 무한 루프 방지를 위한 재시도 카운터 확인 (metadata에 저장)
    """
    logger.info("컨텍스트 기반 쿼리 재작성 노드 실행")
    # TODO: 구현 필요
    # 무한 루프 방지: 재시도 카운터 확인
    retry_count = state.get("metadata", {}).get("rewrite_retry_count", 0)
    state["metadata"]["rewrite_retry_count"] = retry_count + 1
    steps = state.get("steps", [])
    state["steps"] = steps + ["rewrite_query_with_context"]
    # TODO: 재작성된 쿼리를 queries 리스트에 추가
    # rewritten_query = ...
    # state["queries"] = state.get("queries", []) + [rewritten_query]
    return state


# ============================================================================
# 조건 함수들 (라우팅 함수)
# ============================================================================

def route_after_query_evaluation(state: WorkflowState) -> str:
    """
    쿼리 평가 후 라우팅 함수
    
    구현 필요 사항:
    1. state에서 evaluate_query_node의 결과 가져오기
    2. result_dict에서 평가 결과 확인
       - is_valid: 맛집 검색에 적합한 쿼리인지
       - is_inappropriate: 부적절한 질문인지
    3. 조건에 따라 분기
       - is_valid가 True이고 is_inappropriate가 False면 "valid" 반환
       - 그 외의 경우 "invalid" 반환하여 END로 이동
    4. 반환값: "valid" 또는 "invalid"
    """
    result_dict = state.get("result_dict", {})
    # TODO: 구현 필요 - result_dict의 구조에 맞게 평가
    is_valid = result_dict.get("is_valid", False)
    is_inappropriate = result_dict.get("is_inappropriate", False)
    
    if is_valid and not is_inappropriate:
        return "valid"
    else:
        return "invalid"


def route_after_search_evaluation(state: WorkflowState) -> str:
    """
    검색 결과 평가 후 라우팅 함수
    
    검색 결과 평가 결과에 따라 분기합니다.
    - is_relevant가 True이고 is_sufficient가 True면 "valid" 반환 (최종 응답 생성)
    - 그 외의 경우 "invalid" 반환 (병렬 검색으로 이동)
    """
    result_dict = state.get("result_dict", {})
    search_evaluation = result_dict.get("search_evaluation", {})
    
    is_relevant = search_evaluation.get("is_relevant", False)
    is_sufficient = search_evaluation.get("is_sufficient", False)
    
    if is_relevant and is_sufficient:
        return "valid"
    else:
        return "invalid"


def route_after_relevance_evaluation(state: WorkflowState) -> str:
    """
    연관성 평가 후 라우팅 함수
    
    구현 필요 사항:
    1. state에서 evaluate_relevance_node의 결과 가져오기
    2. result_dict에서 평가 결과 확인
       - is_relevant: 연관성 여부
       - needs_rewrite: 쿼리 재작성 필요 여부
       - relevance_score: 연관성 점수
    3. 무한 루프 방지 확인
       - metadata의 rewrite_retry_count 확인
       - 최대 재시도 횟수(예: 3회) 초과 시 "valid" 반환하여 강제 종료
    4. 조건에 따라 분기
       - needs_rewrite가 True이고 재시도 횟수가 최대치 미만이면 "rewrite" 반환
       - 그 외의 경우 "valid" 반환 (최종 응답 생성)
    5. 반환값: "rewrite" 또는 "valid"
    """
    result_dict = state.get("result_dict", {})
    metadata = state.get("metadata", {})
    
    # 무한 루프 방지: 최대 재시도 횟수 확인
    retry_count = metadata.get("rewrite_retry_count", 0)
    max_retries = 3  # 최대 재시도 횟수
    
    if retry_count >= max_retries:
        logger.warning(f"최대 재시도 횟수({max_retries}) 초과, 강제 종료")
        return "valid"
    
    # TODO: 구현 필요 - result_dict의 구조에 맞게 평가
    needs_rewrite = result_dict.get("needs_rewrite", False)
    
    if needs_rewrite:
        return "rewrite"
    else:
        return "valid"