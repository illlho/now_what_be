# 맛집 정보 수집 및 분석 ReAct AI Agent Service 기획서

**작성일**: 2026-01-10
**작성자**: AI Agent + 사용자
**버전**: 1.0
**문서 유형**: ReAct AI Agent Service 기획

> ⚠️ **중요**: 이 문서는 고정된 워크플로우가 아닌, **도구 기반 ReAct Agent**로 설계된 완전 자율형 AI Agent Service 기획서입니다.

---

## 진행 상태
- [x] 기존 고정 플로우 방식 검토
- [x] ReAct Agent 패러다임으로 전환 결정
- [x] MVP 도구 목록 및 가이드 정의
- [ ] 도구 구현
- [ ] Agent 노드 구현
- [ ] 통합 테스트
- [ ] 자가 개선 메커니즘 구현

---

## 1. 서비스 개요

### 1.1 핵심 아이디어

**기존 방식 (고정 플로우)**:
```
개발자가 미리 정의한 순서대로 실행
validate → search → crawl → analyze → ...
```

**ReAct Agent 방식 (도구 기반)**:
```
AI가 도구를 자율적으로 선택, 조합, 반복
AI: "사용자 요청 분석" → Tool 선택 → 실행 → 판단 → Tool 선택 → ...
```

### 1.2 왜 ReAct Agent인가?

**1. 완전한 자율성**:
- AI가 도구 선택, 순서, 반복 횟수를 스스로 결정
- "가능동 맛집" vs "가능동 삼겹살" → 다른 전략 자동 선택

**2. 무한 확장성**:
- 새로운 도구 추가 = 함수 등록만 하면 됨
- 코드 수정 없이 AI가 자동으로 새 도구 활용

**3. 자가 개선**:
- 프롬프트 개선 → Agent 행동 즉시 변화
- 실패 패턴 학습 → 전략 자동 조정

**4. 사용자 요청 대응력**:
- "가능동 맛집 정리해줘. 회는 제외해" → AI가 카테고리 분해, 제외 처리
- 개발자는 가이드만 제공, 나머지는 AI가 판단

### 1.3 서비스 목표

1. **시간 절약**: 1시간 이상 → 10분 이내
2. **자율 판단**: AI가 충분성, 품질, 연관성을 스스로 판단
3. **확장 용이**: 새로운 요청 → 도구 추가만으로 대응
4. **자가 개선**: 프롬프트 최적화로 성능 지속 향상

---

## 2. ReAct Agent 구조

### 2.1 핵심 구성 요소

```
┌─────────────────────────────────┐
│      사용자 요청                │
│  "가능동 맛집, 회는 제외해"     │
└────────────┬────────────────────┘
             ↓
┌────────────────────────────────────────┐
│  ReAct Agent (단일 AI)                │
│  - 요청 분석                           │
│  - 도구 선택 & 파라미터 결정           │
│  - 결과 평가 & 다음 행동 판단          │
└─────┬──────────────────────────────────┘
      ↓
┌─────────────────────────────────────────┐
│  도구 모음 (Tools)                      │
│  ① search_naver_map                    │
│  ② crawl_blog_links                    │
│  ③ crawl_blog_content                  │
│  ④ reverse_geocode                     │
│  ⑤ analyze_blogs                       │
│  ⑥ terminate                           │
└─────┬───────────────────────────────────┘
      ↓
      결과를 Agent에게 반환 → Agent가 다시 판단
      (순환: Agent ↔ Tools)
```

### 2.2 LangGraph 구조

```python
# 노드 2개만 존재 (매우 단순!)
workflow = StateGraph(AgentState)

# 1. Agent 노드: AI가 도구를 선택
workflow.add_node("agent", agent_node)

# 2. Tools 노드: 선택된 도구 실행
workflow.add_node("tools", tool_node)

# 순환 구조
workflow.add_conditional_edges(
    "agent",
    lambda x: "tools" if x["messages"][-1].tool_calls else END
)
workflow.add_edge("tools", "agent")  # 도구 실행 후 다시 Agent로
```

