from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import load_settings
from app.db.session import Base, engine, get_db
from app.models.oplog import OpLog
from app.api.routes_auth import router as auth_router
from app.api.routes_footprints import router as footprints_router
from app.api.routes_footprint_types import router as footprint_types_router
from app.api.routes_comments import router as comments_router
from app.api.routes_admin import router as admin_router
from app.api.routes_upload import router as upload_router
from app.core.security import decode_token, hash_password
from app.models.user import User
from app.utils.file_signature import file_signature_manager
from fastapi.responses import FileResponse
from urllib.parse import unquote
import os
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
        # 创建管理员用户
        admin = s.query(User).filter(User.username == 'admin').first()
        if not admin:
            admin = User(
                username='admin', 
                email='admin@jtrace.com',
                password_hash=hash_password('admin123')
            )
            s.add(admin)
            s.commit()
        
        # 创建默认的足迹类型
        from app.models import FootprintType
        default_types = [
            {'name': '美食', 'icon': '/icons/food.svg', 'sort_order': 1},
            {'name': '景点', 'icon': '/icons/attraction.svg', 'sort_order': 2},
            {'name': '自然', 'icon': '/icons/nature.svg', 'sort_order': 3},
            {'name': '博物馆', 'icon': '/icons/museum.svg', 'sort_order': 4},
            {'name': '购物', 'icon': '/icons/shopping.svg', 'sort_order': 5},
            {'name': '其他', 'icon': '/icons/default.svg', 'sort_order': 6}
        ]
        
        for type_data in default_types:
            exist_type = s.query(FootprintType).filter(FootprintType.name == type_data['name']).first()
            if not exist_type:
                footprint_type = FootprintType(**type_data)
                s.add(footprint_type)
        
        s.commit()
    
    # 处理数据库结构变更（向后兼容）
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

# 静态文件服务 - 上传文件访问
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


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
app.include_router(footprint_types_router, prefix="/api")
app.include_router(comments_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(upload_router, prefix="/api")

# 文件访问路由（不使用/api前缀，直接处理/file路径）
@app.get("/file/{file_path:path}")
async def get_file(
    file_path: str,
    signature: str,
    expires: int,
):
    """获取签名保护的文件"""
    try:
        # 解码文件路径
        decoded_path = unquote(file_path)
        
        # 验证签名
        verification_result = file_signature_manager.verify_signed_url(
            decoded_path, signature, expires
        )
        
        if not verification_result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=verification_result["error"]
            )
        
        # 检查文件是否存在
        if not os.path.exists(decoded_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )
        
        # 返回文件
        return FileResponse(
            path=decoded_path,
            headers={
                "Cache-Control": "public, max-age=3600",  # 缓存1小时
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件访问失败: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    cfg = settings.server
    host = cfg.host or "0.0.0.0"
    port = int(cfg.port or 8000)
    debug = bool(cfg.debug)
    log_level = (cfg.log_level or "info").lower()
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level=log_level,
    )
