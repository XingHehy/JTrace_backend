import os
import hmac
import hashlib
import base64
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, unquote
from typing import Optional, Dict, Any
import json

from ..core.config import load_settings


class FileSignatureManager:
    """文件访问签名管理器"""
    
    def __init__(self):
        self.settings = load_settings()
        self.upload_config = self.settings.upload
        self.signature_config = self.upload_config.access_signature
    
    def generate_directory_path(self, user_id: int, file_type: str = "image") -> str:
        """根据配置策略生成文件存储目录路径"""
        base_dir = self.upload_config.base_dir
        strategy = self.upload_config.directory_strategy
        now = datetime.now()
        
        if strategy == "date_user":
            # 格式: uploads/images/2024/09/22/user_123/
            return os.path.join(
                base_dir, 
                f"{file_type}s", 
                now.strftime("%Y"), 
                now.strftime("%m"), 
                now.strftime("%d"),
                f"user_{user_id}"
            )
        elif strategy == "user_date":
            # 格式: uploads/images/user_123/2024/09/22/
            return os.path.join(
                base_dir, 
                f"{file_type}s", 
                f"user_{user_id}",
                now.strftime("%Y"), 
                now.strftime("%m"), 
                now.strftime("%d")
            )
        else:  # simple
            # 格式: uploads/images/
            return os.path.join(base_dir, f"{file_type}s")
    
    def generate_signed_url(self, file_path: str, expires_minutes: Optional[int] = None) -> str:
        """生成带签名的文件访问URL"""
        if not self.signature_config.enabled:
            return f"/{file_path}"
        
        # 计算过期时间
        if expires_minutes is None:
            expires_minutes = self.signature_config.expires_minutes
        
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
        expires_timestamp = int(expires_at.timestamp())
        
        # 准备签名数据
        signature_data = {
            "path": file_path,
            "expires": expires_timestamp
        }
        
        # 生成签名
        signature = self._generate_signature(signature_data)
        
        # 构建签名URL
        encoded_path = quote(file_path, safe='/')
        return f"/file/{encoded_path}?signature={signature}&expires={expires_timestamp}"
    
    def verify_signed_url(self, file_path: str, signature: str, expires_timestamp: int) -> Dict[str, Any]:
        """验证签名URL的有效性"""
        result = {
            "valid": False,
            "error": None,
            "file_path": file_path
        }
        
        if not self.signature_config.enabled:
            result["valid"] = True
            return result
        
        # 检查是否过期
        current_timestamp = int(datetime.now(timezone.utc).timestamp())
        if current_timestamp > expires_timestamp:
            result["error"] = "URL已过期"
            return result
        
        # 验证签名
        signature_data = {
            "path": file_path,
            "expires": expires_timestamp
        }
        
        expected_signature = self._generate_signature(signature_data)
        if not hmac.compare_digest(signature, expected_signature):
            result["error"] = "签名验证失败"
            return result
        
        result["valid"] = True
        return result
    
    def _generate_signature(self, data: Dict[str, Any]) -> str:
        """生成数据签名"""
        # 将数据转换为JSON字符串并排序键
        json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
        
        # 使用HMAC-SHA256生成签名
        signature = hmac.new(
            self.signature_config.secret_key.encode('utf-8'),
            json_str.encode('utf-8'),
            hashlib.sha256
        )
        
        # Base64编码并URL安全处理
        return base64.urlsafe_b64encode(signature.digest()).decode('utf-8').rstrip('=')
    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        if not os.path.exists(file_path):
            return None
        
        stat = os.stat(file_path)
        return {
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime, timezone.utc),
            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc),
            "exists": True
        }
    
    def is_allowed_file_type(self, content_type: str) -> tuple[bool, str]:
        """检查文件类型是否被允许"""
        if content_type in self.upload_config.allowed_image_types:
            return True, "image"
        elif content_type in self.upload_config.allowed_video_types:
            return True, "video"
        else:
            return False, "unknown"
    
    def is_file_size_allowed(self, file_size: int) -> bool:
        """检查文件大小是否被允许"""
        return file_size <= self.upload_config.max_file_size


# 全局实例
file_signature_manager = FileSignatureManager()
