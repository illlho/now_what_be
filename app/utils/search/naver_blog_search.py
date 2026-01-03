"""네이버 블로그 검색 유틸리티

네이버 블로그 API를 사용하여 블로그 검색을 수행합니다.
"""

import os
import logging
import re
import httpx
from typing import Optional, List, Dict
from pydantic import BaseModel

from app.utils.llm_utils import llm_call, LLMRequest
from app.schemas.llm_response_models import (
    BlogItemsEvaluationResult
)

logger = logging.getLogger(__name__)


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


# 평가 관련 상수
MAX_ITEMS_FOR_EVALUATION = 10  # 한 번에 평가할 최대 항목 수
MAX_DESCRIPTION_LENGTH = 150  # 프롬프트에 포함할 description 최대 길이
MAX_TITLE_LENGTH = 50  # 프롬프트에 포함할 title 최대 길이
MIN_SUFFICIENT_COUNT = 3  # 충분한 검색 결과로 판단하는 최소 개수
MAX_REASONING_LENGTH = 50  # 개별 항목 평가 이유 최대 길이
MIN_RELEVANT_PASS_RATE = 0.6  # 연관성 있는 것으로 판단하는 최소 pass 비율 (60%)
MIN_RELEVANT_ITEMS = 2  # 연관성 있는 것으로 판단하는 최소 pass 항목 수


def strip_html_tags(text: str) -> str:
    """HTML 태그 제거"""
    return re.sub(r'<[^>]*>', '', text)


