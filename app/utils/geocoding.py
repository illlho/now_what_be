"""지오코딩 유틸리티

좌표를 주소로 변환하는 역지오코딩 기능을 제공합니다.
카카오 로컬 API를 사용합니다.
"""

import os
import logging
import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


async def reverse_geocode(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
    """
    좌표를 주소로 변환 (역지오코딩)
    
    카카오 로컬 API를 사용하여 좌표를 주소로 변환합니다.
    위치 키워드 추출을 위해 주소 정보를 반환합니다.
    
    Args:
        latitude: 위도
        longitude: 경도
        
    Returns:
        주소 정보 딕셔너리:
        {
            "location_keyword": "강남구" 또는 "역삼동" 등,
            "depth_1": "서울특별시",
            "depth_2": "강남구",
            "depth_3": "역삼동",
            "address": "서울특별시 강남구 역삼동"
        }
        또는 None (실패 시)
    """
    kakao_rest_api_key = os.getenv('KAKAO_REST_API_KEY')
    
    if not kakao_rest_api_key:
        logger.warning("KAKAO_REST_API_KEY가 설정되지 않았습니다. 역지오코딩을 건너뜁니다.")
        return None
    
    try:
        url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
        params = {
            "x": str(longitude),  # 카카오 API는 경도가 x
            "y": str(latitude),  # 카카오 API는 위도가 y
        }
        
        headers = {
            "Authorization": f"KakaoAK {kakao_rest_api_key}"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=headers)
            
            if not response.is_success:
                logger.error(f"카카오 역지오코딩 API 오류: {response.status_code} - {response.text[:200]}")
                return None
            
            json_data = response.json()
            documents = json_data.get("documents", [])
            
            if not documents:
                logger.warning(f"역지오코딩 결과가 없습니다. 좌표: ({latitude}, {longitude})")
                return None
            
            # 첫 번째 결과 사용
            doc = documents[0]
            
            # 도로명주소 우선, 없으면 지번주소
            road_address = doc.get("road_address")
            address = doc.get("address", {})
            
            if road_address:
                # 도로명주소가 있으면 사용
                region_1 = road_address.get("region_1depth_name", "")
                region_2 = road_address.get("region_2depth_name", "")
                region_3 = road_address.get("region_3depth_name", "")
                
                # 위치 키워드: 시/군/구 또는 읍/면/동 (우선순위: 읍/면/동 > 시/군/구)
                location_keyword = region_3 if region_3 else region_2
                
                return {
                    "location_keyword": location_keyword,
                    "depth_1": region_1,
                    "depth_2": region_2,
                    "depth_3": region_3,
                    "address": road_address.get("address_name", ""),
                }
            else:
                # 지번주소 사용
                region_1 = address.get("region_1depth_name", "")
                region_2 = address.get("region_2depth_name", "")
                region_3 = address.get("region_3depth_name", "")
                region_4 = address.get("region_4depth_name", "")
                
                # 위치 키워드: 읍/면/동 또는 리 (우선순위: 읍/면/동 > 리 > 시/군/구)
                location_keyword = region_3 if region_3 else (region_4 if region_4 else region_2)
                
                return {
                    "location_keyword": location_keyword,
                    "depth_1": region_1,
                    "depth_2": region_2,
                    "depth_3": region_3,
                    "depth_4": region_4,
                    "address": address.get("address_name", ""),
                }
                
    except Exception as e:
        logger.error(f"역지오코딩 실패: {str(e)}", exc_info=True)
        return None

