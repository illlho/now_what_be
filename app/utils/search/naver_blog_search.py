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


class NaverBlogSearchResult(BaseModel):
    """네이버 블로그 검색 결과 항목"""
    title: str
    link: str
    description: str
    bloggername: Optional[str] = None
    bloggerlink: Optional[str] = None
    postdate: Optional[str] = None


class NaverBlogSearchResults(BaseModel):
    """네이버 블로그 검색 결과"""
    queries: List[str]
    count: int
    hits: List[NaverBlogSearchResult]


class EvaluateNaverBlogRequest(BaseModel):
    """네이버 블로그 검색 결과 평가 요청"""
    search_results: NaverBlogSearchResults
    original_query: str


class EvaluateNaverBlogResponse(BaseModel):
    """네이버 블로그 검색 결과 평가 응답"""
    evaluation: Dict
    results: Dict[str, Dict]  # link를 key로 하는 각 항목별 평가 결과 (title, description, reason, pass 포함)
    search_results: NaverBlogSearchResults
    original_query: str


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
    개별 항목 평가 후 종합하여 전체 평가를 도출합니다.
    
    Args:
        queries: 검색 쿼리 리스트
        
    Returns:
        검색 결과 딕셔너리 (evaluation 필드 포함, 예외 발생 시 빈 결과 반환)
    """
    try:
        # 검색 수행
        search_results = await search_naver_blog(queries)
        
        # 원본 쿼리 추출 (첫 번째 쿼리 사용)
        original_query = queries[0] if queries else ""
        
        hits = search_results.get("hits", [])
        
        if not hits:
            # 검색 결과가 없으면 기본 평가 반환
            search_results["evaluation"] = {
                "is_relevant": False,
                "is_sufficient": False,
                "quality_score": 0.0,
                "reasoning": "검색 결과가 없습니다."
            }
            return search_results
        
        # 모든 항목을 한 번의 AI API 호출로 평가
        items_evaluation = await evaluate_all_blog_items(hits, original_query)
        
        # 개별 평가 결과를 종합하여 전체 평가 도출 (AI API 없이)
        evaluation = aggregate_evaluation_from_items(
            items_evaluation,
            len(hits)
        )
        
        # 평가 결과를 검색 결과에 추가
        search_results["evaluation"] = evaluation
        
        return search_results
    except Exception as e:
        logger.error(f"네이버 블로그 검색 실패: {str(e)}", exc_info=True)
        return {
            "queries": queries[:3] if queries else [],
            "count": 0,
            "hits": [],
            "evaluation": {
                "is_relevant": False,
                "is_sufficient": False,
                "quality_score": 0.0,
                "reasoning": f"검색 실패: {str(e)}"
            }
        }


async def test_evaluate_naver_blog_results(
    search_results: Optional[dict] = None,
    original_query: Optional[str] = None
) -> dict:
    """
    네이버 블로그 검색 결과 평가 함수를 테스트하는 함수
    
    각 검색 결과 항목별로 평가를 수행하고, link를 key로 하여 결과를 반환합니다.
    
    Args:
        search_results: 검색 결과 딕셔너리 (없으면 기본 테스트 데이터 사용)
        original_query: 원본 검색 쿼리 (없으면 기본값 사용)
        
    Returns:
        평가 결과와 검색 결과를 포함한 딕셔너리
        - evaluation: 전체 평가 결과
        - results: link를 key로 하는 각 항목별 평가 결과 (title, description, reason, pass 포함)
    """
    # 기본 테스트 데이터
    default_data = {
        "queries": ["삼겹살 의정부"],
        "count": 5,
        "hits": [
            {
                "title": "2025년 10월 밥상 기록",
                "link": "https://blog.naver.com/jsa0406/224130377517",
                "description": "#의정부동오마을 #동오쭈꾸미 10월 퇴사후 자유로운 시간인 낮 시간대를 활용해서 친정부모님과 식사 후... 야채랑 삼겹살이랑 내가 좋아하는 된장찌게! #이지듀 시어머니께서 친정 엄마 여행 선물겸 우리것도... ",
                "bloggername": "제이씬의 꿈꾸는 일상블로그",
                "bloggerlink": "blog.naver.com/jsa0406",
                "postdate": "20260101"
            },
            {
                "title": "의정부삼겹살맛집은 싹쓰리 솥뚜껑 김치삼겹살이 제대로임!",
                "link": "https://blog.naver.com/gksthf219/224130354195",
                "description": "의정부삼겹살맛집 신곡동삼겹살맛집 의정부김치삼겹살 안녕하세요 솔입니다! 오늘은 신곡동에서 제대로 된 삼겹살을 즐기고 싶어서 싹쓰리 솥뚜껑 김치삼겹살 신곡1동점을 방문했어요 주소 경기 의정부시... ",
                "bloggername": "Things I Loved Most",
                "bloggerlink": "blog.naver.com/gksthf219",
                "postdate": "20260101"
            },
            {
                "title": "의정부 산곡동 맛집 인생돼지 의정부고산점 고기 구워주는 곳... ",
                "link": "https://blog.naver.com/hingkku99/224130323639",
                "description": "바라요ㅎㅎ #의정부산곡동맛집 #의정부고산동맛집 #의정부고산동맛집 #의정부고기구워주는곳 #의정부고기집 #의정부삼겹살맛집 #의정부삼겹살주차 #의정부삼겹살집 #인생돼지 #인생돼지의정부고산점... ",
                "bloggername": "꽉토피아",
                "bloggerlink": "blog.naver.com/hingkku99",
                "postdate": "20260101"
            },
            {
                "title": "[호랭이식당 의정부본점] 녹양동 맛집 | 의정부 삼겹살 1등 맛집!",
                "link": "https://blog.naver.com/qmarkemark/224130315627",
                "description": "#의정부고기집 #녹양동맛집 #녹양동삼겹살 #녹양동회식 #의정부삼겹살 #의정부맛집 총평 녹양동 삼겹살.. 여기가 왜 급냉 삼겹살 전문이고 의정부 삼겹살 1등 맛집이라고 하는 이유가 있더라고요... ",
                "bloggername": "물음표?느낌표!의 블로그",
                "bloggerlink": "blog.naver.com/qmarkemark",
                "postdate": "20260101"
            },
            {
                "title": "서울 종로3가역 삼겹살 맛집 '참돼짓간'",
                "link": "https://blog.naver.com/hong-owo-si/224130304404",
                "description": "의정부에서 먹은 고기들은 다 맛있었는데, 서울은 사실 그저 그런 곳이 대부분이었거든요...? 스울 밸 거 읍내 (서울 별 거 없네) 하며 ㅋㅋㅋ 고기 먹곤 했는데, 종로3가역 삼겹살 맛집 참돼짓간은 다르다... ",
                "bloggername": "동그라미",
                "bloggerlink": "blog.naver.com/hong-owo-si",
                "postdate": "20260101"
            }
        ]
    }
    
    # 파라미터가 없으면 기본 데이터 사용
    if search_results is None:
        search_results = default_data
    
    if original_query is None:
        original_query = "삼겹살 의정부"
    
    try:
        hits = search_results.get("hits", [])
        
        # 모든 항목을 한 번의 AI API 호출로 평가
        items_evaluation = await evaluate_all_blog_items(hits, original_query)
        
        # 평가 결과를 link를 key로 하는 형식으로 변환 (title, description 포함)
        # 한 번의 순회로 처리하여 성능 최적화
        results = {}
        for hit in hits:
            link = hit.get("link", "")
            if not link:
                continue
            
            # 개별 평가 결과 가져오기 (없으면 기본값)
            item_eval = items_evaluation.get(link, {
                "reason": "평가되지 않음",
                "pass": False
            })
            
            results[link] = {
                "title": hit.get("title", ""),
                "description": hit.get("description", ""),
                "reason": item_eval.get("reason", ""),
                "pass": item_eval.get("pass", False)
            }
        
        # 개별 평가 결과를 종합하여 전체 평가 도출 (AI API 없이)
        evaluation = aggregate_evaluation_from_items(
            items_evaluation,
            len(hits)
        )
        
        logger.info(f"네이버 블로그 검색 결과 평가 완료: {len(results)}개 항목 평가 및 전체 평가 종합 완료")
        
        return {
            "evaluation": evaluation,
            "results": results,  # link를 key로 하는 각 항목별 평가 결과
            "search_results": search_results,
            "original_query": original_query
        }
    except Exception as e:
        logger.error(f"네이버 블로그 검색 결과 평가 실패: {str(e)}", exc_info=True)
        raise

