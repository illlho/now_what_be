"""기본 도구들 (reverse_geocode, terminate)"""

import logging
from typing import Dict, Any, Optional
from langchain_core.tools import tool
from app.utils.geocoding import reverse_geocode as _reverse_geocode

logger = logging.getLogger(__name__)


@tool
async def reverse_geocode(latitude: float, longitude: float) -> Dict[str, Any]:
    """좌표를 주소로 변환합니다 (Kakao Local API).
    
    Args:
        latitude: 위도
        longitude: 경도
        
    Returns:
        Dict: {
            "location_keyword": "흥선동",
            "depth_1": "의정부시",
            "depth_2": "흥선동",
            "address": "의정부시 흥선동"
        }
        
    Example:
        result = await reverse_geocode(37.74608637371771, 127.03254389562254)
        # → {"location_keyword": "흥선동", ...}
    """
    logger.info(f"🌍 역지오코딩 실행: ({latitude}, {longitude})")
    
    result = await _reverse_geocode(latitude, longitude)
    
    if result:
        logger.info(f"✅ 역지오코딩 성공: {result.get('location_keyword')}")
        return result
    else:
        logger.warning("⚠️  역지오코딩 실패")
        return {
            "location_keyword": None,
            "depth_1": None,
            "depth_2": None,
            "address": None,
            "error": "역지오코딩 실패"
        }


@tool
def terminate(result: Dict[str, Any]) -> str:
    """작업을 완료하고 최종 결과를 반환합니다.
    
    Args:
        result: 최종 결과 딕셔너리
        
    Returns:
        str: 완료 메시지
        
    Example:
        terminate({"places": [...], "summary": "12개 장소 분석 완료"})
    """
    logger.info("🏁 작업 완료 - terminate 호출")
    logger.info(f"최종 결과 키: {list(result.keys())}")
    
    return "작업이 완료되었습니다. 최종 결과를 반환합니다."
