"""Error handling and exception management."""

import logging
import traceback


class CustomException(Exception):
    """Base custom exception class."""

    pass


class ValidationError(CustomException):
    """Raised when data validation fails."""

    pass


class AuthenticationError(CustomException):
    """Raised when authentication fails."""

    pass


class ErrorHandler:
    """Error handler for managing exceptions and logging."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def handle_exception(self, exception, context=None):
        """Handle exception with logging and context."""
        try:
            error_msg = f"Exception occurred: {str(exception)}"
            if context:
                error_msg += f" | Context: {context}"

            self.logger.error(error_msg)
            self.logger.debug(traceback.format_exc())

            return {
                "error": str(exception),
                "type": type(exception).__name__,
                "context": context,
            }
        except Exception as e:
            # Fallback error handling
            print(f"Error in error handler: {e}")
            return {"error": "Unknown error occurred"}

    def safe_execute(self, func, *args, **kwargs):
        """Execute function with exception handling."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return self.handle_exception(e, context=f"Function: {func.__name__}")


def try_catch_decorator(func):
    """Decorator for automatic exception handling."""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            handler = ErrorHandler()
            return handler.handle_exception(
                e, context=f"Decorated function: {func.__name__}"
            )

    return wrapper
