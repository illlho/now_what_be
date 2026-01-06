"""지오코딩 유틸리티

좌표를 주소로 변환하는 역지오코딩 기능을 제공합니다.
OpenStreetMap Nominatim API를 사용합니다. (API 키 불필요)
"""

import logging
import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


async def reverse_geocode(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
    """
    좌표를 주소로 변환 (역지오코딩)
    
    OpenStreetMap Nominatim API를 사용하여 좌표를 주소로 변환합니다.
    API 키가 필요 없으며, User-Agent 헤더만 설정하면 됩니다.
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
    logger.info(f"OpenStreetMap Nominatim 역지오코딩 시작: 좌표 ({latitude}, {longitude})")
    
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "format": "jsonv2",
            "lat": str(latitude),
            "lon": str(longitude),
            "zoom": "18",
            "addressdetails": "1",
        }
        
        # OpenStreetMap Nominatim은 User-Agent 헤더가 필수입니다.
        # API 키는 필요 없지만, 사용자 식별을 위해 User-Agent를 설정해야 합니다.
        # 주의: User-Agent는 ASCII만 허용되므로 한글을 포함할 수 없습니다.
        headers = {
            "Accept": "application/json",
            "Accept-Language": "ko",
            "User-Agent": "NowWhatBackend/1.0",  # 필수: User-Agent 설정 (ASCII만 허용)
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=headers)
            
            if not response.is_success:
                error_text = response.text[:500] if response.text else "응답 없음"
                logger.error(f"OpenStreetMap 역지오코딩 API 오류: {response.status_code} - {error_text}")
                return None
            
            logger.info(f"OpenStreetMap API 응답 성공: {response.status_code}")
            
            json_data = response.json()
            
            # OpenStreetMap 응답 구조:
            # address: {country, state, city, town, village, suburb, city_district, road 등}
            # display_name: 전체 주소 문자열
            
            address = json_data.get("address", {})
            display_name = json_data.get("display_name", "")
            
            logger.info(f"OpenStreetMap 응답: address keys = {list(address.keys()) if address else 'None'}, display_name = {display_name[:100]}")
            
            if not address and not display_name:
                logger.warning(f"역지오코딩 결과가 없습니다. 좌표: ({latitude}, {longitude})")
                return None
            
            # 한국 주소 체계에 맞게 파싱
            # OpenStreetMap 한국 주소 구조:
            # - city: "서울특별시" (시/도)
            # - borough: "중구" (구)
            # - suburb: "명동" (동)
            # - quarter: "태평로1가" (상세 지역)
            
            # 시/도: city (한국에서는 city가 시/도를 의미)
            depth_1 = address.get("city", "") or address.get("state", "") or address.get("region", "")
            
            # 시/군/구: borough (구) 또는 county (군)
            depth_2 = address.get("borough", "") or address.get("city_district", "") or address.get("county", "")
            
            # 읍/면/동: suburb (동) > town (읍) > village (면)
            depth_3 = address.get("suburb", "") or address.get("town", "") or address.get("village", "")
            
            # 리/동: quarter (상세 지역) 또는 neighbourhood
            depth_4 = address.get("quarter", "") or address.get("neighbourhood", "")
            
            # 위치 키워드: 읍/면/동 > 리 > 시/군/구 (우선순위)
            location_keyword = depth_3 if depth_3 else (depth_4 if depth_4 else depth_2)
            
            # location_keyword가 없으면 display_name에서 추출 시도
            if not location_keyword and display_name:
                # display_name에서 한국 주소 패턴 추출 시도
                # 예: "대한민국 서울특별시 중구 명동" -> "명동" 또는 "중구"
                parts = display_name.split(",")
                for part in reversed(parts):
                    part = part.strip()
                    # "구" 또는 "동"으로 끝나는 부분 찾기
                    if part.endswith("구") or part.endswith("동") or part.endswith("읍") or part.endswith("면"):
                        location_keyword = part
                        if part.endswith("구"):
                            depth_2 = part
                        elif part.endswith("동") or part.endswith("읍") or part.endswith("면"):
                            depth_3 = part
                        break
                    # "시"로 끝나는 경우도 처리
                    elif part.endswith("시") and not depth_1:
                        depth_1 = part
            
            # 주소 문자열 생성
            address_parts = [depth_1, depth_2, depth_3]
            if depth_4:
                address_parts.append(depth_4)
            address_str = " ".join([part for part in address_parts if part]) or display_name
            
            result = {
                "location_keyword": location_keyword,
                "depth_1": depth_1,
                "depth_2": depth_2,
                "depth_3": depth_3,
                "depth_4": depth_4,
                "address": address_str,
            }
            
            logger.info(f"✅ 역지오코딩 성공: {location_keyword} (주소: {address_str[:50]})")
            return result
                
    except Exception as e:
        logger.error(f"역지오코딩 실패: {str(e)}", exc_info=True)
        return None

