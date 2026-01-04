# 위치 정보 정규화 및 저장 구조 설계 문서

## 개요

맛집 검색 서비스에서 사용자 입력을 정규화하고, 위치 정보를 계층적으로 저장하여 검색 성능과 정확도를 향상시키기 위한 설계 문서입니다.

## 핵심 요구사항

### 1. 사용자 입력 정규화
- 사용자 입력을 AI + Tool 기반으로 정규화
- "위치 표준명 + 음식(or 카테고리)" 형태로 가공
- "근처 맛집" → 현재 위치 수집
- "역삼 맛집" → 위치 추출 및 표준명 변환

### 2. 계층적 위치 정보 저장
- depth 기반 계층 구조 (1dep ~ 4dep)
- 예: "신철원" → "강원도(1dep) > 철원군(2dep) > 갈말읍(3dep) > 신철원(4dep)"
- 인덱싱 및 검색 성능 최적화

### 3. 구주소/신주소 분리 저장
- 지번주소 (old_address): "지포리 7"
- 도로명주소 (new_address): "강원특별자치도 철원군 갈말읍 명성로139번안길 45 신철원초교"
- 역지오코딩 결과를 그대로 저장

### 4. 사용자 입력 중심 저장
- 사용자가 입력한 내용이 중심 (name, normalized_name)
- 역지오코딩 결과는 보조 정보로 활용
- 주소에 포함된 건물명은 별도 추출하지 않음

### 5. DB 캐싱 전략
- 정규화된 위치 + 음식 조합으로 캐싱
- 동일한 질문 시 DB 조회하여 빠른 응답
- 검색 결과 재사용

## 데이터베이스 스키마

### locations 테이블

```sql
CREATE TABLE locations (
  id INT PRIMARY KEY AUTO_INCREMENT,
  
  -- 사용자 입력 (중심)
  name VARCHAR(255) NOT NULL,  -- 사용자 입력: "신철원초등학교"
  normalized_name VARCHAR(255) UNIQUE NOT NULL,  -- 정규화된 사용자 입력
  
  -- 계층 정보 (역지오코딩 결과의 도로명주소에서 파싱)
  depth_1 VARCHAR(100) NOT NULL,  -- 도/시: "강원특별자치도"
  depth_2 VARCHAR(100) NOT NULL,  -- 시/군/구: "철원군"
  depth_3 VARCHAR(100) NOT NULL,  -- 읍/면/동: "갈말읍"
  depth_4 VARCHAR(100) NULL,      -- 리/동: "지포리" 또는 NULL
  
  -- 주소 정보 (역지오코딩 결과)
  old_address VARCHAR(500) NULL,  -- 지번주소: "지포리 7"
  new_address VARCHAR(500) NULL,  -- 도로명주소: "강원특별자치도 철원군 갈말읍 명성로139번안길 45 신철원초교"
  
  -- 공통 정보
  latitude FLOAT NULL,
  longitude FLOAT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  -- 인덱스
  INDEX idx_normalized_name (normalized_name),
  INDEX idx_depth_composite (depth_1, depth_2, depth_3, depth_4),
  INDEX idx_old_address (old_address),
  INDEX idx_new_address (new_address),
  INDEX idx_coordinates (latitude, longitude),
  FULLTEXT INDEX idx_fulltext_search (name, new_address, old_address)
);
```

### 저장 예시

#### 예시 1: 행정구역 "신철원"
```python
{
  "id": 23,
  "name": "신철원",
  "normalized_name": "신철원",
  "depth_1": "강원특별자치도",
  "depth_2": "철원군",
  "depth_3": "갈말읍",
  "depth_4": "지포리",
  "old_address": "지포리 7",
  "new_address": NULL,
  "latitude": 38.1234,
  "longitude": 127.5678
}
```

#### 예시 2: 건물 "신철원초등학교"
```python
{
  "id": 100,
  "name": "신철원초등학교",
  "normalized_name": "신철원초등학교",
  "depth_1": "강원특별자치도",
  "depth_2": "철원군",
  "depth_3": "갈말읍",
  "depth_4": "지포리",
  "old_address": "지포리 7",
  "new_address": "강원특별자치도 철원군 갈말읍 명성로139번안길 45 신철원초교",
  "latitude": 38.1235,
  "longitude": 127.5679
}
```

## 워크플로우

### 1. 사용자 입력 처리

```
사용자 입력: "신철원초등학교 맛집"
  ↓
AI Agent 분석 (LLM 호출)
  - 입력 분석: "신철원초등학교" = 위치명
  - Tool 호출 결정: normalize_location("신철원초등학교") 필요
  ↓
Tool 실행: normalize_location("신철원초등학교")
  ↓
역지오코딩 API 호출
  - "신철원초등학교" → (lat, lng) 조회
  - 또는 좌표가 있으면 → 역지오코딩
  ↓
역지오코딩 결과 파싱
  - depth_1~4 파싱
  - old_address, new_address 저장
  ↓
locations 테이블에 저장
  - name: "신철원초등학교" (사용자 입력)
  - normalized_name: "신철원초등학교" (정규화된 사용자 입력)
  - depth_1~4: 역지오코딩 결과에서 파싱
  - old_address, new_address: 역지오코딩 결과
  ↓
최종 출력: "위치 표준명 + 음식(or 카테고리)"
```

