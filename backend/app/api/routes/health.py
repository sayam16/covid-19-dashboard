from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request) -> dict[str, str]:
    startup_error = getattr(request.app.state, "startup_error", None)
    if startup_error:
        return {"status": "degraded", "reason": startup_error}
    return {"status": "ok"}
