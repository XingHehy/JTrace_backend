"""
媒体文件相关工具函数
"""
from urllib.parse import unquote
from .file_signature import file_signature_manager


def generate_media_url(file_path: str) -> str:
    """
    根据文件路径生成签名URL
    
    Args:
        file_path: 文件路径，可能包含签名参数
        
    Returns:
        生成的签名URL或直接返回的外部URL
        
    Examples:
        >>> generate_media_url("uploads/images/2025/09/22/user_1/image.jpg")
        "/file/uploads/images/2025/09/22/user_1/image.jpg?signature=xxx&expires=xxx"
        >>> generate_media_url("https://picsum.photos/800/600")
        "https://picsum.photos/800/600"
        >>> generate_media_url("/file/uploads/images/xxx.jpg?signature=old")
        "/file/uploads/images/xxx.jpg?signature=new&expires=new"
    """
    try:
        # 如果是外部HTTP/HTTPS链接，直接返回
        if file_path.startswith('http://') or file_path.startswith('https://'):
            return file_path
            
        # 如果已经是签名URL，先提取文件路径
        if file_path.startswith('/file/'):
            # 兼容旧数据：提取文件路径部分
            url_parts = file_path.split('/file/')
            if len(url_parts) > 1:
                file_path_with_params = url_parts[1]
                file_path = file_path_with_params.split('?')[0]  # 去掉查询参数
                file_path = unquote(file_path)
                
                # 再次检查解码后的路径是否为外部链接
                if file_path.startswith('http://') or file_path.startswith('https://'):
                    return file_path
        
        # 生成新的签名URL
        signed_url = file_signature_manager.generate_signed_url(file_path)
        return signed_url
        
    except Exception as e:
        print(f"生成媒体URL失败: {e}")
        # 降级处理：如果是外部链接，直接返回
        if file_path.startswith('http://') or file_path.startswith('https://'):
            return file_path
        # 如果是文件路径，至少返回一个基本URL
        if not file_path.startswith('/') and not file_path.startswith('http'):
            return f"/{file_path}"
        return file_path
