"""그래프 시각화 유틸리티

워크플로우 그래프를 Mermaid 다이어그램으로 시각화하기 위한 유틸리티 함수들을 정의합니다.
"""

import logging
from typing import Callable
from langgraph.graph import StateGraph

logger = logging.getLogger(__name__)


def generate_mermaid_diagram(build_graph_func: Callable[[], StateGraph]) -> str:
    """
    LangGraph 그래프에서 Mermaid 다이어그램 코드를 생성합니다.
    
    Args:
        build_graph_func: 그래프를 생성하는 함수
        
    Returns:
        Mermaid 다이어그램 코드 문자열
    """
    try:
        # 그래프 생성
        graph = build_graph_func()
        
        # 그래프 컴파일
        compiled_graph = graph.compile()
        
        # Mermaid 다이어그램 생성
        mermaid_code = compiled_graph.get_graph().draw_mermaid()
        
        return mermaid_code
    except Exception as e:
        logger.error(f"Mermaid 다이어그램 생성 실패: {str(e)}", exc_info=True)
        raise


def generate_html_content(mermaid_code: str) -> str:
    """
    Mermaid 다이어그램을 포함한 HTML 콘텐츠를 생성합니다.
    
    Args:
        mermaid_code: Mermaid 다이어그램 코드 문자열
        
    Returns:
        완성된 HTML 콘텐츠 문자열
    """
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>워크플로우 그래프 시각화</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .mermaid {{
            text-align: center;
            margin: 20px 0;
        }}
        .info {{
            background-color: #e3f2fd;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .code-block {{
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            font-family: monospace;
            font-size: 12px;
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="mermaid">
            {mermaid_code}
        </div>
    </div>
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
</body>
</html>
"""
    return html_content


def generate_error_html(error_message: str) -> str:
    """
    에러 발생 시 표시할 HTML 콘텐츠를 생성합니다.
    
    Args:
        error_message: 에러 메시지
        
    Returns:
        에러 HTML 콘텐츠 문자열
    """
    error_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>오류 발생</title>
</head>
<body>
    <h1>그래프 시각화 중 오류 발생</h1>
    <p>{error_message}</p>
</body>
</html>
"""
    return error_html

