from typing import Any, Optional


def ok(data: Any = None, message: str = "") -> dict:
    return {"success": True, "message": message, "data": data}


def fail(message: str = "", data: Any = None) -> dict:
    return {"success": False, "message": message, "data": data}
