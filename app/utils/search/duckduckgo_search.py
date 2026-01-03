"""DuckDuckGo 검색 유틸리티

DuckDuckGo Search를 사용하여 웹 검색을 수행합니다.
"""

import logging
from typing import Optional
from duckduckgo_search import DDGS

from app.utils.llm_utils import llm_call, LLMRequest
from app.schemas.llm_response_models import (
    BlogItemsEvaluationResult
)

logger = logging.getLogger(__name__)

# 평가 관련 상수 (블로그와 동일)
MAX_ITEMS_FOR_EVALUATION = 10  # 한 번에 평가할 최대 항목 수
MAX_DESCRIPTION_LENGTH = 150  # 프롬프트에 포함할 description 최대 길이
MAX_TITLE_LENGTH = 50  # 프롬프트에 포함할 title 최대 길이
MAX_REASONING_LENGTH = 50  # 개별 항목 평가 이유 최대 길이
MIN_RELEVANT_PASS_RATE = 0.6  # 연관성 있는 것으로 판단하는 최소 pass 비율 (60%)
MIN_RELEVANT_ITEMS = 2  # 연관성 있는 것으로 판단하는 최소 pass 항목 수


async def search_duckduckgo(
    queries: list[str],
    max_results_per_query: int = 10,
    max_total: int = 30
) -> dict:
    """
    DuckDuckGo 웹 검색
    
    Args:
        queries: 검색 쿼리 리스트
        max_results_per_query: 쿼리당 최대 결과 개수
        max_total: 전체 최대 결과 개수
        
    Returns:
        {
            "queries": 사용된 쿼리 리스트,
            "count": 검색 결과 개수,
            "hits": 검색 결과 리스트
        }
    """
    all_hits = []
    
    # 각 쿼리별로 검색 (최대 3개 쿼리만 처리)
    limited_queries = queries[:3]
    
    try:
        with DDGS() as ddgs:
            for query in limited_queries:
                # 이미 충분한 결과가 있으면 중단
                if len(all_hits) >= max_total:
                    break
                
                try:
                    # DuckDuckGo 텍스트 검색
                    results = list(ddgs.text(
                        query,
                        max_results=min(max_results_per_query, max_total - len(all_hits))
                    ))
                    
                    hits = []
                    for result in results:
                        title = result.get("title", "")
                        url = result.get("href", "")
                        description = result.get("body", "")
                        
                        if title and url:
                            hits.append({
                                "title": title,
                                "link": url,
                                "description": description,
                            })
                    
                    all_hits.extend(hits)
                    logger.info(f'DuckDuckGo 검색 완료: query="{query}", results={len(hits)}개')
                    
                except Exception as e:
                    logger.error(f'DuckDuckGo 검색 오류 (query="{query}"): {str(e)}')
                    continue  # 하나 실패해도 다른 쿼리는 계속 진행
        
        # 중복 제거 (link 기준)
        seen = set()
        unique_hits = []
        for hit in all_hits:
            link = hit.get("link", "")
            if link and link not in seen:
                seen.add(link)
                unique_hits.append(hit)
        
        return {
            "queries": limited_queries,
            "count": len(unique_hits),
            "hits": unique_hits[:max_total]  # 최대 개수 제한
        }
        
    except Exception as e:
        logger.error(f"DuckDuckGo 검색 전체 실패: {str(e)}", exc_info=True)
        return {
            "queries": limited_queries,
            "count": 0,
            "hits": []
        }


def _get_default_evaluation(hits: list[dict], original_query: str) -> dict:
    """
    기본 평가 로직 (에러 처리용)
    
    AI API 호출 실패 시 키워드 매칭을 통한 기본 평가를 수행합니다.
    
    Args:
        hits: 검색 결과 항목 리스트 (title, link, description 포함)
        original_query: 원본 검색 쿼리
        
    Returns:
        평가 결과 딕셔너리 (link를 key로 하는 각 항목별 평가 결과)
    """
    results = {}
    query_keywords = original_query.lower().split()
    
    for hit in hits:
        link = hit.get("link", "")
        if not link:
            continue
        
        title = hit.get("title", "").lower()
        description = hit.get("description", "").lower()
        has_keywords = any(keyword in title or keyword in description for keyword in query_keywords)
        
        results[link] = {
            "reason": f"평가 실패, 기본 평가: {'키워드 포함' if has_keywords else '키워드 미포함'}",
            "pass": has_keywords
        }
    
    return results