### 2. Tool 설계

#### Tool 1: `normalize_location(location_name: str) -> str`
```python
def normalize_location(location_name: str) -> dict:
    """
    위치명을 표준명으로 정규화
    
    1. 사전 조회 (빠르고 일관성)
    2. 유사도 매칭 (사전 매칭 실패 시)
    3. 역지오코딩 (최후 수단)
    4. 결과를 사전에 저장 (학습)
    
    Returns:
        {
            "normalized_name": "신철원초등학교",
            "depth_1": "강원특별자치도",
            "depth_2": "철원군",
            "depth_3": "갈말읍",
            "depth_4": "지포리",
            "old_address": "지포리 7",
            "new_address": "강원특별자치도 철원군 갈말읍 명성로139번안길 45 신철원초교",
            "latitude": 38.1235,
            "longitude": 127.5679
        }
    """
```

#### Tool 2: `get_current_location() -> str`
```python
def get_current_location() -> dict:
    """
    사용자의 현재 위치 가져오기 (FE에서 전달된 정보)
    
    Returns:
        현재 위치 정보 (위치 표준명, depth_1~4 등)
    """
```

## 역지오코딩 통합

### API 선택

**카카오 로컬 API (권장)**
- 한국 주소 체계에 최적화
- 상세한 행정구역 정보 제공
- 무료 할당량 제공 (일 300,000건)

### 역지오코딩 결과 파싱

```python
def parse_geocoding_result(api_response: dict) -> dict:
    """
    역지오코딩 결과 파싱
    
    API 응답 예시:
    {
      "documents": [{
        "address": {
          "address_name": "지포리 7",
          "region_1depth_name": "강원특별자치도",
          "region_2depth_name": "철원군",
          "region_3depth_name": "갈말읍",
          "region_4depth_name": "지포리"
        },
        "road_address": {
          "address_name": "강원특별자치도 철원군 갈말읍 명성로139번안길 45 신철원초교",
          "region_1depth_name": "강원특별자치도",
          "region_2depth_name": "철원군",
          "region_3depth_name": "갈말읍",
          "road_name": "명성로139번안길",
          "main_building_no": "45"
        }
      }]
    }
    
    Returns:
        {
            "depth_1": "강원특별자치도",
            "depth_2": "철원군",
            "depth_3": "갈말읍",
            "depth_4": "지포리",
            "old_address": "지포리 7",
            "new_address": "강원특별자치도 철원군 갈말읍 명성로139번안길 45 신철원초교",
            "latitude": 38.1235,
            "longitude": 127.5679
        }
    """
    doc = api_response["documents"][0]
    
    # 지번주소 (구주소)
    address = doc.get("address", {})
    old_address = address.get("address_name", "")
    
    # 도로명주소 (신주소)
    road_address = doc.get("road_address", {})
    new_address = road_address.get("address_name", "") if road_address else None
    
    # depth 파싱 (도로명주소 우선, 없으면 지번주소)
    if road_address:
        depth_1 = road_address.get("region_1depth_name", "")
        depth_2 = road_address.get("region_2depth_name", "")
        depth_3 = road_address.get("region_3depth_name", "")
        depth_4 = road_address.get("region_4depth_name", None) or address.get("region_4depth_name", None)
    else:
        depth_1 = address.get("region_1depth_name", "")
        depth_2 = address.get("region_2depth_name", "")
        depth_3 = address.get("region_3depth_name", "")
        depth_4 = address.get("region_4depth_name", None)
    
    return {
        "depth_1": depth_1,
        "depth_2": depth_2,
        "depth_3": depth_3,
        "depth_4": depth_4,
        "old_address": old_address,
        "new_address": new_address,
        "latitude": doc.get("y", None),
        "longitude": doc.get("x", None)
    }
```

## 검색 로직

### 케이스 1: 사용자 입력으로 검색 (정확 매칭)
```sql
-- "신철원초등학교" 검색 (사용자 입력 중심)
SELECT * FROM locations 
WHERE normalized_name = '신철원초등학교'
OR name LIKE '%신철원초등학교%';
```

### 케이스 2: 검색 실패 → 상위 지역 검색
```sql
-- 1. 사용자 입력으로 검색 실패
SELECT * FROM locations 
WHERE normalized_name = '신철원초등학교';
-- 결과 없음

-- 2. 상위 지역으로 검색 (depth_1~4로 매칭)
-- AI가 "신철원초등학교" → "갈말읍" 또는 "지포리" 추출
SELECT * FROM locations 
WHERE depth_1 = '강원특별자치도' 
AND depth_2 = '철원군' 
AND depth_3 = '갈말읍'
AND (normalized_name NOT LIKE '%초등학교%' OR normalized_name IS NULL);  -- 행정구역만
```

