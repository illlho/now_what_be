"""LLM 관련 유틸리티 함수들

모델 호출 및 LLM 관련 헬퍼 함수들을 정의합니다.
"""

from typing import Optional, TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json
import logging

logger = logging.getLogger(__name__)

# 전역 모델 인스턴스 (필요시 초기화)
_model: Optional[ChatOpenAI] = None



def get_model() -> ChatOpenAI:
    """LLM 모델 인스턴스 반환 (싱글톤 패턴)"""
    global _model
    if _model is None:
        _model = ChatOpenAI(model="gpt-4o-mini")
    return _model


def get_query_evaluation_system_prompt() -> str:
    """맛집 검색 쿼리 평가를 위한 시스템 프롬프트 (CoT, ReAct 기법 활용)"""
    return """당신은 맛집 검색 쿼리를 평가하는 전문 AI 어시스턴트입니다.

## 평가 프로세스 (Chain of Thought + ReAct)

다음 단계를 순차적으로 수행하세요:

### 1단계: 관찰 (Observation)
- 사용자 입력의 전체 맥락을 파악합니다
- 입력의 의도와 목적을 분석합니다
- 포함된 키워드와 정보를 추출합니다

### 2단계: 추론 (Reasoning)
다음 항목들을 체크합니다:

**2.1 맛집 검색 관련성 평가**
- 맛집, 음식, 식당, 카페, 레스토랑 등과 관련된 내용인가?
- 음식 주문, 맛집 추천, 식당 정보 요청 등 맛집 검색 목적이 있는가?

**2.2 부적절성 검사**
- 욕설, 비방, 불법적 내용이 포함되어 있는가?
- 맛집 검색과 전혀 무관한 질문인가? (예: 날씨, 뉴스, 일반 대화 등)

**2.3 정보 완전성 분석**
- 어디서(위치): 지역명, 구/동 이름, 랜드마크 등 위치 정보가 있는가?
- 무엇을(음식 종류/메뉴): 음식 종류, 메뉴, 식당 유형 등 검색 항목이 있는가?
- 추가 조건: 가격대, 분위기, 주차, 예약 등 추가 요구사항이 있는가?

**2.4 검색 최적화 판단**
- 입력 내용을 그대로 검색에 사용할 수 있는가?
- 불필요한 수식어("맛있는", "좋은", "근처" 등)가 많아 리라이트가 필요한가?
- 모호하거나 검색에 최적화되지 않은 표현이 있는가?

### 3단계: 행동 (Action)
평가 결과에 따라 적절한 응답을 생성합니다:
- 맛집 검색에 적합한 경우: 검색에 최적화된 쿼리로 변환
- 맛집 검색과 무관한 경우: 무관함을 명시
- 정보가 부족한 경우: 부족한 정보를 명시
- 부적절한 경우: 부적절함을 명시

## 응답 형식
반드시 JSON 형식으로 응답하세요:
{
  "is_valid": boolean,
  "is_inappropriate": boolean,
  "location": string | null,
  "search_item": string | null,
  "can_use_as_is": boolean,
  "needs_rewrite": boolean,
  "rewritten_query": string | null,
  "reasoning": string,
  "confidence": float (0.0 ~ 1.0)
}

## 예시

입력: "강남에 맛있는 파스타 먹고 싶어"
{
  "is_valid": true,
  "is_inappropriate": false,
  "location": "강남",
  "search_item": "파스타",
  "can_use_as_is": true,
  "needs_rewrite": false,
  "rewritten_query": null,
  "reasoning": "[Observation] 위치(강남)와 음식 종류(파스타)가 명확히 포함됨. [Reasoning] 맛집 검색 관련성 높음, 정보 완전함. [Action] 그대로 검색에 사용 가능.",
  "confidence": 0.95
}

입력: "오늘 날씨 어때?"
{
  "is_valid": false,
  "is_inappropriate": false,
  "location": null,
  "search_item": null,
  "can_use_as_is": false,
  "needs_rewrite": false,
  "rewritten_query": null,
  "reasoning": "[Observation] 날씨 관련 질문. [Reasoning] 맛집 검색과 무관한 내용. [Action] 맛집 검색과 관련 없음을 명시.",
  "confidence": 0.9
}

입력: "홍대 근처에 가성비 좋은 한식집 알려줘"
{
  "is_valid": true,
  "is_inappropriate": false,
  "location": "홍대",
  "search_item": "한식",
  "can_use_as_is": false,
  "needs_rewrite": true,
  "rewritten_query": "홍대 한식",
  "reasoning": "[Observation] 위치(홍대)와 음식 종류(한식) 추출 가능. [Reasoning] '근처', '가성비 좋은' 같은 수식어는 검색에 불필요. [Action] 핵심 키워드만 추출하여 리라이트.",
  "confidence": 0.85
}

주의:
- 반드시 JSON 형식으로만 응답하세요
- reasoning 필드에는 [Observation], [Reasoning], [Action] 단계를 명시하세요
- is_inappropriate=true면 is_valid=false여야 합니다"""