async def evaluate_all_duckduckgo_items(
    hits: list[dict],
    original_query: str
) -> dict:
    """
    모든 DuckDuckGo 검색 결과 항목을 한 번의 AI API 호출로 평가합니다.
    
    Args:
        hits: 검색 결과 항목 리스트 (title, link, description 포함)
        original_query: 원본 검색 쿼리
        
    Returns:
        평가 결과 딕셔너리 (link를 key로 하는 각 항목별 평가 결과)
    """
    if not hits:
        return {}
    
    # 평가할 항목 제한 (토큰 절약)
    items_to_evaluate = hits[:MAX_ITEMS_FOR_EVALUATION]
    
    # 항목 정보 포맷팅 (간소화된 포맷, 링크는 최소한만 포함)
    items_text = "\n".join([
        f"{i+1}. {hit.get('link', 'N/A')}|{hit.get('title', 'N/A')[:MAX_TITLE_LENGTH]}|{hit.get('description', 'N/A')[:MAX_DESCRIPTION_LENGTH]}"
        for i, hit in enumerate(items_to_evaluate)
    ])
    
    # 시스템 프롬프트 (간소화, 200자 이내)
    system_prompt = """맛집 검색 결과 평가 AI. 위치/음식종류 일치, 실용성 평가. 각 항목: link, is_relevant, reasoning(최대 50자)."""
    
    # 사용자 프롬프트 (간소화, 평가 기준 축소)
    user_prompt = f"""사용자 질문: "{original_query}"
검색 결과 ({len(hits)}개 중 {len(items_to_evaluate)}개 평가):
{items_text}

평가 기준:
1. 위치 일치: 요청한 위치와 검색 결과 위치 일치 여부
2. 음식 종류 일치: 요청한 음식 종류와 검색 결과 음식 종류 일치 여부
3. 실용성: 실제 맛집 정보(위치, 음식종류, 맛집이름) 제공 여부

각 항목의 연관성과 실용성을 평가하세요. reasoning은 최대 {MAX_REASONING_LENGTH}자로 작성하세요."""
    
    try:
        llm_request: LLMRequest = {
            "user_prompt": user_prompt,
            "system_prompt": system_prompt
        }
        
        result, _ = await llm_call(llm_request, BlogItemsEvaluationResult)
        
        # link를 key로 하는 딕셔너리로 변환
        results = {}
        for item in result.items:
            results[item.link] = {
                "reason": item.reasoning,
                "pass": item.is_relevant
            }
        
        logger.info(f"개별 DuckDuckGo 항목 평가 완료: {len(results)}개 항목 평가")
        
        return results
    except Exception as e:
        logger.error(f"개별 DuckDuckGo 항목 평가 실패: {str(e)}", exc_info=True)
        # 기본 평가 로직 사용
        return _get_default_evaluation(hits, original_query)


async def execute_duckduckgo_search(queries: list[str]) -> dict:
    """
    DuckDuckGo 검색 실행 함수 (병렬 실행용)
    
    검색을 수행하고 결과를 AI API로 평가합니다.
    각 포스트별 평가 결과를 리스트로 반환합니다.
    
    Args:
        queries: 검색 쿼리 리스트
        
    Returns:
        검색 결과 딕셔너리:
        - items: 각 포스트별 평가 결과 리스트
          - 각 항목: title, link, description, pass(통과여부), reason(통과이유)
    """
    try:
        # 검색 수행
        search_results = await search_duckduckgo(queries)
        
        # 원본 쿼리 추출 (첫 번째 쿼리 사용)
        original_query = queries[0] if queries else ""
        
        hits = search_results.get("hits", [])
        
        if not hits:
            # 검색 결과가 없으면 빈 리스트 반환
            return {
                "items": []
            }
        
        # 모든 항목을 한 번의 AI API 호출로 평가
        items_evaluation = await evaluate_all_duckduckgo_items(hits, original_query)
        
        # 각 포스트별 평가 결과 리스트 생성 (검색 상세 내용 + 평가 정보)
        evaluated_items = []
        for hit in hits:
            link = hit.get("link", "")
            if not link:
                continue
            
            # 개별 평가 결과 가져오기 (없으면 기본값)
            item_eval = items_evaluation.get(link, {
                "reason": "평가되지 않음",
                "pass": False
            })
            
            # 검색 상세 내용 + 평가 정보 결합
            evaluated_items.append({
                "title": hit.get("title", ""),
                "link": link,
                "description": hit.get("description", ""),
                "pass": item_eval.get("pass", False),  # 통과 여부
                "reason": item_eval.get("reason", "")  # 통과 이유
            })
        
        return {
            "items": evaluated_items
        }
    except Exception as e:
        logger.error(f"DuckDuckGo 검색 실패: {str(e)}", exc_info=True)
        return {
            "items": []
        }

