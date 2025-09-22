from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import uuid
import shutil
from datetime import datetime
from typing import List, Optional
from urllib.parse import unquote

from ..db.session import get_db
from ..api.deps import get_current_user
from ..models.user import User
from ..utils.response import ok, fail
from ..utils.file_signature import file_signature_manager
from ..core.config import load_settings

router = APIRouter(prefix="/upload", tags=["upload"])
settings = load_settings()


def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    return os.path.splitext(filename)[1].lower()


def generate_unique_filename(filename: str) -> str:
    """生成唯一文件名"""
    ext = get_file_extension(filename)
    unique_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{unique_id}{ext}"


def validate_file_type(file: UploadFile) -> str:
    """验证文件类型，返回类型标识"""
    allowed, file_type = file_signature_manager.is_allowed_file_type(file.content_type)
    if not allowed:
        allowed_types = settings.upload.allowed_image_types + settings.upload.allowed_video_types
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {file.content_type}. 支持的格式: {', '.join(allowed_types)}"
        )
    return file_type


def validate_file_size(file_size: int):
    """验证文件大小"""
    if not file_signature_manager.is_file_size_allowed(file_size):
        max_size_mb = settings.upload.max_file_size // (1024*1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件过大，最大允许 {max_size_mb}MB"
        )


def generate_avatar_path(user_id: int, filename: str) -> str:
    """为头像生成公开访问路径"""
    ext = get_file_extension(filename)
    unique_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    avatar_filename = f"avatar_{timestamp}_{unique_id}{ext}"
    
    # 头像存储在uploads/avatars目录下（公开访问）
    avatar_dir = os.path.join("uploads", "avatars")
    os.makedirs(avatar_dir, exist_ok=True)
    
    return os.path.join(avatar_dir, avatar_filename).replace('\\', '/')


@router.post("/media")
def upload_media(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    user: User = Depends(get_current_user)
):
    """上传图片或视频文件"""
    try:
        # 验证文件类型
        media_type = validate_file_type(file)
        
        # 读取文件内容以获取大小
        file_content = file.file.read()
        file.file.seek(0)  # 重置文件指针
        
        # 验证文件大小
        validate_file_size(len(file_content))
        
        # 生成目录路径
        directory_path = file_signature_manager.generate_directory_path(user.id, media_type)
        os.makedirs(directory_path, exist_ok=True)
        
        # 生成唯一文件名
        unique_filename = generate_unique_filename(file.filename)
        
        # 完整文件路径
        file_path = os.path.join(directory_path, unique_filename)
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # 生成相对路径用于URL
        relative_path = os.path.relpath(file_path, '.').replace('\\', '/')
        
        # 生成签名URL
        signed_url = file_signature_manager.generate_signed_url(relative_path)
        
        return ok({
            "media_url": relative_path,  # 返回文件路径，不包含签名
            "media_type": media_type,
            "description": description,
            "original_filename": file.filename,
            "size": len(file_content),
            "file_path": relative_path,  # 保持兼容性
            "signed_url": signed_url     # 如果前端需要立即预览，可以使用这个
        }, "文件上传成功")
        
    except HTTPException:
        raise
    except Exception as e:
        return fail(f"文件上传失败: {str(e)}")