async def search_naver_blog(
    queries: list[str],
    limit_per_query: int = 5,
    max_total: int = 15
) -> dict:
    """
    네이버 블로그 검색
    
    Args:
        queries: 검색 쿼리 리스트
        limit_per_query: 쿼리당 가져올 개수
        max_total: 최대 총 개수
        
    Returns:
        {
            "queries": 사용된 쿼리 리스트,
            "count": 검색 결과 개수,
            "hits": 검색 결과 리스트
        }
    """
    client_id = os.getenv('NAVER_CLIENT_ID')
    client_secret = os.getenv('NAVER_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        logger.error("NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET이 설정되지 않았습니다.")
        raise ValueError("NAVER_SECRET_MISSING")
    
    all_hits = []
    display = limit_per_query
    
    # 각 쿼리별로 검색 (최대 3개 쿼리만 처리)
    limited_queries = queries[:3]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for query in limited_queries:
            # 이미 충분한 결과가 있으면 중단
            if len(all_hits) >= max_total:
                break
            
            try:
                url = "https://openapi.naver.com/v1/search/blog.json"
                params = {
                    "query": query,
                    "display": str(display),
                    "sort": "date"  # 최신순
                }
                
                headers = {
                    "X-Naver-Client-Id": client_id,
                    "X-Naver-Client-Secret": client_secret,
                }
                
                response = await client.get(url, params=params, headers=headers)
                
                if not response.is_success:
                    error_body = response.text[:200] if response.text else ""
                    logger.error(f"Naver Blog API error: {response.status_code} - {error_body}")
                    continue  # 하나 실패해도 다른 쿼리는 계속 진행
                
                json_data = response.json()
                items = json_data.get("items", [])
                
                hits = []
                for item in items:
                    title = strip_html_tags(str(item.get("title", "")))
                    link = str(item.get("link", ""))
                    
                    if title and link:
                        hits.append({
                            "title": title,
                            "link": link,  # DB unique key로 사용 가능한 링크
                            "description": strip_html_tags(str(item.get("description", ""))),
                            "bloggername": item.get("bloggername"),
                            "bloggerlink": item.get("bloggerlink"),
                            "postdate": item.get("postdate"),
                        })
                
                all_hits.extend(hits)
                
            except Exception as e:
                logger.error(f'Naver Blog search error for query "{query}": {str(e)}')
                continue
    
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


async def evaluate_all_blog_items(
    hits: list[dict],
    original_query: str
) -> dict:
    """
    모든 블로그 검색 결과 항목을 한 번의 AI API 호출로 평가합니다.
    
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
        
        logger.info(f"개별 블로그 항목 평가 완료: {len(results)}개 항목 평가")
        
        return results
    except Exception as e:
        logger.error(f"개별 블로그 항목 평가 실패: {str(e)}", exc_info=True)
        # 기본 평가 로직 사용
        return _get_default_evaluation(hits, original_query)


def aggregate_evaluation_from_items(
    items_evaluation: dict,
    total_count: int
) -> dict:
    """
    개별 항목 평가 결과를 종합하여 전체 평가를 도출합니다.
    
    Args:
        items_evaluation: link를 key로 하는 개별 항목 평가 결과
        total_count: 전체 검색 결과 개수
        
    Returns:
        전체 평가 결과 딕셔너리 (is_relevant, is_sufficient, quality_score, reasoning)
    """
    if not items_evaluation:
        return {
            "is_relevant": False,
            "is_sufficient": False,
            "quality_score": 0.0,
            "reasoning": "평가할 항목이 없습니다."
        }
    
    # 통계 계산
    total_items = len(items_evaluation)
    passed_items = sum(1 for item in items_evaluation.values() if item.get("pass", False))
    pass_rate = passed_items / total_items if total_items > 0 else 0.0
    
    # 전체 평가 도출
    # is_relevant: pass 비율과 최소 항목 수 모두 고려 (더 엄격한 기준)
    is_relevant = pass_rate >= MIN_RELEVANT_PASS_RATE and passed_items >= MIN_RELEVANT_ITEMS
    is_sufficient = total_count >= MIN_SUFFICIENT_COUNT  # 최소 개수 이상
    
    # quality_score: pass 비율(70%) + 결과 개수(30%)를 모두 고려
    # 결과 개수가 많을수록 품질 점수에 가산점 (최대 10개까지)
    count_score = min(total_count, 10) / 10.0  # 0.0 ~ 1.0
    quality_score = round(pass_rate * 0.7 + count_score * 0.3, 2)
    
    # reasoning 생성
    if passed_items == 0:
        reasoning = f"평가된 {total_items}개 항목 중 연관성 있는 항목이 없습니다."
    elif passed_items == total_items:
        reasoning = f"평가된 {total_items}개 항목 모두 연관성이 있습니다."
    else:
        reasoning = f"평가된 {total_items}개 항목 중 {passed_items}개({pass_rate*100:.0f}%)가 연관성이 있습니다."
    
    # 최대 150자로 제한
    if len(reasoning) > 150:
        reasoning = reasoning[:147] + "..."
    
    return {
        "is_relevant": is_relevant,
        "is_sufficient": is_sufficient,
        "quality_score": quality_score,
        "reasoning": reasoning
    }


async def execute_naver_blog_search(queries: list[str]) -> dict:
    """
    네이버 블로그 검색 실행 함수 (병렬 실행용)
    
    검색을 수행하고 결과를 AI API로 평가합니다.
    각 포스트별 평가 결과를 리스트로 반환합니다.
    
    Args:
        queries: 검색 쿼리 리스트
        
    Returns:
        검색 결과 딕셔너리:
        - items: 각 포스트별 평가 결과 리스트
          - 각 항목: title, link, description, bloggername, postdate, pass(통과여부), reason(통과이유)
    """
    try:
        # 검색 수행
        search_results = await search_naver_blog(queries)
        
        # 원본 쿼리 추출 (첫 번째 쿼리 사용)
        original_query = queries[0] if queries else ""
        
        hits = search_results.get("hits", [])
        
        if not hits:
            # 검색 결과가 없으면 빈 리스트 반환
            return {
                "items": []
            }
        
        # 모든 항목을 한 번의 AI API 호출로 평가
        items_evaluation = await evaluate_all_blog_items(hits, original_query)
        
        # 각 포스트별 평가 결과 리스트 생성 (블로그 상세 내용 + 평가 정보)
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
            
            # 블로그 상세 내용 + 평가 정보 결합
            evaluated_items.append({
                "title": hit.get("title", ""),
                "link": link,
                "description": hit.get("description", ""),
                "bloggername": hit.get("bloggername"),
                "bloggerlink": hit.get("bloggerlink"),
                "postdate": hit.get("postdate"),
                "pass": item_eval.get("pass", False),  # 통과 여부
                "reason": item_eval.get("reason", "")  # 통과 이유
            })
        
        return {
            "items": evaluated_items
        }
    except Exception as e:
        logger.error(f"네이버 블로그 검색 실패: {str(e)}", exc_info=True)
        return {
            "items": []
        }


