from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import load_settings
from app.db.session import Base, engine, get_db
from app.models.oplog import OpLog
from app.api.routes_auth import router as auth_router
from app.api.routes_footprints import router as footprints_router
from app.api.routes_admin import router as admin_router
from app.core.security import decode_token, hash_password
from app.models.user import User
from contextlib import asynccontextmanager
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request as StarletteRequest
from fastapi import HTTPException, status
from app.utils.response import ok, fail

settings = load_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with Session(bind=engine) as s:
        admin = s.query(User).filter(User.username == 'admin').first()
        if not admin:
            admin = User(username='admin', password_hash=hash_password('admin123'), is_admin=True)
            s.add(admin)
            s.commit()
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE footprints ADD COLUMN is_public TINYINT(1) NOT NULL DEFAULT 0"))
    except Exception:
        pass
    yield


app = FastAPI(title="JTrace API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.server.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: StarletteRequest, exc: RequestValidationError):
    return JSONResponse(status_code=200, content=fail("参数错误", exc.errors()))


@app.exception_handler(Exception)
async def global_exception_handler(request: StarletteRequest, exc: Exception):
    if isinstance(exc, HTTPException):
        if exc.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN):
            # 认证/权限错误按原码返回
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        # 其他 HTTPException 统一返回 200
        return JSONResponse(status_code=200, content=fail(str(exc.detail)))
    return JSONResponse(status_code=200, content=fail("服务器错误"))


@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        try:
            if request.url.path.startswith("/api/"):
                user_id = None
                token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
                username = None
                if token:
                    try:
                        payload = decode_token(token)
                        username = payload.get("sub")
                    except Exception:
                        username = None
                with engine.begin() as conn:
                    if username:
                        try:
                            uid = conn.execute(text("SELECT id FROM users WHERE username=:u"), {"u": username}).scalar()
                            if uid:
                                user_id = int(uid)
                        except Exception:
                            user_id = None
                    conn.execute(
                        OpLog.__table__.insert().values(
                            user_id=user_id,
                            action="REQUEST",
                            path=request.url.path,
                            method=request.method,
                            detail=None,
                        )
                    )
        except Exception:
            pass


@app.get("/api/health")
async def health():
    return ok({"status": "ok"})


app.include_router(auth_router, prefix="/api")
app.include_router(footprints_router, prefix="/api")
app.include_router(admin_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    cfg = settings.server
    host = cfg.host or "0.0.0.0"
    port = int(cfg.port or 8000)
    debug = bool(cfg.debug)
    log_level = (cfg.log_level or "info").lower()
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level=log_level,
    )
