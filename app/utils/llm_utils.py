"""LLM 관련 유틸리티 함수들

모델 호출 및 LLM 관련 헬퍼 함수들을 정의합니다.
with_structured_output을 사용하여 타입 안전한 응답을 보장합니다.
"""

from typing import Optional, TypedDict, TypeVar, Type
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

# 제네릭 타입 변수
T = TypeVar('T', bound=BaseModel)

# 전역 모델 인스턴스 (싱글톤 패턴)
_model: Optional[ChatOpenAI] = None


def get_model() -> ChatOpenAI:
    """
    LLM 모델 인스턴스 반환 (싱글톤 패턴)
    
    Returns:
        ChatOpenAI: 초기화된 LLM 모델 인스턴스
    """
    global _model
    if _model is None:
        _model = ChatOpenAI(model="gpt-4o-mini")
    return _model


class LLMRequest(TypedDict):
    """
    LLM 모델 호출 요청 타입
    
    Attributes:
        user_prompt: 사용자 프롬프트 (필수)
        system_prompt: 시스템 프롬프트 (선택)
    """
    user_prompt: str  # 사용자 프롬프트
    system_prompt: Optional[str]  # 시스템 프롬프트 (선택)


async def llm_call(request: LLMRequest, output_model: Type[T]) -> T:
    """
    LLM 모델 호출 함수 (with_structured_output 사용)
    
    Args:
        request: LLM 호출 요청 정보
        output_model: 응답을 받을 Pydantic 모델 클래스
        
    Returns:
        output_model 타입의 Pydantic 모델 인스턴스
        
    Example:
        ```python
        result = await llm_call(request, QueryEvaluationResult)
        # result는 QueryEvaluationResult 인스턴스
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
        
        # with_structured_output을 사용하여 구조화된 출력 보장
        structured_model = model.with_structured_output(output_model)
        
        # 모델 호출 (자동으로 Pydantic 모델로 변환됨)
        result = await structured_model.ainvoke(messages)
        
        logger.info(f"LLM 응답 완료: {output_model.__name__} 타입으로 반환")
        return result
        
    except Exception as e:
        logger.error(f"LLM 호출 실패: {str(e)}", exc_info=True)
        raise