**특징**:
- 고정된 순서 없음 (Agent가 매번 선택)
- 무한 순환 가능 (제약 조건으로 제어)
- 새 도구 추가 시 노드 수정 불필요

---

## 3. 도구(Tools) 정의

### 3.1 MVP 도구 목록 (6개)

| 번호 | 도구명 | 역할 | 입력 | 출력 |
|------|--------|------|------|------|
| 1 | `search_naver_map` | 네이버 지도 검색 | `query: str, limit: int` | `List[Place]` |
| 2 | `crawl_blog_links` | 블로그 링크 수집 | `place_url: str, limit: int` | `List[str]` |
| 3 | `crawl_blog_content` | 블로그 본문 크롤링 | `blog_url: str` | `str` |
| 4 | `reverse_geocode` | 좌표 → 주소 | `lat: float, lng: float` | `Dict` |
| 5 | `analyze_blogs` | 블로그 분석 (LLM) | `blogs: List[str], keywords: List[str]` | `Dict` |
| 6 | `terminate` | 작업 완료 | `result: Dict` | - |

### 3.2 도구별 상세 정의

#### 1. `search_naver_map`

**역할**: 네이버 지도 API로 장소 검색

**입력**:
```python
{
    "query": "가능동 한식",
    "limit": 5
}
```

**출력**:
```python
[
    {
        "name": "맛있는 한식집",
        "address": "의정부시 가능동 123",
        "naver_map_url": "https://...",
        "category": "한식"
    },
    ...
]
```

**Agent 사용 시나리오**:
- "맛집" 키워드 → 여러 카테고리로 분해 → 각각 검색
- 결과 < 3개 → 위치 범위 확장하여 재검색

---

#### 2. `crawl_blog_links`

**역할**: 네이버 지도 리뷰 탭에서 블로그 링크 수집

**입력**:
```python
{
    "place_url": "https://map.naver.com/...",
    "limit": 5
}
```

**출력**:
```python
[
    "https://blog.naver.com/user1/123",
    "https://blog.naver.com/user2/456",
    ...
]
```

**Agent 사용 시나리오**:
- 장소당 5개 목표
- 부족하면 다른 소스 시도 (추후 구현)

---

#### 3. `crawl_blog_content`

**역할**: 블로그 본문 텍스트 크롤링

**입력**:
```python
{
    "blog_url": "https://blog.naver.com/user1/123"
}
```

**출력**:
```python
"오늘 가능동 한식집 다녀왔어요. 된장찌개가 정말 맛있었고..."
```

**Agent 사용 시나리오**:
- 블로그 링크 받은 후 본문 수집
- 에러 시 해당 블로그 스킵

---

#### 4. `reverse_geocode`

**역할**: 좌표를 주소로 변환 (Kakao Local API)

**입력**:
```python
{
    "latitude": 37.74608637371771,
    "longitude": 127.03254389562254
}
```

**출력**:
```python
{
    "location_keyword": "흥선동",
    "depth_1": "의정부시",
    "depth_2": "흥선동",
    "address": "의정부시 흥선동"
}
```

**Agent 사용 시나리오**:
- 사용자가 위치 키워드 없이 요청 시 사용
- "맛집 추천" + 좌표 → 주소 조회 → "흥선동 음식점" 검색

---

#### 5. `analyze_blogs`

**역할**: 수집된 블로그 분석 (LLM 호출)

**입력**:
```python
{
    "blogs": ["블로그1 본문", "블로그2 본문", ...],
    "keywords": ["한식", "된장찌개"],
    "place_name": "맛있는 한식집"
}
```

**출력**:
```python
{
    "relevance": 0.85,  # 연관성 점수
    "specialty": "된장찌개",
    "scores": {
        "맛": 800,
        "가격": 600,
        "서비스": 700,
        ...
    },
    "summary": "된장찌개 맛집. 가성비 좋음. 주차 불편."
}
```

**Agent 사용 시나리오**:
- 블로그 수집 완료 후 분석
- 연관성 낮으면 해당 장소 제외

