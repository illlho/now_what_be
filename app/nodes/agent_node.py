"""ReAct Agent 노드 구현"""

import logging
import time
from typing import Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import ToolNode

from app.schemas.agent_state import AgentState
from app.tools.basic_tools import reverse_geocode, terminate
from app.config import settings

logger = logging.getLogger(__name__)

# 도구 목록 (현재는 2개만)
TOOLS = [reverse_geocode, terminate]

# LLM with tools
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=settings.openai_api_key,
    temperature=0
)
llm_with_tools = llm.bind_tools(TOOLS)

# Tool 실행 노드 (LangGraph 내장)
tool_node = ToolNode(TOOLS)


def agent_node(state: AgentState) -> AgentState:
    """
    ReAct Agent 노드
    
    AI가 도구를 선택하고 실행을 결정합니다.
    
    Args:
        state: Agent 상태
        
    Returns:
        업데이트된 Agent 상태
    """
    logger.info("=" * 60)
    logger.info("🤖 Agent 노드 실행")
    logger.info("=" * 60)
    
    # 1. 안전장치: 도구 호출 횟수 제한
    if state.get("tool_call_count", 0) >= 20:
        logger.warning("⚠️  최대 도구 호출 횟수(20회) 도달")
        return {
            "messages": [AIMessage(content="최대 도구 호출 횟수에 도달했습니다. 현재까지의 결과를 반환합니다.")],
            "done": True
        }
    
    # 2. 안전장치: 타임아웃 체크 (10분)
    start_time = state.get("start_time", time.time())
    elapsed = time.time() - start_time
    if elapsed > 600:  # 10분
        logger.warning(f"⚠️  타임아웃 ({elapsed:.1f}초)")
        return {
            "messages": [AIMessage(content="타임아웃이 발생했습니다. 현재까지의 결과를 반환합니다.")],
            "done": True
        }
    
    # 3. 시스템 프롬프트 (Agent 가이드)
    system_prompt = """당신은 맛집 정보 수집 및 분석 전문 AI Agent입니다.

[목표]
사용자의 요청에 따라 맛집 정보를 자율적으로 수집, 분석, 정리합니다.

[사용 가능한 도구]
1. reverse_geocode: 좌표를 주소로 변환
2. terminate: 작업 완료

[기본 전략]
1. 사용자 요청 분석
   - 위치 키워드 추출 (없으면 reverse_geocode 사용)
   - 음식 키워드 추출 ("맛집"이면 카테고리로 분해)
   
2. 작업 완료 판단
   - 충분한 정보 수집 완료 시 terminate 호출

[제약 조건]
- 최대 도구 호출: 20회
- 타임아웃: 10분

[현재 상태]
- 도구 호출 횟수: {tool_count}/20
- 경과 시간: {elapsed:.1f}초
""".format(
        tool_count=state.get("tool_call_count", 0),
        elapsed=elapsed
    )
    
    # 4. 메시지 구성
    messages = state.get("messages", [])
    
    # 첫 실행인 경우 시스템 프롬프트 + 사용자 요청 추가
    if len(messages) == 0:
        user_query = state.get("user_query", "")
        user_location = state.get("user_location")
        
        user_message = f"사용자 요청: {user_query}"
        if user_location:
            user_message += f"\n사용자 위치 좌표: 위도={user_location['latitude']}, 경도={user_location['longitude']}"
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
    else:
        # 기존 메시지에 시스템 프롬프트 업데이트 (상태 정보 갱신)
        if messages[0].type == "system":
            messages[0] = SystemMessage(content=system_prompt)
        else:
            messages.insert(0, SystemMessage(content=system_prompt))
    
    logger.info(f"메시지 개수: {len(messages)}")
    
    # 5. LLM 호출
    try:
        response = llm_with_tools.invoke(messages)
        logger.info(f"AI 응답: {response.content[:100] if response.content else '(도구 호출)'}")
        
        # 도구 호출이 있는지 확인
        if hasattr(response, 'tool_calls') and response.tool_calls:
            logger.info(f"🔧 도구 호출: {len(response.tool_calls)}개")
            for tool_call in response.tool_calls:
                logger.info(f"  - {tool_call['name']}: {tool_call.get('args', {})}")
        
        # terminate가 호출되었는지 확인
        done = False
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call['name'] == 'terminate':
                    done = True
                    logger.info("🏁 terminate 호출 감지 - 작업 완료")
                    break
        
        return {
            "messages": [response],
            "done": done
        }
        
    except Exception as e:
        logger.error(f"❌ Agent 실행 중 오류: {str(e)}", exc_info=True)
        return {
            "messages": [AIMessage(content=f"오류가 발생했습니다: {str(e)}")],
            "done": True
        }


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """
    Agent가 계속 실행될지 종료될지 결정
    
    Args:
        state: Agent 상태
        
    Returns:
        "tools": 도구 실행 노드로 이동
        "end": 종료
    """
    # done 플래그 확인
    if state.get("done", False):
        logger.info("✅ done=True → 종료")
        return "end"
    
    # 마지막 메시지 확인
    messages = state.get("messages", [])
    if not messages:
        logger.info("메시지 없음 → 종료")
        return "end"
    
    last_message = messages[-1]
    
    # 도구 호출이 있으면 계속
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        logger.info(f"🔧 도구 호출 있음 → tools 노드로")
        return "tools"
    
    # 도구 호출 없으면 종료
    logger.info("도구 호출 없음 → 종료")
    return "end"
