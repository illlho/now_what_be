"""오케스트레이션 라우터

여러 Agent 작업을 조율하고 워크플로우를 관리하는 중앙 라우터
"""

from typing import Optional
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import logging
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=".env", override=True)

from langgraph.graph import StateGraph, END

# 스키마 import
from app.schemas.workflow_state import WorkflowState
from app.schemas.orchestration_models import (
    UserRequest,
    TokenUsageSummary,
    OrchestrationResponse,
    GraphVisualizationResponse,
)
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

# 노드 함수 import
from app.nodes.workflow_nodes import (
    evaluate_query_node,
    rewrite_query_and_extract_keywords_node,
    hybrid_search_node,
    evaluate_search_results_node,
    generate_final_response_node,
    parallel_search_node,
    evaluate_relevance_node,
    rewrite_query_with_context_node,
    route_after_query_evaluation,
    route_after_search_evaluation,
    route_after_relevance_evaluation,
)

# 유틸리티 함수 import
from app.utils.llm_utils import LLMRequest, llm_call
from app.utils.graph_visualization import (
    generate_mermaid_diagram,
    generate_html_content,
    generate_error_html
)
from app.utils.search.naver_blog_search import (
    test_evaluate_naver_blog_results,
    EvaluateNaverBlogRequest,
    EvaluateNaverBlogResponse,
    NaverBlogSearchResults
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/orchestration", tags=["orchestration"])


def _aggregate_token_usage(result_state: WorkflowState) -> Optional[TokenUsageSummary]:
    """
    워크플로우 실행 결과에서 토큰 사용량을 집계합니다.
    
    Args:
        result_state: 워크플로우 실행 결과 상태
        
    Returns:
        토큰 사용량 요약 정보 (토큰 정보가 없으면 None)
    """
    # token_usage_total에서 누적 값 가져오기
    token_usage_total = result_state.get("token_usage_total", {})
    token_usage_list = result_state.get("token_usage_list", [])
    
    # 토큰 정보가 없으면 None 반환
    if not token_usage_total or token_usage_total.get("total_tokens", 0) == 0:
        return None
    
    # node_breakdown 생성 (token_usage_list에서)
    node_breakdown = []
    for usage in token_usage_list:
        node_breakdown.append({
            "step": usage.get("step", "unknown"),
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "cost_formatted": usage.get("cost_formatted", "0.00원(0 tokens)")
        })
    
    return TokenUsageSummary(
        total_input_tokens=token_usage_total.get("total_input_tokens", 0),
        total_output_tokens=token_usage_total.get("total_output_tokens", 0),
        total_tokens=token_usage_total.get("total_tokens", 0),
        total_cost_krw=token_usage_total.get("total_cost_krw", 0.0),
        total_cost_formatted=token_usage_total.get("total_cost_formatted", "0.00원(0 tokens)"),
        node_breakdown=node_breakdown
    )


def _build_graph() -> StateGraph:
    """워크플로우 그래프 생성 (재사용 가능하도록 분리)"""
    graph = StateGraph(WorkflowState)
    
    # 노드 추가
    graph.add_node("evaluate_query", evaluate_query_node)  # 쿼리 평가
    graph.add_node("rewrite_query_and_extract_keywords", rewrite_query_and_extract_keywords_node)  # 쿼리 재작성 및 키워드 추출
    graph.add_node("hybrid_search", hybrid_search_node)  # 하이브리드 검색
    graph.add_node("evaluate_search_results", evaluate_search_results_node)  # 검색 결과 평가
    graph.add_node("generate_final_response", generate_final_response_node)  # 최종 응답 생성
    graph.add_node("parallel_search", parallel_search_node)  # 병렬 검색 (네이버지도, 블로그, 웹)
    graph.add_node("evaluate_relevance", evaluate_relevance_node)  # 연관성 평가
    graph.add_node("rewrite_query_with_context", rewrite_query_with_context_node)  # 컨텍스트 기반 쿼리 재작성
    
    # 엔트리 포인트 설정
    graph.set_entry_point("evaluate_query")
    
    # 엣지 추가
    # 1. 쿼리 평가 후 분기
    graph.add_conditional_edges(
        "evaluate_query",
        route_after_query_evaluation,
        {
            "valid": "rewrite_query_and_extract_keywords",
            "invalid": END
        }
    )
    
    # 2. 쿼리 재작성 → 하이브리드 검색
    graph.add_edge("rewrite_query_and_extract_keywords", "hybrid_search")
    
    # 3. 하이브리드 검색 → 검색 결과 평가
    graph.add_edge("hybrid_search", "evaluate_search_results")
    
    # 4. 검색 결과 평가 후 분기
    graph.add_conditional_edges(
        "evaluate_search_results",
        route_after_search_evaluation,
        {
            "valid": "generate_final_response",
            "invalid": "parallel_search"
        }
    )
    
    # 5. 병렬 검색 → 연관성 평가
    graph.add_edge("parallel_search", "evaluate_relevance")
    
    # 6. 연관성 평가 후 분기
    graph.add_conditional_edges(
        "evaluate_relevance",
        route_after_relevance_evaluation,
        {
            "rewrite": "rewrite_query_with_context",
            "valid": "generate_final_response"
        }
    )
    
    # 7. 컨텍스트 기반 쿼리 재작성 → 병렬 검색 (루프)
    graph.add_edge("rewrite_query_with_context", "parallel_search")
    
    # 8. 최종 응답 생성 → 종료
    graph.add_edge("generate_final_response", END)
    
    return graph

@router.get("/graph-visualization/html", response_class=HTMLResponse, summary="워크플로우 그래프 HTML 뷰어")
async def get_graph_visualization_html():
    """
    워크플로우 그래프를 HTML 페이지로 시각화합니다.
    Mermaid.js를 사용하여 브라우저에서 바로 확인할 수 있습니다.
    """
    try:
        # Mermaid 다이어그램 생성
        mermaid_code = generate_mermaid_diagram(_build_graph)
        
        # HTML 콘텐츠 생성
        html_content = generate_html_content(mermaid_code)
        
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"그래프 HTML 시각화 실패: {str(e)}", exc_info=True)
        error_html = generate_error_html(str(e))
        return HTMLResponse(content=error_html, status_code=500)


