"""
Module: rle.py
Cài đặt thuật toán Run-Length Encoding (RLE) cho nén ảnh không mất dữ liệu (lossless).
Hỗ trợ ảnh nhị phân, ảnh xám (1 kênh) và ảnh màu RGB (3 kênh).
Với ảnh màu, áp dụng Planar RLE (nén theo từng kênh màu độc lập) để tăng khả năng
tận dụng các dải pixel liên tiếp cùng màu và tránh hiện tượng nhiễu xen kẽ kênh.
Dữ liệu nén được đóng gói thành file nhị phân hoàn chỉnh có header.
"""

import struct
import numpy as np

MAGIC_RLE = b"RLE1"  # Header định danh định dạng nén RLE

def rle_encode_bytes(data: bytes) -> bytes:
    """
    Mã hóa chuỗi byte 1D bằng RLE.
    Mỗi run được biểu diễn bằng cặp (count: uint8, value: uint8).
    Nếu run dài hơn 255, tách thành nhiều cặp có count <= 255.
    """
    if not data:
        return b""
    
    encoded = bytearray()
    n = len(data)
    i = 0
    
    while i < n:
        val = data[i]
        run_len = 1
        # Đếm số phần tử liên tiếp giống nhau (tối đa 255)
        while i + 1 < n and data[i + 1] == val and run_len < 255:
            run_len += 1
            i += 1
        encoded.append(run_len)
        encoded.append(val)
        i += 1
        
    return bytes(encoded)

def rle_decode_bytes(encoded_data: bytes, expected_length: int) -> bytes:
    """
    Giải mã chuỗi byte RLE thành chuỗi byte gốc.
    """
    if len(encoded_data) % 2 != 0:
        raise ValueError("Dữ liệu RLE hỏng: độ dài payload phải là số chẵn (các cặp count, value)")
    decoded = bytearray()
    i = 0
    n = len(encoded_data)
    
    while i < n:
        count = encoded_data[i]
        val = encoded_data[i + 1]
        decoded.extend([val] * count)
        i += 2
        
    if len(decoded) != expected_length:
        raise ValueError(f"Kích thước giải mã ({len(decoded)}) không khớp với kích thước kỳ vọng ({expected_length})")
        
    return bytes(decoded)

def compress_rle(image: np.ndarray) -> bytes:
    """
    Nén một mảng ảnh numpy (uint8) bằng RLE.
    Với ảnh màu (3 chiều), mã hóa theo từng kênh (Planar) để tối ưu độ dài dải.
    Đóng gói header:
      - Magic: 4 bytes (b"RLE1")
      - Height: uint32 (4 bytes)
      - Width: uint32 (4 bytes)
      - Channels: uint8 (1 byte: 1 cho ảnh xám/nhị phân, 3 cho ảnh màu)
      - Payload: dữ liệu nén RLE
    """
    if image.dtype != np.uint8:
        image = image.astype(np.uint8)
        
    shape = image.shape
    if len(shape) == 2:
        h, w = shape
        c = 1
        raw_bytes = image.tobytes()
    elif len(shape) == 3:
        h, w, c = shape
        # Planar RLE: Gom byte theo từng kênh màu để tăng độ dài dải liên tiếp
        raw_bytes = b"".join(image[:, :, ch].tobytes() for ch in range(c))
    else:
        raise ValueError("Ảnh phải có 2 chiều (xám/nhị phân) hoặc 3 chiều (màu)")
        
    payload = rle_encode_bytes(raw_bytes)
    
    # Đóng gói header: Magic (4s), Height (I), Width (I), Channels (B)
    header = struct.pack(">4sIIB", MAGIC_RLE, h, w, c)
    return header + payload

def decompress_rle(compressed_data: bytes) -> np.ndarray:
    """
    Giải mã chuỗi byte nén RLE thành ảnh numpy gốc.
    """
    if len(compressed_data) < 13:
        raise ValueError("Dữ liệu nén quá ngắn, không chứa đủ header RLE")
        
    magic, h, w, c = struct.unpack(">4sIIB", compressed_data[:13])
    if magic != MAGIC_RLE:
        raise ValueError("Định dạng không hợp lệ, không phải file nén RLE")
        
    payload = compressed_data[13:]
    expected_length = h * w * c
    raw_bytes = rle_decode_bytes(payload, expected_length)
    
    arr = np.frombuffer(raw_bytes, dtype=np.uint8)
    if c == 1:
        return arr.reshape((h, w))
    else:
        # Tái lập ảnh màu từ các kênh planar
        channels = [arr[ch * h * w : (ch + 1) * h * w].reshape((h, w)) for ch in range(c)]
        return np.stack(channels, axis=-1)
