"""HTTP API request handlers."""

import json
from datetime import datetime
from typing import Any, Dict


class HTTPError(Exception):
    """Base exception for HTTP errors."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class ValidationError(HTTPError):
    """Raised when request validation fails."""

    def __init__(self, message: str):
        super().__init__(400, message)


class NotFoundError(HTTPError):
    """Raised when requested resource is not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(404, message)


class BaseHandler:
    """Base class for HTTP request handlers."""

    def __init__(self):
        self.logger = None

    def validate_request(self, data: Dict[str, Any], required_fields: list) -> None:
        """Validate incoming request data."""
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")

            if not data[field]:
                raise ValidationError(f"Empty value for field: {field}")

    def create_response(self, data: Any, status_code: int = 200) -> Dict[str, Any]:
        """Create standardized API response."""
        return {
            "status": "success" if status_code < 400 else "error",
            "status_code": status_code,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

    def handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle and format errors for API response."""
        if isinstance(error, HTTPError):
            return self.create_response({"message": error.message}, error.status_code)
        else:
            return self.create_response({"message": "Internal server error"}, 500)


class UserHandler(BaseHandler):
    """Handler for user-related API endpoints."""

    def __init__(self, user_service):
        super().__init__()
        self.user_service = user_service

    def create_user(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user account."""
        try:
            self.validate_request(request_data, ["username", "email", "password"])

            user = self.user_service.create_user(
                username=request_data["username"],
                email=request_data["email"],
                password=request_data["password"],
            )

            return self.create_response(
                {"user_id": user.id, "username": user.username, "email": user.email},
                201,
            )

        except Exception as e:
            return self.handle_error(e)

    def get_user(self, user_id: int) -> Dict[str, Any]:
        """Get user by ID."""
        try:
            user = self.user_service.get_user(user_id)
            if not user:
                raise NotFoundError(f"User {user_id} not found")

            return self.create_response(
                {
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "created_at": user.created_at.isoformat(),
                    "is_active": user.is_active,
                }
            )

        except Exception as e:
            return self.handle_error(e)

    def update_user(self, user_id: int, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user information."""
        try:
            user = self.user_service.get_user(user_id)
            if not user:
                raise NotFoundError(f"User {user_id} not found")

            updated_user = self.user_service.update_user(user_id, request_data)

            return self.create_response(
                {
                    "user_id": updated_user.id,
                    "username": updated_user.username,
                    "email": updated_user.email,
                }
            )

        except Exception as e:
            return self.handle_error(e)


def parse_json_body(request_body: str) -> Dict[str, Any]:
    """Parse JSON request body."""
    try:
        return json.loads(request_body)
    except json.JSONDecodeError:
        raise ValidationError("Invalid JSON in request body")


def extract_query_params(query_string: str) -> Dict[str, str]:
    """Extract query parameters from URL."""
    params = {}
    if not query_string:
        return params

    for param in query_string.split("&"):
        if "=" in param:
            key, value = param.split("=", 1)
            params[key] = value

    return params
