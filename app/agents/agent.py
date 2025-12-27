from typing import TypedDict, Annotated, Optional
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import operator
import logging
from app.config import settings
from app.exceptions import APIKeyError, AgentError
from app.constants.error_codes import ErrorCode

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Agent 상태 정의"""
    messages: Annotated[list, add_messages]
    user_query: str
    response: str


class LangGraphAgent:
    """LangGraph를 사용한 AI Agent"""
    
    def __init__(self):
        """Agent 초기화 (Lazy initialization)"""
        self._llm: Optional[ChatOpenAI] = None
        self._graph: Optional[StateGraph] = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Agent 초기화 확인 및 초기화"""
        if self._initialized:
            return
        
        try:
            # OpenAI API 키 검증
            if not settings.openai_api_key:
                raise APIKeyError(
                    "OPENAI_API_KEY가 설정되지 않았습니다. "
                    ".env 파일을 생성하고 OPENAI_API_KEY를 설정하세요. "
                    ".env.example 파일을 참고하세요.",
                    error_code=ErrorCode.API_KEY_MISSING
                )
            
            logger.info("LangGraph Agent 초기화 중...")
            
            self._llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.7,
                api_key=settings.openai_api_key
            )
            self._graph = self._build_graph()
            self._initialized = True
            
            logger.info("LangGraph Agent 초기화 완료")
            
        except APIKeyError:
            raise
        except Exception as e:
            logger.error(f"Agent 초기화 실패: {str(e)}", exc_info=True)
            raise AgentError(
                f"Agent 초기화 중 오류가 발생했습니다: {str(e)}",
                error_code=ErrorCode.AGENT_INIT_FAILED
            )
    
    def _build_graph(self) -> StateGraph:
        """LangGraph 그래프 구성"""
        workflow = StateGraph(AgentState)
        
        # 노드 추가
        workflow.add_node("process_query", self._process_query)
        workflow.add_node("generate_response", self._generate_response)
        
        # 엣지 추가
        workflow.set_entry_point("process_query")
        workflow.add_edge("process_query", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    def _process_query(self, state: AgentState) -> AgentState:
        """사용자 쿼리 처리"""
        # 쿼리 전처리 또는 검증 로직 추가 가능
        return state
    
    def _generate_response(self, state: AgentState) -> AgentState:
        """LLM을 사용한 응답 생성"""
        user_query = state.get("user_query", "")
        
        try:
            # LLM 호출
            response = self._llm.invoke(user_query)
            state["response"] = response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"LLM 호출 실패: {str(e)}", exc_info=True)
            raise AgentError(
                f"AI 응답 생성 중 오류가 발생했습니다: {str(e)}",
                error_code=ErrorCode.AGENT_LLM_ERROR
            )
        
        return state
    
    async def process(self, user_query: str) -> str:
        """Agent 실행"""
        # 초기화 확인
        self._ensure_initialized()
        
        try:
            initial_state = {
                "messages": [],
                "user_query": user_query,
                "response": ""
            }
            
            result = await self._graph.ainvoke(initial_state)
            return result.get("response", "")
            
        except APIKeyError:
            raise
        except AgentError:
            raise
        except Exception as e:
            logger.error(f"Agent 처리 실패: {str(e)}", exc_info=True)
            raise AgentError(
                f"Agent 처리 중 오류가 발생했습니다: {str(e)}",
                error_code=ErrorCode.AGENT_PROCESSING_FAILED
            )


# 싱글톤 인스턴스 (Lazy initialization)
agent = LangGraphAgent()

