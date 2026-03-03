"""imghdr module for Python 3.12"""
import struct

def what(file=None, h=None):
    """Detect image format"""
    if h is None and file:
        with open(file, 'rb') as f:
            h = f.read(32)
    elif h is None:
        return None
    
    # JPEG
    if h.startswith(b'\xff\xd8\xff'):
        return 'jpeg'
    # PNG
    if h.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    # GIF
    if h.startswith(b'GIF87a') or h.startswith(b'GIF89a'):
        return 'gif'
    # WebP
    if h.startswith(b'RIFF') and h[8:12] == b'WEBP':
        return 'webp'
    # BMP
    if h.startswith(b'BM'):
        return 'bmp'
    # TIFF
    if h.startswith(b'II*\x00') or h.startswith(b'MM\x00*'):
        return 'tiff'
    return None

def test():
    """Test function"""
    print("imghdr module loaded successfully")
