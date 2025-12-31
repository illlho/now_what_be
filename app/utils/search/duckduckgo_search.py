"""DuckDuckGo 검색 유틸리티

DuckDuckGo Search를 사용하여 웹 검색을 수행합니다.
"""

import logging
from typing import Optional
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)


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