---

#### 6. `terminate`

**역할**: 작업 완료 신호 (명시적 종료)

**입력**:
```python
{
    "result": {
        "places": [...],
        "summary": "총 12개 장소 분석 완료"
    }
}
```

**출력**: 워크플로우 종료

**Agent 사용 시나리오**:
- 충분한 정보 수집 및 분석 완료 판단
- 최종 결과 반환

---

## 4. Agent 가이드 (시스템 프롬프트)

### 4.1 전체 가이드

```
당신은 맛집 정보 수집 및 분석 전문 AI Agent입니다.

[목표]
사용자의 요청에 따라 맛집 정보를 자율적으로 수집, 분석, 정리합니다.

[사용 가능한 도구]
1. search_naver_map: 네이버 지도에서 장소 검색
2. crawl_blog_links: 네이버 지도 리뷰 탭에서 블로그 링크 수집
3. crawl_blog_content: 블로그 본문 크롤링
4. reverse_geocode: 좌표를 주소로 변환
5. analyze_blogs: 블로그 분석 (연관성, 특색, 점수)
6. terminate: 작업 완료

[기본 전략]
1. 사용자 요청 분석
   - 위치 키워드 추출 (없으면 reverse_geocode 사용)
   - 음식 키워드 추출 ("맛집"이면 3-5개 카테고리로 분해)
   - 제외 키워드 확인

2. 장소 검색
   - 카테고리당 3-5개 장소 검색
   - 결과 < 3개면 위치 범위 확대 재검색 (1회)
   
3. 블로그 수집
   - 장소당 5개 블로그 목표
   - 부족해도 진행 (있는 만큼)
   
4. 블로그 분석
   - 연관성 평가 (키워드 일치도)
   - 특색 파악 (공통 언급 메뉴/요소)
   - 점수 산정 (맛/가격/서비스/양/웨이팅)
   
5. 결과 정리
   - 통과 장소만 포함
   - 카테고리별 태그
   - 종합 점수 순 정렬
   - terminate 호출

[제약 조건]
- 최대 도구 호출: 20회
- 최대 장소 수: 15개
- 타임아웃: 10분
- 제약 초과 시 현재까지 결과로 terminate

[특별 규칙]
- "맛집" 키워드: 한식/중식/일식/양식/카페 등 3-5개로 분해
- 제외 키워드: 해당 카테고리 검색 제외 (예: "회 제외" → 일식 제외)
- 위치 없음: reverse_geocode로 좌표 → 주소 변환
- 음식 없음: "음식점"으로 기본 설정
```

### 4.2 예시 시나리오

**입력**: "가능동 맛집 정리해줘. 회는 제외해"

**Agent 사고 과정**:
```
[분석]
- 위치: "가능동"
- 음식: "맛집" → 카테고리 분해 필요
- 제외: "회" → 일식 제외

[계획]
1. 카테고리 결정: 한식, 중식, 양식, 카페 (일식 제외)
2. 각 카테고리별 검색
3. 블로그 수집 및 분석
4. 결과 정리

[실행]
Tool 1: search_naver_map("가능동 한식", limit=3)
  → 결과: [장소1, 장소2, 장소3]
  
Tool 2: search_naver_map("가능동 중식", limit=3)
  → 결과: [장소4, 장소5] (2개만)
  
Tool 3: search_naver_map("가능동 양식", limit=3)
  → 결과: [장소6, 장소7, 장소8]
  
Tool 4: search_naver_map("가능동 카페", limit=3)
  → 결과: [장소9, 장소10]
  
[판단] 총 10개 장소. 충분. 블로그 수집 시작.

Tool 5: crawl_blog_links(장소1)
  → 결과: [블로그1, 블로그2, 블로그3, 블로그4, 블로그5]
  
Tool 6: crawl_blog_content(블로그1)
  → 결과: "본문..."
  
... (반복)

Tool N: analyze_blogs(...)
  → 결과: {relevance: 0.9, scores: {...}}
  
[최종 판단] 충분한 정보 수집. 분석 완료.

Tool 20: terminate(result={...})
```

