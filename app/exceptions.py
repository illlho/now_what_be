"""커스텀 예외 클래스"""


class BaseAPIException(Exception):
    """기본 API 예외 클래스"""
    def __init__(self, message: str, status_code: int = 500, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        super().__init__(self.message)


class ConfigurationError(BaseAPIException):
    """설정 관련 에러"""
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=500,
            error_code="CONFIGURATION_ERROR"
        )


class APIKeyError(BaseAPIException):
    """API 키 관련 에러"""
    def __init__(self, message: str = "API 키가 설정되지 않았습니다."):
        super().__init__(
            message=message,
            status_code=503,
            error_code="API_KEY_ERROR"
        )


class AgentError(BaseAPIException):
    """Agent 처리 관련 에러"""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code="AGENT_ERROR"
        )


class ValidationError(BaseAPIException):
    """입력 검증 에러"""
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR"
        )

