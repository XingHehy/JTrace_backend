"""
头像相关工具函数
"""


def convert_avatar_url(avatar_url: str) -> str:
    """
    转换头像URL格式，将 /uploads/avatars/ 转换为 /avatars/
    
    Args:
        avatar_url: 原始头像URL路径
        
    Returns:
        转换后的头像URL路径
        
    Examples:
        >>> convert_avatar_url("/uploads/avatars/avatar_xxx.jpg")
        "/avatars/avatar_xxx.jpg"
        >>> convert_avatar_url(None)
        None
        >>> convert_avatar_url("/other/path.jpg")
        "/other/path.jpg"
    """
    if not avatar_url:
        return avatar_url
    
    if avatar_url.startswith('/uploads/avatars/'):
        # 提取文件名，转换为新格式
        filename = avatar_url.replace('/uploads/avatars/', '')
        return f'/avatars/{filename}'
    
    return avatar_url
