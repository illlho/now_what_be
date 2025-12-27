"""에러 코드 상수 정의

모든 에러 코드를 중앙에서 관리하여 일관성과 유지보수성을 향상시킵니다.
"""


class ErrorCode:
    """에러 코드 상수 클래스"""
    
    # ========== 일반 에러 ==========
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    """서버 내부 오류"""
    
    # ========== 설정 관련 에러 ==========
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    """설정 관련 에러"""
    
    # ========== API 키 관련 에러 ==========
    API_KEY_ERROR = "API_KEY_ERROR"
    """API 키 관련 에러 (일반)"""
    API_KEY_MISSING = "API_KEY_MISSING"
    """API 키가 설정되지 않음"""
    API_KEY_INVALID = "API_KEY_INVALID"
    """API 키가 유효하지 않음"""
    
    # ========== Agent 관련 에러 ==========
    AGENT_ERROR = "AGENT_ERROR"
    """Agent 처리 관련 에러 (일반)"""
    AGENT_INIT_FAILED = "AGENT_INIT_FAILED"
    """Agent 초기화 실패"""
    AGENT_PROCESSING_FAILED = "AGENT_PROCESSING_FAILED"
    """Agent 처리 실패"""
    AGENT_LLM_ERROR = "AGENT_LLM_ERROR"
    """LLM 호출 에러"""
    
    # ========== 검증 관련 에러 ==========
    VALIDATION_ERROR = "VALIDATION_ERROR"
    """입력 검증 에러"""
    VALIDATION_FIELD_ERROR = "VALIDATION_FIELD_ERROR"
    """특정 필드 검증 에러"""
    
    # ========== HTTP 관련 에러 ==========
    @staticmethod
    def http_error(status_code: int) -> str:
        """HTTP 상태 코드 기반 에러 코드 생성"""
        return f"HTTP_{status_code}"
    
    # ========== 일반적인 HTTP 에러 코드 ==========
    HTTP_400_BAD_REQUEST = "HTTP_400"
    """잘못된 요청"""
    HTTP_401_UNAUTHORIZED = "HTTP_401"
    """인증 필요"""
    HTTP_403_FORBIDDEN = "HTTP_403"
    """접근 금지"""
    HTTP_404_NOT_FOUND = "HTTP_404"
    """리소스를 찾을 수 없음"""
    HTTP_422_UNPROCESSABLE_ENTITY = "HTTP_422"
    """처리할 수 없는 엔티티"""
    HTTP_429_TOO_MANY_REQUESTS = "HTTP_429"
    """너무 많은 요청"""
    HTTP_500_INTERNAL_SERVER_ERROR = "HTTP_500"
    """서버 내부 오류"""
    HTTP_503_SERVICE_UNAVAILABLE = "HTTP_503"
    """서비스 사용 불가"""


# 편의를 위한 별칭
ERROR_CODES = ErrorCode