@router.post("/start-foodie-workflow", response_model=OrchestrationResponse, summary="맛집 탐색 워크플로우 시작")
async def start_foodie_workflow(request: UserRequest):
    try:
        # 그래프 생성
        graph = _build_graph()

        # 그래프 컴파일
        compiled_graph = graph.compile()
        
        # 초기 상태 설정
        initial_state: WorkflowState = {
            "queries": [request.query],  # 0번 인덱스에 최초 사용자 입력
            "steps": [],  # 빈 리스트로 시작 (첫 노드에서 추가됨)
            "result_dict": {},
            "metadata": {},
            "token_usage_list": [],  # 각 노드별 토큰 사용량 리스트
            "token_usage_total": {  # 누적 토큰 사용량 및 비용
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "total_cost_krw": 0.0,
                "total_cost_formatted": "0.00원(0 tokens)"
            }
        }

        # 워크플로우 실행
        logger.info("워크플로우 실행 중...")
        result_state = await compiled_graph.ainvoke(initial_state)
        
        logger.info(f"워크플로우 결과: {result_state}")

        # 결과 추출
        final_result = result_state.get("result_dict", {})
        metadata = result_state.get("metadata", {})
        success = metadata.get("status") == "completed" if metadata else True
        
        # 토큰 사용량 집계
        token_usage_summary = _aggregate_token_usage(result_state)
        
        logger.info(
            f"워크플로우 완료: 성공={success}, 결과 타입={type(final_result)} | "
            f"총 비용: {token_usage_summary.total_cost_formatted if token_usage_summary else 'N/A'}"
        )
        
        return OrchestrationResponse(
            result_dict=final_result,
            query=request.query,
            success=success,
            token_usage=token_usage_summary
        )
    except Exception as e:
        logger.error(f"워크플로우 실행 실패: {str(e)}", exc_info=True)
        
        return OrchestrationResponse(
            result_dict={"error": f"워크플로우 실행 중 오류 발생: {str(e)}"},
            query=request.query,
            success=False,
            token_usage=None
        )


@router.post("/test/evaluate-naver-blog", response_model=EvaluateNaverBlogResponse, summary="네이버 블로그 검색 결과 평가 테스트")
async def test_evaluate_naver_blog(request: Optional[EvaluateNaverBlogRequest] = None):
    """
    네이버 블로그 검색 결과 평가 함수를 테스트하는 엔드포인트
    
    요청이 없으면 기본 테스트 데이터를 사용합니다.
    """
    # 요청이 있으면 사용, 없으면 None 전달 (기본 데이터 사용)
    search_results_dict = None
    original_query = None
    
    # if request:
    #     search_results_dict = request.search_results.model_dump()
    #     original_query = request.original_query
    
    try:
        # 테스트 함수 호출 (로직은 naver_blog_search.py에 있음)
        result = await test_evaluate_naver_blog_results(
            search_results=search_results_dict,
            original_query=original_query
        )
        
        return EvaluateNaverBlogResponse(
            evaluation=result["evaluation"],
            results=result["results"],  # link를 key로 하는 각 항목별 평가 결과
            search_results=NaverBlogSearchResults(**result["search_results"]),
            original_query=result["original_query"]
        )
    except Exception as e:
        logger.error(f"네이버 블로그 검색 결과 평가 실패: {str(e)}", exc_info=True)
        raise