"""
Custom Exceptions for AI Automation System
Provides specific, descriptive error types for better error handling
"""


class AIAutomationError(Exception):
    """Base exception for all AI automation errors"""
    
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary for API responses"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details
        }


# ============================================
# GPM-Related Exceptions
# ============================================

class GPMError(AIAutomationError):
    """Base exception for GPM-related errors"""
    pass


class GPMNotRunningError(GPMError):
    """GPM application is not running or API is unreachable"""
    
    def __init__(self, api_url: str = None):
        super().__init__(
            message="GPM Browser is not running or API is unreachable",
            details={"api_url": api_url, "suggestion": "Please start GPM Browser application"}
        )


class GPMProfileNotFoundError(GPMError):
    """Specified GPM profile doesn't exist"""
    
    def __init__(self, profile_id: str):
        super().__init__(
            message=f"GPM profile not found: {profile_id}",
            details={"profile_id": profile_id, "suggestion": "Create the profile in GPM first"}
        )


class GPMProfileCreationError(GPMError):
    """Failed to create GPM profile"""
    
    def __init__(self, profile_name: str, reason: str = None):
        super().__init__(
            message=f"Failed to create GPM profile: {profile_name}",
            details={"profile_name": profile_name, "reason": reason}
        )


class GPMBrowserError(GPMError):
    """Error launching or controlling GPM browser"""
    
    def __init__(self, action: str, reason: str = None):
        super().__init__(
            message=f"GPM browser error during: {action}",
            details={"action": action, "reason": reason}
        )


class GPMConnectionError(GPMError):
    """Failed to connect Playwright to GPM browser"""
    
    def __init__(self, debug_port: int = None, reason: str = None):
        super().__init__(
            message="Failed to connect to GPM browser via CDP",
            details={
                "debug_port": debug_port,
                "reason": reason,
                "suggestion": "Ensure browser is running and debug port is accessible"
            }
        )


# ============================================
# AI Session Exceptions
# ============================================

class AISessionError(AIAutomationError):
    """Base exception for AI session-related errors"""
    pass


class SessionExpiredError(AISessionError):
    """AI provider session has expired, needs re-login"""
    
    def __init__(self, provider: str):
        super().__init__(
            message=f"Session expired for {provider}",
            details={"provider": provider, "suggestion": "Please re-login to the account"}
        )


class LoginTimeoutError(AISessionError):
    """User didn't complete login within timeout period"""
    
    def __init__(self, provider: str, timeout_seconds: int):
        super().__init__(
            message=f"Login timeout for {provider} (waited {timeout_seconds}s)",
            details={
                "provider": provider,
                "timeout_seconds": timeout_seconds,
                "suggestion": "Try again and complete login faster"
            }
        )


class LoginDetectionError(AISessionError):
    """Could not detect login status"""
    
    def __init__(self, provider: str, reason: str = None):
        super().__init__(
            message=f"Could not detect login status for {provider}",
            details={"provider": provider, "reason": reason}
        )


# ============================================
# AI Provider Exceptions
# ============================================

class AIProviderError(AIAutomationError):
    """Base exception for AI provider-related errors"""
    pass


class ProviderNotConfiguredError(AIProviderError):
    """AI provider is not configured (missing API key or profile)"""
    
    def __init__(self, provider: str):
        super().__init__(
            message=f"AI provider not configured: {provider}",
            details={"provider": provider, "suggestion": "Configure in AI Settings"}
        )


class PromptError(AIProviderError):
    """Error sending prompt or receiving response"""
    
    def __init__(self, provider: str, reason: str = None):
        super().__init__(
            message=f"Failed to get response from {provider}",
            details={"provider": provider, "reason": reason}
        )


class RateLimitError(AIProviderError):
    """AI provider rate limit exceeded"""
    
    def __init__(self, provider: str, retry_after: int = None):
        super().__init__(
            message=f"Rate limit exceeded for {provider}",
            details={
                "provider": provider,
                "retry_after_seconds": retry_after,
                "suggestion": "Wait before retrying"
            }
        )


class AllProvidersFailedError(AIProviderError):
    """All AI providers failed after retries"""
    
    def __init__(self, attempted_providers: list, errors: list = None):
        super().__init__(
            message="All AI providers failed",
            details={
                "attempted_providers": attempted_providers,
                "errors": errors,
                "suggestion": "Check account status and network connection"
            }
        )


# ============================================
# Database Exceptions
# ============================================

class DatabaseError(AIAutomationError):
    """Database operation failed"""
    pass


class AccountNotFoundError(DatabaseError):
    """Account not found in database"""
    
    def __init__(self, account_id: int = None, profile_id: str = None):
        identifier = f"id={account_id}" if account_id else f"profile_id={profile_id}"
        super().__init__(
            message=f"Account not found: {identifier}",
            details={"account_id": account_id, "profile_id": profile_id}
        )