---

## 5. 상태(State) 설계

### 5.1 AgentState 구조

```python
class AgentState(TypedDict):
    """ReAct Agent 상태"""
    
    # 대화 메시지 (LangChain 표준)
    messages: Annotated[list, add_messages]
    
    # 사용자 요청 정보
    user_query: str
    user_location: Optional[Dict[str, float]]  # {latitude, longitude}
    
    # Agent 수집 데이터
    places: List[Dict[str, Any]]  # 검색된 장소 목록
    blog_links: Dict[str, List[str]]  # {place_name: [blog_urls]}
    blog_contents: Dict[str, str]  # {blog_url: content}
    analysis_results: Dict[str, Dict]  # {place_name: analysis}
    
    # 실행 제어
    tool_call_count: int  # 도구 호출 횟수
    start_time: float  # 시작 시간
    done: bool  # 완료 여부
    
    # 최종 결과
    final_result: Optional[Dict[str, Any]]
```

### 5.2 상태 흐름

```
초기 상태:
{
    messages: [HumanMessage("가능동 맛집")],
    user_query: "가능동 맛집",
    places: [],
    tool_call_count: 0,
    done: False
}

↓ Agent 도구 선택

{
    messages: [..., AIMessage(tool_calls=[search_naver_map])],
    tool_call_count: 1
}

↓ Tool 실행

{
    messages: [..., ToolMessage(content="[장소1, ...]")],
    places: [장소1, 장소2, ...],
    tool_call_count: 1
}

↓ Agent 다시 판단 → Tool 선택 → ... (반복)

↓ terminate 호출

{
    done: True,
    final_result: {...}
}
```

---

## 6. MVP 제약 조건

### 6.1 비용/시간 제어

| 제약 | 값 | 이유 |
|------|-------|------|
| 최대 도구 호출 | 20회 | 무한루프 방지, 비용 통제 |
| 최대 장소 수 | 15개 | 블로그 75개 = 적절한 분석량 |
| 타임아웃 | 10분 | 사용자 대기 한계 |
| 장소당 블로그 | 5개 | 품질 vs 속도 균형 |

### 6.2 안전장치

```python
def agent_node(state: AgentState) -> AgentState:
    # 1. 도구 호출 횟수 제한
    if state["tool_call_count"] >= 20:
        return {
            "messages": [AIMessage(content="최대 호출 횟수 도달")],
            "done": True
        }
    
    # 2. 타임아웃 체크
    elapsed = time.time() - state["start_time"]
    if elapsed > 600:  # 10분
        return {
            "messages": [AIMessage(content="타임아웃")],
            "done": True
        }
    
    # 3. 정상 실행
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}
```

---

## 7. 자가 개선 메커니즘

### 7.1 프롬프트 최적화

**현재 성과 추적**:
- 성공률 (완료/실패)
- 평균 도구 호출 횟수
- 평균 소요 시간
- 사용자 만족도

**개선 사이클**:
```
1주차: 기본 가이드 프롬프트 사용
  → 성공률 70%, 평균 15회 호출

2주차: 프롬프트 개선 ("블로그 5개면 충분" 명시)
  → 성공률 80%, 평균 12회 호출

3주차: 재검색 전략 개선 ("depth_3 → depth_2")
  → 성공률 85%, 평균 10회 호출
```

### 7.2 실패 패턴 학습

**실패 로그 수집**:
```json
{
    "user_query": "가능동 맛집",
    "failure_reason": "검색 결과 0개",
    "tool_calls": ["search_naver_map('가능동 맛집')"],
    "suggestion": "카테고리 분해 필요"
}
```

**프롬프트 업데이트**:
```
[개선 전]
"맛집"을 적절히 처리하세요.

[개선 후]
"맛집" 키워드는 반드시 3-5개 카테고리로 분해하세요.
예: "가능동 맛집" → "가능동 한식", "가능동 중식", ...
```

### 7.3 도구 사용 패턴 분석