async def evaluate_user_input(user_input: str) -> dict:
    """
    사용자 입력 평가 (맛집 검색 쿼리)
    
    CoT와 ReAct 기법을 활용하여 사용자 입력을 평가합니다.
    
    Args:
        user_input: 사용자 입력
        
    Returns:
        평가 결과 (dict)
    """
    
    user_prompt = f'''다음 사용자 입력을 평가 프로세스에 따라 단계별로 분석하고 JSON 형식으로 응답하세요:

사용자 입력: "{user_input}"

위의 평가 프로세스(Observation → Reasoning → Action)를 따라 분석한 후, JSON 형식으로 결과를 반환하세요.'''
    
    llm_request: LLMRequest = {
        "user_prompt": user_prompt,
        "system_prompt": get_query_evaluation_system_prompt()
    }
    
    return await llm_call(llm_request)


class LLMRequest(TypedDict):
    """모델 호출 요청"""
    user_prompt: str  # 사용자 프롬프트
    system_prompt: Optional[str]  # 시스템 프롬프트 (선택)


async def llm_call(request: LLMRequest) -> dict:
    """
    LLM 모델 호출 함수
    
    Args:
        request: LLM 호출 요청 정보
        
    Returns:
        모델 응답 dict (JSON이면 파싱, 아니면 dict에 담아서 반환)
    """
    model = get_model()
    user_prompt = request.get("user_prompt", "")
    system_prompt = request.get("system_prompt")
    
    # 메시지 구성
    messages = []
    
    # 시스템 프롬프트 추가 (있는 경우)
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    else:
        # 기본 시스템 프롬프트
        messages.append(SystemMessage(
            content="You are my AI assistant, please answer my query to the best of your ability."
        ))
    
    # 사용자 프롬프트 추가
    messages.append(HumanMessage(content=user_prompt))
    
    try:
        logger.info(f"LLM 호출: user_prompt={user_prompt[:50]}...")
        
        # 모델 호출
        response = await model.ainvoke(messages)
        
        # 응답 추출
        result_text = response.content if hasattr(response, 'content') else str(response)
        
        logger.info(f"LLM 응답 완료: 길이={len(result_text)}")
        
        # JSON 파싱 시도
        try:
            # 코드 블록 제거
            cleaned_text = result_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            
            # JSON 파싱
            result_dict = json.loads(cleaned_text)
            logger.debug("JSON 파싱 성공")
            return result_dict
            
        except json.JSONDecodeError:
            # JSON이 아닌 경우 dict에 담아서 반환
            logger.debug("JSON 파싱 실패, dict로 감싸서 반환")
            return {"response": result_text}
        
    except Exception as e:
        logger.error(f"LLM 호출 실패: {str(e)}", exc_info=True)
        raise

