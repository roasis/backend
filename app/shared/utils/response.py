from typing import Any, Optional

from pydantic import BaseModel


class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None


class SuccessResponse(ApiResponse):
    success: bool = True


class ErrorResponse(ApiResponse):
    success: bool = False
