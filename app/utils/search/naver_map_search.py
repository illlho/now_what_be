"""네이버 지도 검색 유틸리티

네이버 지도 API를 사용하여 로컬 검색을 수행합니다.
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


async def search_naver_map(queries: list[str]) -> dict:
    """
    네이버 지도(로컬) 검색
    
    Args:
        queries: 검색 쿼리 리스트
        
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
    display = 5
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for query in queries:
            try:
                url = "https://openapi.naver.com/v1/search/local.json"
                params = {
                    "query": query,
                    "display": str(display),
                    "sort": "comment"  # 댓글순
                }
                
                headers = {
                    "X-Naver-Client-Id": client_id,
                    "X-Naver-Client-Secret": client_secret,
                }
                
                response = await client.get(url, params=params, headers=headers)
                
                if not response.is_success:
                    error_body = response.text[:200] if response.text else ""
                    logger.error(f"Naver Map API error: {response.status_code} - {error_body}")
                    continue  # 하나 실패해도 다른 쿼리는 계속 진행
                
                json_data = response.json()
                items = json_data.get("items", [])
                
                hits = []
                for item in items:
                    title = strip_html_tags(str(item.get("title", "")))
                    
                    if title:
                        hits.append({
                            "title": title,
                            "link": item.get("link"),
                            "category": strip_html_tags(str(item.get("category", ""))) if item.get("category") else None,
                            "description": strip_html_tags(str(item.get("description", ""))) if item.get("description") else None,
                            "telephone": item.get("telephone"),
                            "address": item.get("address"),
                            "roadAddress": item.get("roadAddress"),
                            "mapx": item.get("mapx"),
                            "mapy": item.get("mapy"),
                        })
                
                all_hits.extend(hits)
                
            except Exception as e:
                logger.error(f'Naver Map search error for query "{query}": {str(e)}')
                continue
    
    # 중복 제거 (link 또는 title+address 기준)
    seen = set()
    unique_hits = []
    for hit in all_hits:
        link = hit.get("link", "")
        title = hit.get("title", "")
        road_address = hit.get("roadAddress", "")
        address = hit.get("address", "")
        
        key = link if link and link.strip() else f"{title}|{road_address or address or ''}"
        
        if key and key not in seen:
            seen.add(key)
            unique_hits.append(hit)
    
    return {
        "queries": queries,
        "count": len(unique_hits),
        "hits": unique_hits[:30]  # 최대 30개로 제한
    }


async def execute_naver_map_search(queries: list[str]) -> dict:
    """
    네이버 지도 검색 실행 함수 (병렬 실행용)
    
    Args:
        queries: 검색 쿼리 리스트
        
    Returns:
        검색 결과 딕셔너리 (예외 발생 시 빈 결과 반환)
    """
    try:
        return await search_naver_map(queries)
    except Exception as e:
        logger.error(f"네이버 지도 검색 실패: {str(e)}", exc_info=True)
        return {
            "queries": queries if queries else [],
            "count": 0,
            "hits": []
        }