### 케이스 3: 행정구역으로 검색
```sql
-- "신철원 맛집"
SELECT * FROM locations 
WHERE depth_1 = '강원특별자치도' 
AND depth_2 = '철원군' 
AND depth_3 = '갈말읍' 
AND depth_4 = '신철원'
AND (normalized_name NOT LIKE '%초등학교%' OR normalized_name IS NULL);  -- 행정구역만
```

### 케이스 4: 주소로 검색 (보조)
```sql
-- 도로명주소로 검색 (보조적)
SELECT * FROM locations 
WHERE new_address LIKE '%명성로139번안길%';

-- 지번주소로 검색 (보조적)
SELECT * FROM locations 
WHERE old_address LIKE '%지포리%';
```

## DB 캐싱 전략

### search_cache 테이블 (추후 구현)

```sql
CREATE TABLE search_cache (
  id INT PRIMARY KEY AUTO_INCREMENT,
  location_id INT NOT NULL,  -- locations.id 참조
  food_category_id INT NOT NULL,  -- 음식/카테고리 ID
  cache_key VARCHAR(255) UNIQUE NOT NULL,  -- "location_id:food_category_id"
  search_results JSON NOT NULL,  -- 검색 결과
  result_count INT NOT NULL,
  expires_at DATETIME NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  INDEX idx_location_id (location_id),
  INDEX idx_food_category_id (food_category_id),
  INDEX idx_cache_key (cache_key),
  INDEX idx_expires_at (expires_at)
);
```

### 캐시 키 생성
```python
# 정규화된 위치 ID + 음식 카테고리 ID
cache_key = f"{location_id}:{food_category_id}"

# 예시: "100:5" (신철원초등학교 + 삼겹살)
```

## 일관성 보장 전략

### Tool 내부에서 일관성 보장
```python
def normalize_location(location_name: str) -> dict:
    # 1. 사전 조회 (우선순위 1, 일관성 보장)
    canonical = lookup_in_dictionary(location_name)
    if canonical:
        return canonical  # 일관된 결과
    
    # 2. 유사도 매칭 (우선순위 2)
    similar = fuzzy_match(location_name)
    if similar and confidence >= 0.9:
        # 사전에 저장하여 다음엔 일관된 결과
        save_to_dictionary(location_name, similar)
        return similar
    
    # 3. 역지오코딩 (최후 수단)
    geocoded = reverse_geocode(location_name)
    # 사전에 저장하여 다음엔 일관된 결과
    save_to_dictionary(location_name, geocoded)
    return geocoded
```

### 핵심 포인트
- **AI는 Tool 호출 결정만 담당**
- **Tool 내부에서 일관성 보장** (사전 우선, 결과 저장)
- **같은 입력은 사전에서 조회되어 일관된 결과 반환**

## 장점

### 1. 사용자 입력 중심
- 사용자가 입력한 내용이 중심 (name, normalized_name)
- 검색 정확도 향상
- 데이터 일관성

### 2. 계층적 구조
- depth 기반 계층 구조로 인덱싱 효율 향상
- 상위 지역 기반 범위 검색 가능
- 검색 성능 최적화

### 3. 주소 정보 분리
- 구주소와 신주소를 모두 저장
- 다양한 검색 패턴 지원
- 역지오코딩 결과를 그대로 활용

### 4. AI + Tool 기반
- 유연한 입력 처리
- 복잡한 패턴 처리 가능
- 확장성

## 단점 및 고려사항

### 1. 역지오코딩 의존성
- 외부 API 의존 (카카오 로컬 API)
- API 장애 시 위치 정보 저장 불가
- API 비용/할당량 관리 필요

### 2. NULL 처리
- 많은 NULL 컬럼 가능 (행정구역은 new_address NULL)
- 인덱스 효율 저하 가능
- 부분 인덱스 활용 권장

### 3. 중복 가능성
- 같은 건물이 다른 형식으로 저장될 수 있음
- 정규화 필요
- normalized_name으로 중복 방지

## 향후 개선 사항

### 1. 별칭 사전 구축
- location_aliases 테이블 추가
- "역삼" → "역삼동" 매핑
- 자동 학습 메커니즘

### 2. 캐싱 최적화
- 역지오코딩 결과 캐싱
- 검색 결과 캐싱
- TTL 관리

### 3. 성능 최적화
- 부분 인덱스 활용
- 풀텍스트 검색
- 쿼리 최적화

## 참고 사항

- 이 문서는 설계 단계의 문서이며, 실제 구현 시 변경될 수 있습니다.
- 역지오코딩 API는 카카오 로컬 API를 권장하지만, 다른 API도 사용 가능합니다.
- DB는 SQLite로 시작하여 PostgreSQL로 전환하는 것을 권장합니다.