@router.post("/media/batch")
def upload_media_batch(
    files: List[UploadFile] = File(...),
    descriptions: Optional[List[str]] = Form(None),
    user: User = Depends(get_current_user)
):
    """批量上传图片或视频文件"""
    try:
        if len(files) > 10:  # 限制批量上传数量
            return fail("一次最多只能上传10个文件")
        
        results = []
        
        for i, file in enumerate(files):
            try:
                # 验证文件类型
                media_type = validate_file_type(file)
                
                # 读取文件内容
                file_content = file.file.read()
                file.file.seek(0)
                
                # 验证文件大小
                validate_file_size(len(file_content))
                
                # 生成目录路径
                directory_path = file_signature_manager.generate_directory_path(user.id, media_type)
                os.makedirs(directory_path, exist_ok=True)
                
                # 生成唯一文件名
                unique_filename = generate_unique_filename(file.filename)
                
                # 完整文件路径
                file_path = os.path.join(directory_path, unique_filename)
                
                # 保存文件
                with open(file_path, "wb") as buffer:
                    buffer.write(file_content)
                
                # 生成相对路径
                relative_path = os.path.relpath(file_path, '.').replace('\\', '/')
                
                # 生成签名URL
                signed_url = file_signature_manager.generate_signed_url(relative_path)
                
                # 获取描述
                description = None
                if descriptions and i < len(descriptions):
                    description = descriptions[i]
                
                results.append({
                    "media_url": relative_path,  # 返回文件路径，不包含签名
                    "media_type": media_type,
                    "description": description,
                    "original_filename": file.filename,
                    "size": len(file_content),
                    "sort_order": i,
                    "file_path": relative_path,  # 保持兼容性
                    "signed_url": signed_url     # 如果前端需要立即预览，可以使用这个
                })
                
            except Exception as e:
                results.append({
                    "error": f"文件 {file.filename} 上传失败: {str(e)}",
                    "original_filename": file.filename
                })
        
        return ok(results, f"批量上传完成，共处理{len(files)}个文件")
        
    except Exception as e:
        return fail(f"批量上传失败: {str(e)}")


@router.delete("/media")
def delete_media(
    file_path: str,
    user: User = Depends(get_current_user)
):
    """删除媒体文件"""
    try:
        # 检查文件是否存在
        if os.path.exists(file_path):
            # 简单检查：确保文件路径在上传目录内（防止路径遍历攻击）
            abs_file_path = os.path.abspath(file_path)
            abs_upload_dir = os.path.abspath(settings.upload.base_dir)
            
            if not abs_file_path.startswith(abs_upload_dir):
                return fail("无权删除该文件")
            
            os.remove(file_path)
            return ok(None, "文件删除成功")
        else:
            return fail("文件不存在")
            
    except Exception as e:
        return fail(f"删除文件失败: {str(e)}")


# 文件访问路由已移动到 main.py 中，直接处理 /file 路径


@router.get("/info/{file_path:path}")
def get_file_info(
    file_path: str,
    user: User = Depends(get_current_user)
):
    """获取文件信息（需要认证）"""
    try:
        decoded_path = unquote(file_path)
        file_info = file_signature_manager.get_file_info(decoded_path)
        
        if file_info is None:
            return fail("文件不存在")
        
        return ok(file_info, "获取文件信息成功")
        
    except Exception as e:
        return fail(f"获取文件信息失败: {str(e)}")


@router.post("/refresh-url")
def refresh_file_url(
    file_path: str,
    expires_minutes: Optional[int] = None,
    user: User = Depends(get_current_user)
):
    """刷新文件访问URL（重新签名）"""
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return fail("文件不存在")
        
        # 生成新的签名URL
        signed_url = file_signature_manager.generate_signed_url(file_path, expires_minutes)
        
        return ok({
            "media_url": signed_url,
            "file_path": file_path
        }, "URL刷新成功")
        
    except Exception as e:
        return fail(f"URL刷新失败: {str(e)}")


@router.post("/avatar")
def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user)
):
    """上传用户头像（公开访问，无需签名）"""
    try:
        # 验证文件类型（只允许图片）
        if not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="头像只支持图片格式"
            )
        
        # 读取文件内容以获取大小
        file_content = file.file.read()
        file.file.seek(0)  # 重置文件指针
        
        # 验证文件大小（头像限制为2MB）
        if len(file_content) > 2 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="头像文件过大，最大允许2MB"
            )
        
        # 生成头像存储路径
        avatar_path = generate_avatar_path(user.id, file.filename)
        
        # 保存文件
        with open(avatar_path, "wb") as buffer:
            buffer.write(file_content)
        
        # 返回简化的访问URL（通过前端代理）
        # 从 uploads/avatars/xxx.jpg 提取文件名，返回 /avatars/xxx.jpg
        filename = os.path.basename(avatar_path)
        public_url = f"/avatars/{filename}"
        
        return ok({
            "media_url": public_url,  # 公开访问路径
            "media_type": "image",
            "original_filename": file.filename,
            "size": len(file_content)
        }, "头像上传成功")
        
    except HTTPException:
        raise
    except Exception as e:
        return fail(f"头像上传失败: {str(e)}")