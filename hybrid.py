"""
Module: hybrid.py
Nén kết hợp RLE -> Huffman (mở rộng so với yêu cầu đề bài).

Ý tưởng:
  - RLE khai thác dư thừa KHÔNG GIAN (các pixel liền kề giống nhau) -> chuỗi cặp (count, value).
  - Chuỗi byte sau RLE vẫn còn dư thừa THỐNG KÊ (ví dụ count = 255 và value = 0/255 xuất hiện rất nhiều
    trong ảnh nhị phân) -> tiếp tục nén bằng Huffman.
  Đây chính là nguyên lý của các chuẩn thực tế như CCITT Group 3 Fax (Modified Huffman = RLE + Huffman).

Định dạng file: một file Huffman (HUF1) bọc toàn bộ file RLE (RLE1) bên trong,
nên giải mã chỉ cần: Huffman decode -> RLE decode.
"""

import numpy as np
from rle import compress_rle, decompress_rle
from huffman import compress_huffman, decompress_huffman


def compress_rle_huffman(image: np.ndarray) -> bytes:
    """Nén ảnh: RLE trước, sau đó Huffman trên chuỗi byte RLE."""
    rle_bytes = compress_rle(image)
    rle_arr = np.frombuffer(rle_bytes, dtype=np.uint8).reshape(1, -1)
    return compress_huffman(rle_arr)


def decompress_rle_huffman(compressed_data: bytes) -> np.ndarray:
    """Giải mã: Huffman decode ra chuỗi byte RLE, sau đó RLE decode ra ảnh."""
    rle_arr = decompress_huffman(compressed_data)
    return decompress_rle(rle_arr.tobytes())
