# 데이터 준비 워크플로우 문서

## 개요

맛집 검색 서비스의 Agentic Workflow에서 Document Parsing/Understanding과 VectorDB를 효과적으로 활용하기 위한 데이터 사전 준비 작업 워크플로우입니다.

이 문서는 데이터 수집부터 벡터화 저장, 키워드 인덱스 구축까지의 전체 프로세스를 정의합니다.

---

## 목차

1. [전체 워크플로우 개요](#전체-워크플로우-개요)
2. [Phase 1: 데이터 수집](#phase-1-데이터-수집)
3. [Phase 2: 데이터 가공 및 품질 관리](#phase-2-데이터-가공-및-품질-관리)
4. [Phase 3: 키워드 추출 및 인덱스 구축](#phase-3-키워드-추출-및-인덱스-구축)
5. [Phase 4: 예상 질문 생성 및 벡터화](#phase-4-예상-질문-생성-및-벡터화)
6. [Phase 5: 문서 벡터화 및 VectorDB 저장](#phase-5-문서-벡터화-및-vectordb-저장)
7. [기술 스택 제안](#기술-스택-제안)
8. [구현 순서 및 우선순위](#구현-순서-및-우선순위)

---

## 전체 워크플로우 개요

```
┌─────────────────────────────────────────────────────────────┐
│                    데이터 준비 워크플로우                      │
└─────────────────────────────────────────────────────────────┘

Phase 1: 데이터 수집
    ↓
Phase 2: 데이터 가공 및 품질 관리
    ↓
Phase 3: 키워드 추출 및 인덱스 구축
    ↓
Phase 4: 예상 질문 생성 및 벡터화
    ↓
Phase 5: 문서 벡터화 및 VectorDB 저장
    ↓
    완료 → Agentic Workflow에서 활용 가능
```

---

## Phase 1: 데이터 수집

### 1.1 수집 대상 소스

#### 네이버 블로그/카페
- **대상**: 맛집 리뷰, 추천 글
- **수집 방법**: 
  - 네이버 검색 API 또는 크롤링
  - 블로그 포스트 본문, 이미지, 댓글
- **수집 주기**: 일일/주간 배치
- **예상 데이터량**: 수천 ~ 수만 건/일

#### 네이버지도
- **대상**: 맛집 기본 정보, 리뷰, 평점
- **수집 방법**: 네이버지도 API
- **수집 항목**:
  - 맛집명, 주소, 전화번호
  - 영업시간, 메뉴 정보
  - 평점, 리뷰 수
  - 위치 좌표
- **수집 주기**: 주간 배치 (변경사항 위주)

#### 웹 검색 결과
- **대상**: 구글, 다음 등 검색 결과
- **수집 방법**: 검색 API 또는 크롤링
- **수집 항목**: 검색 결과 스니펫, 링크, 요약 정보

### 1.2 데이터 저장 형식 (Raw Data)

```json
{
  "source": "naver_blog",
  "source_id": "blog_12345",
  "url": "https://blog.naver.com/...",
  "title": "강남역 파스타 맛집 추천",
  "content": "강남역 근처에 있는 파스타집을 소개합니다...",
  "images": [
    {
      "url": "https://...",
      "alt_text": "파스타 사진",
      "needs_ocr": true
    }
  ],
  "author": "블로거명",
  "published_date": "2024-01-15",
  "metadata": {
    "view_count": 1234,
    "like_count": 56,
    "comment_count": 12
  },
  "collected_at": "2024-12-31T10:00:00Z"
}
```

### 1.3 수집 파이프라인 구조

```
[크롤러/API] → [데이터 검증] → [Raw Data Storage]
     ↓
[에러 처리] → [재시도 로직] → [로깅/모니터링]
```

---

## Phase 2: 데이터 가공 및 품질 관리

### 2.1 데이터 정제 작업

#### 텍스트 정제
- **불필요한 수식어 제거**: "정말 맛있는", "완전 추천" 등
- **광고 문구 제거**: "무료배송", "이벤트 진행 중" 등
- **HTML 태그 제거**: 크롤링된 HTML 정제
- **특수문자 정규화**: 공백, 줄바꿈 정리

#### 위치 정보 표준화
- **목표**: 다양한 표현을 표준 형식으로 통일
- **예시**:
  - "강남구", "강남", "강남역 근처", "강남역 5분 거리" → `{"region": "강남구", "landmark": "강남역"}`
  - "홍대입구역", "홍대", "홍익대 앞" → `{"region": "마포구", "landmark": "홍대입구역"}`

#### 메뉴 정보 구조화
- **비정형 텍스트에서 메뉴 추출**:
  - "크림파스타 15,000원" → `{"name": "크림파스타", "price": 15000}`
  - "스테이크 세트 35,000원" → `{"name": "스테이크 세트", "price": 35000}`

#### 평점/리뷰 정보 정규화
- **평점 통일**: 5점 만점, 10점 만점 등 → 5점 만점으로 통일
- **리뷰 수 정규화**: "100개+", "많음" 등 → 숫자로 변환

### 2.2 이미지 처리 (OCR, VLM)

#### OCR 처리
- **대상**: 메뉴판, 가격표 이미지
- **작업**:
  - 이미지에서 텍스트 추출
  - 메뉴명, 가격 정보 파싱
  - 구조화된 데이터로 변환

#### VLM (Vision Language Model) 처리
- **대상**: 음식 사진, 인테리어 사진
- **작업**:
  - 음식 종류 인식: "크림파스타", "피자" 등
  - 분위기 분석: "로맨틱한", "캐주얼한" 등
  - 인테리어 스타일: "모던한", "빈티지한" 등

### 2.3 데이터 품질 검증

#### 필수 필드 검증
- 위치 정보 존재 여부
- 음식 종류/메뉴 정보 존재 여부
- 본문 내용 최소 길이 (예: 50자 이상)

#### 중복 데이터 제거
- URL 기반 중복 제거
- 내용 유사도 기반 중복 제거 (임베딩 유사도 활용)

#### 데이터 품질 점수 계산
```python
quality_score = (
    has_location * 0.3 +
    has_food_type * 0.3 +
    content_length_score * 0.2 +
    has_images * 0.1 +
    has_rating * 0.1
)
```

### 2.4 가공된 데이터 구조

```json
{
  "document_id": "processed_blog_12345",
  "source": "naver_blog",
  "source_id": "blog_12345",
  "title": "강남역 파스타 맛집 추천",
  "content": "정제된 본문 내용...",
  "structured_data": {
    "location": {
      "region": "강남구",
      "landmark": "강남역",
      "address": "서울시 강남구 테헤란로 123",
      "coordinates": {"lat": 37.4980, "lng": 127.0276}
    },
    "food_type": "파스타",
    "menu_items": [
      {"name": "크림파스타", "price": 15000},
      {"name": "토마토파스타", "price": 14000}
    ],
    "keywords": ["강남", "파스타", "데이트", "가성비"],
    "atmosphere": ["로맨틱한", "조용한"],
    "rating": 4.5,
    "review_count": 123
  },
  "images": [
    {
      "url": "https://...",
      "extracted_text": "크림파스타 15,000원",  // OCR 결과
      "vlm_analysis": {
        "food_type": "크림파스타",
        "atmosphere": "로맨틱한"
      }
    }
  ],
  "quality_score": 0.95,
  "processed_at": "2024-12-31T11:00:00Z"
}
```

---

## Phase 3: 키워드 추출 및 인덱스 구축

### 3.1 키워드 추출 방법

#### 자동 추출
- **명사 추출**: KoNLPy, Mecab 등을 사용한 형태소 분석
- **핵심 키워드 추출**: TF-IDF, TextRank 등
- **엔티티 인식**: 위치명, 음식명, 브랜드명 등

#### 수동 구축
- **동의어/유의어 사전**:
  ```
  파스타 = 스파게티, 이탈리안
  가성비 = 저렴한, 합리적인, 싼
  데이트 = 커플, 로맨틱한
  ```

#### 키워드 카테고리화
- **위치 키워드**: 강남, 홍대, 이태원 등
- **음식 종류**: 파스타, 한식, 일식, 카페 등
- **특징 키워드**: 가성비, 분위기, 데이트, 혼밥 등
- **가격대 키워드**: 저렴한, 보통, 비싼 등

### 3.2 키워드 인덱스 구축

#### 역색인(Inverted Index) 구조
```
키워드 → [문서 ID 리스트]

예시:
"강남" → [doc_1, doc_2, doc_3, doc_15, ...]
"파스타" → [doc_1, doc_5, doc_7, doc_12, ...]
"가성비" → [doc_1, doc_4, doc_9, doc_20, ...]
```

#### 키워드-문서 매핑 메타데이터
```json
{
  "keyword": "강남",
  "documents": [
    {
      "doc_id": "doc_1",
      "frequency": 5,  // 문서 내 출현 빈도
      "positions": [10, 45, 120],  // 출현 위치
      "importance": 0.8  // 키워드 중요도
    }
  ],
  "synonyms": ["강남구", "강남역"],
  "category": "location"
}
```

#### 키워드 검색 최적화
- **부울 검색 지원**: AND, OR, NOT 연산
- **구문 검색**: "강남 파스타" 같은 구문 검색
- **유사 키워드 확장**: "파스타" 검색 시 "스파게티"도 포함

### 3.3 키워드 인덱스 저장

#### 저장소 옵션
- **Elasticsearch**: 전문 검색 엔진, 역색인 최적화
- **Redis**: 빠른 키워드 조회용 캐시
- **PostgreSQL**: 관계형 데이터로 저장 (GIN 인덱스 활용)

---

## Phase 4: 예상 질문 생성 및 벡터화

### 4.1 예상 질문 생성 방법

#### 패턴 기반 생성
- **템플릿 활용**:
  ```
  "{location} {food_type} 맛집"
  "{location} 가성비 좋은 {food_type}"
  "{location} 데이트하기 좋은 {food_type}집"
  "{location} {food_type} 추천"
  ```

#### LLM 기반 생성
- **프롬프트 예시**:
  ```
  주어진 맛집 정보를 바탕으로 사용자가 할 수 있는 질문을 10개 생성하세요.
  
  맛집 정보:
  - 위치: 강남
  - 음식: 파스타
  - 특징: 가성비 좋음, 데이트하기 좋음
  
  생성된 질문:
  1. "강남 파스타 맛집 추천"
  2. "강남 가성비 좋은 파스타집"
  3. "강남 데이트하기 좋은 파스타집"
  ...
  ```

#### 실제 사용자 질문 수집
- **로그 분석**: 실제 사용자 질문 패턴 수집
- **자주 묻는 질문(FAQ)**: 빈도 높은 질문 우선 생성

### 4.2 질문-문서 매핑

#### 매핑 방법
- **수동 매핑**: 각 예상 질문에 가장 적합한 문서 할당
- **자동 매핑**: 
  - 문서 내용과 질문 유사도 계산
  - 유사도 임계값 이상인 문서 매핑

#### 매핑 데이터 구조
```json
{
  "expected_query_id": "eq_001",
  "query": "강남 파스타 맛집 추천",
  "query_variations": [
    "강남 파스타 맛집",
    "강남 파스타집",
    "강남 파스타 추천"
  ],
  "mapped_documents": [
    {
      "doc_id": "doc_1",
      "relevance_score": 0.95,
      "mapping_reason": "강남 지역, 파스타 전문, 높은 평점"
    },
    {
      "doc_id": "doc_5",
      "relevance_score": 0.88,
      "mapping_reason": "강남 지역, 파스타 메뉴 있음"
    }
  ],
  "embedding": [0.123, 0.456, ...]  // 질문 임베딩
}
```

### 4.3 예상 질문 벡터화

#### 임베딩 생성
- **모델 선택**: 
  - 한국어 특화: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
  - 또는 OpenAI `text-embedding-3-small`
- **벡터 차원**: 384 또는 1536 차원

#### 벡터 저장
- **VectorDB에 저장**: 예상 질문과 문서를 함께 저장
- **메타데이터 포함**: 질문 카테고리, 매핑된 문서 ID 등

---

## Phase 5: 문서 벡터화 및 VectorDB 저장

### 5.1 문서 임베딩 생성

#### 임베딩 대상 텍스트 구성
```python
embedding_text = f"""
{title}
{content}
위치: {location}
음식 종류: {food_type}
특징: {', '.join(keywords)}
"""
```

#### 임베딩 모델
- **한국어 특화 모델**: 
  - `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
  - `jhgan/ko-sroberta-multitask`
- **OpenAI 모델**: `text-embedding-3-small` (유료)

### 5.2 VectorDB 선택 및 설정

#### 추천 VectorDB 옵션

##### Pinecone (클라우드)
- **장점**: 관리형 서비스, 확장성 좋음
- **단점**: 유료, 데이터가 클라우드에 저장
- **적용**: 프로덕션 환경

##### Weaviate (오픈소스)
- **장점**: 오픈소스, GraphQL API, 자체 임베딩 지원
- **단점**: 자체 호스팅 필요
- **적용**: 온프레미스 환경

##### Qdrant (오픈소스)
- **장점**: 빠른 성능, Rust 기반, REST API
- **단점**: 자체 호스팅 필요
- **적용**: 고성능이 필요한 경우

##### Chroma (오픈소스)
- **장점**: 간단한 설정, Python 친화적
- **단점**: 대규모 데이터 처리 시 성능 제한
- **적용**: 프로토타입, 소규모 데이터

### 5.3 데이터 저장 구조

#### VectorDB 저장 형식
```json
{
  "id": "doc_1",
  "vector": [0.123, 0.456, ...],  // 384차원 또는 1536차원
  "metadata": {
    "source": "naver_blog",
    "title": "강남역 파스타 맛집 추천",
    "location": "강남구",
    "food_type": "파스타",
    "keywords": ["강남", "파스타", "가성비"],
    "rating": 4.5,
    "quality_score": 0.95,
    "processed_at": "2024-12-31T11:00:00Z"
  },
  "payload": {
    "content": "전체 본문 내용...",
    "structured_data": {...}
  }
}
```

#### 인덱스 설정
- **인덱스 타입**: HNSW (Hierarchical Navigable Small World)
- **차원 수**: 임베딩 모델에 맞게 설정
- **거리 메트릭**: Cosine Similarity (권장)

### 5.4 벡터 검색 최적화

#### 하이브리드 검색 전략
- **벡터 검색**: 의미 기반 유사도 검색
- **키워드 검색**: 정확한 키워드 매칭
- **결합 방법**: 
  - Reciprocal Rank Fusion (RRF)
  - 가중치 기반 결합

#### 필터링 지원
- **메타데이터 필터**: 위치, 음식 종류 등으로 필터링
- **범위 필터**: 평점, 가격대 등

---

## 기술 스택 제안

### 데이터 수집
- **크롤링**: Scrapy, BeautifulSoup, Selenium
- **API**: 네이버 검색 API, 네이버지도 API
- **스케줄링**: Airflow, Celery

### 데이터 가공
- **텍스트 처리**: KoNLPy, Mecab, spaCy
- **OCR**: Tesseract, PaddleOCR, Google Vision API
- **VLM**: GPT-4 Vision, Claude Vision, LLaVA

### 키워드 인덱스
- **검색 엔진**: Elasticsearch (권장)
- **캐시**: Redis
- **데이터베이스**: PostgreSQL (GIN 인덱스)

### 벡터화
- **임베딩 모델**: 
  - `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
  - OpenAI `text-embedding-3-small`
- **벡터화 라이브러리**: sentence-transformers, openai

### VectorDB
- **프로덕션**: Pinecone (클라우드) 또는 Weaviate (온프레미스)
- **프로토타입**: Chroma

### 파이프라인 오케스트레이션
- **Airflow**: 배치 작업 스케줄링
- **Celery**: 비동기 작업 처리

---

## 구현 순서 및 우선순위

### Phase 1: MVP (Minimum Viable Product)
1. **데이터 수집** (네이버 블로그, 네이버지도)
2. **기본 데이터 가공** (텍스트 정제, 위치 표준화)
3. **문서 벡터화 및 VectorDB 저장** (Chroma 사용)
4. **기본 키워드 추출** (명사 추출)

**예상 기간**: 2-3주

### Phase 2: 품질 개선
1. **데이터 품질 검증 강화**
2. **키워드 인덱스 구축** (Elasticsearch)
3. **예상 질문 생성 및 매핑** (패턴 기반)
4. **하이브리드 검색 구현**

**예상 기간**: 2-3주

### Phase 3: 고도화
1. **OCR/VLM 통합** (이미지 처리)
2. **LLM 기반 예상 질문 생성**
3. **VectorDB 최적화** (Pinecone 또는 Weaviate로 마이그레이션)
4. **파이프라인 자동화** (Airflow)

**예상 기간**: 3-4주

---

## 데이터 품질 지표

### 수집 단계
- 수집 성공률: > 95%
- 데이터 완전성: 필수 필드 존재율 > 90%

### 가공 단계
- 위치 정보 추출률: > 85%
- 음식 종류 추출률: > 80%
- 품질 점수 평균: > 0.7

### 검색 단계
- 벡터 검색 정확도 (Recall@10): > 0.8
- 키워드 검색 정확도: > 0.9
- 하이브리드 검색 정확도: > 0.85

---

## 모니터링 및 유지보수

### 데이터 품질 모니터링
- 일일 데이터 수집량 추이
- 데이터 품질 점수 분포
- 검색 성능 지표 (응답 시간, 정확도)

### 주기적 업데이트
- **데이터 수집**: 일일/주간 배치
- **벡터 인덱스 재구축**: 월간 (또는 데이터 변경량에 따라)
- **예상 질문 업데이트**: 분기별
- **키워드 사전 업데이트**: 수시 (새로운 트렌드 반영)

---

## 참고 자료

- [LangChain Vector Stores](https://python.langchain.com/docs/modules/data_connection/vectorstores/)
- [sentence-transformers Documentation](https://www.sbert.net/)
- [Elasticsearch Guide](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Airflow Documentation](https://airflow.apache.org/docs/)

---

## 문서 버전

- **버전**: 1.0
- **작성일**: 2024-12-31
- **최종 수정일**: 2024-12-31

