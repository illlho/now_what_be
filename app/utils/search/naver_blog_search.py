"""네이버 블로그 검색 유틸리티

네이버 블로그 API를 사용하여 블로그 검색을 수행합니다.
"""

import os
import logging
import re
import httpx
from typing import Optional

logger = logging.getLogger(__name__)


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
                            "link": link,
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


async def execute_naver_blog_search(queries: list[str]) -> dict:
    """
    네이버 블로그 검색 실행 함수 (병렬 실행용)
    
    Args:
        queries: 검색 쿼리 리스트
        
    Returns:
        검색 결과 딕셔너리 (예외 발생 시 빈 결과 반환)
    """
    try:
        return await search_naver_blog(queries)
    except Exception as e:
        logger.error(f"네이버 블로그 검색 실패: {str(e)}", exc_info=True)
        return {
            "queries": queries[:3] if queries else [],
            "count": 0,
            "hits": []
        }

