"""LLM 관련 유틸리티 함수들

모델 호출 및 LLM 관련 헬퍼 함수들을 정의합니다.
"""

from typing import Optional, TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
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


async def evaluate_user_input(user_input: str) -> str:
    """
    사용자 입력 평가
    
    사용자 입력을 평가합니다.
    
    Args:
        user_input: 사용자 입력
    """
    LLMRequest(user_prompt=user_input, system_prompt="")
    llm_call(user_input)


class LLMRequest(TypedDict):
    """모델 호출 요청"""
    user_prompt: str  # 사용자 프롬프트
    system_prompt: Optional[str]  # 시스템 프롬프트 (선택)


async def llm_call(request: LLMRequest) -> str:
    """
    LLM 모델 호출 함수
    
    Args:
        request: LLM 호출 요청 정보
        
    Returns:
        모델 응답 문자열
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
        result = response.content if hasattr(response, 'content') else str(response)
        
        logger.info(f"LLM 응답 완료: 길이={len(result)}")
        
        return result
        
    except Exception as e:
        logger.error(f"LLM 호출 실패: {str(e)}", exc_info=True)
        raise