**통계 수집**:
- 가장 많이 사용되는 도구
- 도구 조합 패턴
- 성공률이 높은 순서

**예시**:
```
패턴 A: search → crawl_links → crawl_content → analyze
  성공률: 85%
  
패턴 B: search → search → crawl_links → analyze
  성공률: 65% (블로그 수집 생략 시 품질 저하)
  
→ 가이드 업데이트: "반드시 블로그 수집 후 분석"
```

---

## 8. 기존 고정 플로우와의 비교

| 항목 | 고정 플로우 | ReAct Agent |
|------|-------------|-------------|
| 노드 수 | 9개 (validate, search, crawl, ...) | **2개** (agent, tools) |
| 조건부 엣지 | 6개 (개발자가 하드코딩) | **1개** (AI가 판단) |
| 새 요청 대응 | 코드 수정 필요 | **프롬프트만 수정** |
| 확장성 | 노드 추가 = 코드 수정 | **도구 추가 = 함수 등록** |
| 자가 개선 | 불가능 (플로우 고정) | **가능** (프롬프트 개선) |
| Agent다움 | 60점 (판단만, 행동 고정) | **95점** (완전 자율) |
| 개발 복잡도 | 높음 | **낮음** |
| 유지보수 | 분기 추가마다 수정 | **거의 없음** |

---

## 9. 구현 계획

### 9.1 Phase 1: 도구 구현 (2-3일)

**우선순위**:
1. ✅ `reverse_geocode` (기존 코드 재사용)
2. 🔧 `search_naver_map` (네이버 지도 API)
3. 🔧 `crawl_blog_links` (셀레니움/httpx)
4. 🔧 `crawl_blog_content` (BeautifulSoup)
5. 🔧 `analyze_blogs` (LLM 호출)
6. 🔧 `terminate` (상태 업데이트)

### 9.2 Phase 2: Agent 구현 (1-2일)

1. AgentState 정의
2. agent_node 구현 (LLM with tools)
3. tool_node 구현 (도구 실행)
4. 워크플로우 연결
5. 안전장치 추가

### 9.3 Phase 3: 테스트 (1-2일)

**테스트 케이스**:
1. "가능동 삼겹살" (단순)
2. "가능동 맛집" (카테고리 분해)
3. "가능동 맛집, 회는 제외" (제외 조건)
4. "맛집 추천" (위치 없음, 좌표만)

### 9.4 Phase 4: 자가 개선 (지속)

- 실패 로그 수집
- 프롬프트 개선
- 성능 모니터링

---

## 10. 성공 지표

### 10.1 기능 지표

| 지표 | 목표 |
|------|------|
| 작업 완료율 | 85% 이상 |
| 평균 소요 시간 | 10분 이내 |
| 평균 도구 호출 | 15회 이하 |
| 타임아웃율 | 5% 이하 |

### 10.2 품질 지표

| 지표 | 목표 |
|------|------|
| 연관성 정확도 | 80% 이상 |
| 특색 파악 정확도 | 70% 이상 |
| 사용자 만족도 | 4.0/5.0 이상 |

---

## 11. 향후 확장 계획

### 11.1 도구 추가

- `search_instagram`: 인스타그램 검색
- `search_youtube`: 유튜브 리뷰 검색
- `ocr_menu`: 메뉴판 OCR (가격 추출)
- `get_user_preference`: 사용자 선호도 조회

### 11.2 Agent 다중화

```
[Master Agent]
  ├─ [Search Agent] (장소 검색 전문)
  ├─ [Crawl Agent] (크롤링 전문)
  └─ [Analysis Agent] (분석 전문)
```

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 | 작성자 |
|------|------|-----------|--------|
| 2026-01-10 | 1.0 | ReAct Agent 기획서 작성 (고정 플로우 방식 폐기) | AI Agent + 사용자 |

---

## 다음 단계

**즉시**: 도구 6개 구현 시작
1. `search_naver_map`
2. `crawl_blog_links`
3. `crawl_blog_content`
4. `analyze_blogs`
5. `terminate`
