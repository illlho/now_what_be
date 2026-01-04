"""LLM 관련 유틸리티 함수들

모델 호출 및 LLM 관련 헬퍼 함수들을 정의합니다.
with_structured_output을 사용하여 타입 안전한 응답을 보장합니다.
"""

from typing import Optional, TypedDict, TypeVar, Type, NamedTuple
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel
import logging
import tiktoken
import json
from app.config import settings
from app.exceptions import APIKeyError

logger = logging.getLogger(__name__)

# GPT-4o-mini 가격 (USD per 1M tokens)
# Source: https://openai.com/api/pricing/
GPT4O_MINI_INPUT_PRICE_PER_1M = 0.150  # $0.150 per 1M input tokens
GPT4O_MINI_OUTPUT_PRICE_PER_1M = 0.600  # $0.600 per 1M output tokens

# USD to KRW 환율 (환경변수로 설정 가능, 기본값 1300)
USD_TO_KRW = 1443

# 제네릭 타입 변수
T = TypeVar('T', bound=BaseModel)

# 전역 모델 인스턴스 (싱글톤 패턴)
_model: Optional[ChatOpenAI] = None


class TokenUsageInfo(NamedTuple):
    """토큰 사용량 및 비용 정보"""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_krw: float
    cost_formatted: str  # 예: "0.02원(2340 tokens)"


def get_model() -> ChatOpenAI:
    """
    LLM 모델 인스턴스 반환 (싱글톤 패턴)
    
    Returns:
        ChatOpenAI: 초기화된 LLM 모델 인스턴스
        
    Raises:
        APIKeyError: OpenAI API 키가 설정되지 않은 경우
    """
    global _model
    if _model is None:
        # API 키 검증
        api_key = settings.validate_openai_key()
        _model = ChatOpenAI(model="gpt-4o-mini", api_key=api_key)
    return _model


def _get_token_count(text: str) -> int:
    """
    텍스트의 토큰 수 계산 (gpt-4o-mini용)
    
    Args:
        text: 토큰 수를 계산할 텍스트
        
    Returns:
        토큰 수
    """
    try:
        # gpt-4o-mini는 o200k_base 인코딩 사용
        encoding = tiktoken.get_encoding("o200k_base")
        return len(encoding.encode(text))
    except Exception as e:
        logger.warning(f"토큰 수 계산 실패: {str(e)}, 근사치 사용")
        # 근사치: 1 토큰 ≈ 4 문자 (한글은 더 적을 수 있음)
        return len(text) // 4


def calculate_cost(input_tokens: int, output_tokens: int) -> tuple[float, str]:
    """
    토큰 사용량에 따른 비용 계산 (gpt-4o-mini 기준)
    
    Args:
        input_tokens: 입력 토큰 수
        output_tokens: 출력 토큰 수
        
    Returns:
        (비용(원), 포맷된 문자열) 튜플
    """
    # USD 비용 계산
    input_cost_usd = (input_tokens / 1_000_000) * GPT4O_MINI_INPUT_PRICE_PER_1M
    output_cost_usd = (output_tokens / 1_000_000) * GPT4O_MINI_OUTPUT_PRICE_PER_1M
    total_cost_usd = input_cost_usd + output_cost_usd
    
    # 한화로 변환
    total_cost_krw = total_cost_usd * USD_TO_KRW
    
    # 포맷팅: 소수점 둘째 자리까지
    total_tokens = input_tokens + output_tokens
    formatted_cost = f"{total_cost_krw:.2f}원({total_tokens} tokens)"
    
    return total_cost_krw, formatted_cost


class LLMRequest(TypedDict):
    """
    LLM 모델 호출 요청 타입
    
    Attributes:
        user_prompt: 사용자 프롬프트 (필수)
        system_prompt: 시스템 프롬프트 (선택)
    """
    user_prompt: str  # 사용자 프롬프트
    system_prompt: Optional[str]  # 시스템 프롬프트 (선택)


async def llm_call(request: LLMRequest, output_model: Type[T]) -> tuple[T, TokenUsageInfo]:
    """
    LLM 모델 호출 함수 (with_structured_output 사용)
    
    Args:
        request: LLM 호출 요청 정보
        output_model: 응답을 받을 Pydantic 모델 클래스
        
    Returns:
        (Pydantic 모델 인스턴스, 토큰 사용량 및 비용 정보) 튜플
        
    Example:
        ```python
        result, token_info = await llm_call(request, QueryEvaluationResult)
        # result는 QueryEvaluationResult 인스턴스
        # token_info.cost_formatted는 "0.02원(2340 tokens)" 형식
        ```
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
        logger.info(f"LLM 호출: user_prompt={user_prompt[:50]}..., output_model={output_model.__name__}")
        
        # 요청 토큰 수 계산
        request_text = ""
        for msg in messages:
            if hasattr(msg, 'content'):
                request_text += msg.content + "\n"
        input_tokens = _get_token_count(request_text)
        
        # with_structured_output을 사용하여 구조화된 출력 보장
        structured_model = model.with_structured_output(output_model)
        
        # 모델 호출 (자동으로 Pydantic 모델로 변환됨)
        result = await structured_model.ainvoke(messages)
        
        # 응답 토큰 수 계산 (Pydantic 모델을 JSON으로 변환하여 계산)
        result_json = json.dumps(result.model_dump(), ensure_ascii=False)
        output_tokens = _get_token_count(result_json)
        
        # 비용 계산
        cost_krw, cost_formatted = calculate_cost(input_tokens, output_tokens)
        
        # 토큰 사용량 정보 생성
        token_info = TokenUsageInfo(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_krw=cost_krw,
            cost_formatted=cost_formatted
        )
        
        # 로그 출력
        logger.info(
            f"LLM 응답 완료: {output_model.__name__} 타입으로 반환 | "
            f"비용: {cost_formatted} | "
            f"입력: {input_tokens} tokens, 출력: {output_tokens} tokens"
        )
        
        return result, token_info
        
    except Exception as e:
        logger.error(f"LLM 호출 실패: {str(e)}", exc_info=True)
        raise

