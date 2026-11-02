from datetime import datetime

from fastapi import Request
from fastapi.responses import JSONResponse


def build_response(request: Request, status_code: int, message: str, data=None, error=None):
    return JSONResponse(
        status_code=status_code,
        content={
            "statusCode": status_code,
            "message": message,
            "error": error,
            "data": data,
            "path": request.url.path,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )


def success_response(request: Request, message: str = "Success", data=None, status_code: int = 200):
    return build_response(request, status_code, message, data=data, error=None)


def error_response(request: Request, message: str, error=None, status_code: int = 400):
    return build_response(request, status_code, message, data=None, error=error)
