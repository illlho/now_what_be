from typing import TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import operator
from app.config import settings


class AgentState(TypedDict):
    """Agent 상태 정의"""
    messages: Annotated[list, add_messages]
    user_query: str
    response: str


class LangGraphAgent:
    """LangGraph를 사용한 AI Agent"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.7,
            api_key=settings.openai_api_key
        )
        self.graph = self._build_graph()
    
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
        
        # LLM 호출
        response = self.llm.invoke(user_query)
        
        state["response"] = response.content if hasattr(response, 'content') else str(response)
        return state
    
    async def process(self, user_query: str) -> str:
        """Agent 실행"""
        initial_state = {
            "messages": [],
            "user_query": user_query,
            "response": ""
        }
        
        result = await self.graph.ainvoke(initial_state)
        return result.get("response", "")


# 싱글톤 인스턴스
agent = LangGraphAgent()

