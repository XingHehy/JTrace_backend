"""
加密解密工具类 - 用于敏感配置加密传输
"""
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, Any
import jwt
from ..core.config import load_settings


class ConfigEncryption:
    """配置加密类"""
    
    def __init__(self):
        self.settings = load_settings()
        if not self.settings.maps:
            raise ValueError("Map settings not configured")
        
        self.encryption_config = self.settings.maps.encryption
        self.secret_key = self.encryption_config.secret_key
        self.algorithm = self.encryption_config.algorithm
    
    def encrypt_config(self, config_data: Dict[str, Any], expires_minutes: int = 60) -> str:
        """
        加密配置数据
        
        Args:
            config_data: 要加密的配置数据
            expires_minutes: 过期时间（分钟）
            
        Returns:
            加密后的JWT token字符串
        """
        if not self.encryption_config.enabled:
            # 如果未启用加密，直接返回base64编码
            return base64.b64encode(json.dumps(config_data).encode()).decode()
        
        # 添加过期时间
        payload = {
            'data': config_data,
            'exp': datetime.utcnow() + timedelta(minutes=expires_minutes),
            'iat': datetime.utcnow()
        }
        
        # 使用JWT加密
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def decrypt_config(self, encrypted_token: str) -> Dict[str, Any]:
        """
        解密配置数据
        
        Args:
            encrypted_token: 加密的token字符串
            
        Returns:
            解密后的配置数据
            
        Raises:
            jwt.ExpiredSignatureError: token已过期
            jwt.InvalidTokenError: token无效
        """
        if not self.encryption_config.enabled:
            # 如果未启用加密，直接base64解码
            return json.loads(base64.b64decode(encrypted_token.encode()).decode())
        
        # JWT解密
        payload = jwt.decode(encrypted_token, self.secret_key, algorithms=[self.algorithm])
        return payload['data']
    
    def get_map_config(self, expires_minutes: int = 60) -> str:
        """
        获取加密的地图配置
        
        Args:
            expires_minutes: 过期时间（分钟）
            
        Returns:
            加密后的地图配置token
        """
        map_config = {
            'amap': {
                'api_key': self.settings.maps.amap.api_key,
                'security_js_code': self.settings.maps.amap.security_js_code,
                'version': self.settings.maps.amap.version,
                'ui_version': self.settings.maps.amap.ui_version
            }
        }
        
        return self.encrypt_config(map_config, expires_minutes)


# 全局实例
config_encryption = None

def get_config_encryption() -> ConfigEncryption:
    """获取配置加密实例（单例模式）"""
    global config_encryption
    if config_encryption is None:
        config_encryption = ConfigEncryption()
    return config_encryption
