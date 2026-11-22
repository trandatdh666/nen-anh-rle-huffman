"""
Module: huffman.py
Cài đặt thuật toán Huffman Coding cho nén ảnh không mất dữ liệu.
Hỗ trợ nén bit-level (đóng gói bit thực sự thành các byte nhị phân).
Có header lưu tần số (frequency table) và kích thước ảnh để giải mã độc lập.
"""

import heapq
import struct
from collections import Counter
from typing import Dict, Optional, Tuple
import numpy as np

MAGIC_HUF = b"HUF1"

class HuffmanNode:
    """Nút trong cây Huffman"""
    def __init__(self, freq: int, symbol: Optional[int] = None, left=None, right=None, order: int = 0):
        self.freq = freq
        self.symbol = symbol  # Giá trị byte (0 - 255) hoặc None đối với nút cha
        self.left = left
        self.right = right
        self.order = order    # Thứ tự chèn để giải quyết xung đột khi tần số bằng nhau
        
    def __lt__(self, other: 'HuffmanNode') -> bool:
        if self.freq != other.freq:
            return self.freq < other.freq
        return self.order < other.order
        
    @property
    def is_leaf(self) -> bool:
        return self.left is None and self.right is None


def build_huffman_tree(freq_table: Dict[int, int]) -> Optional[HuffmanNode]:
    """
    Xây dựng cây Huffman từ bảng tần số.
    """
    if not freq_table:
        return None
        
    heap = []
    order = 0
    # Đưa các lá vào min-heap
    # Sắp xếp các ký hiệu trước để đảm bảo tính tất định (deterministic tree)
    for sym in sorted(freq_table.keys()):
        node = HuffmanNode(freq=freq_table[sym], symbol=sym, order=order)
        heapq.heappush(heap, node)
        order += 1
        
    # Trường hợp đặc biệt: chỉ có 1 ký hiệu duy nhất trong toàn bộ ảnh
    if len(heap) == 1:
        root = HuffmanNode(freq=heap[0].freq, left=heap[0], order=order)
        return root
        
    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        parent = HuffmanNode(
            freq=left.freq + right.freq,
            symbol=None,
            left=left,
            right=right,
            order=order
        )
        heapq.heappush(heap, parent)
        order += 1
        
    return heap[0]


def build_codes(root: Optional[HuffmanNode]) -> Dict[int, str]:
    """
    Duyệt cây Huffman để tạo bảng mã nhị phân (prefix code) cho từng ký hiệu.
    """
    codes = {}
    if root is None:
        return codes
        
    # Nếu chỉ có 1 ký hiệu
    if root.left and root.right is None and root.left.is_leaf:
        codes[root.left.symbol] = "0"
        return codes
        
    def _dfs(node: HuffmanNode, current_code: str):
        if node.is_leaf:
            codes[node.symbol] = current_code if current_code else "0"
            return
        if node.left:
            _dfs(node.left, current_code + "0")
        if node.right:
            _dfs(node.right, current_code + "1")
            
    _dfs(root, "")
    return codes


def huffman_encode_bytes(data: bytes, codes: Dict[int, str]) -> Tuple[bytes, int]:
    """
    Chuyển đổi chuỗi byte đầu vào thành chuỗi bit được đóng gói thành các byte.
    Trả về (packed_bytes, total_bits).
    """
    # Xây dựng bảng chuyển đổi nhanh: mỗi byte -> (bit_integer, bit_length)
    lookup = {}
    for sym, code_str in codes.items():
        lookup[sym] = (int(code_str, 2), len(code_str))
        
    buffer = 0
    buf_len = 0
    packed = bytearray()
    total_bits = 0
    
    for byte_val in data:
        val_bits, bits_count = lookup[byte_val]
        buffer = (buffer << bits_count) | val_bits
        buf_len += bits_count
        total_bits += bits_count
        
        while buf_len >= 8:
            buf_len -= 8
            packed.append((buffer >> buf_len) & 0xFF)
            buffer &= (1 << buf_len) - 1
            
    if buf_len > 0:
        packed.append((buffer << (8 - buf_len)) & 0xFF)
        
    return bytes(packed), total_bits


def huffman_decode_bytes(packed_data: bytes, root: HuffmanNode, total_symbols: int) -> bytes:
    """
    Giải mã dòng bit nhị phân thành chuỗi byte gốc dựa trên cây Huffman.
    """
    if total_symbols == 0:
        return b""
        
    # Trường hợp đặc biệt: chỉ có 1 ký hiệu duy nhất
    if root.left and root.right is None and root.left.is_leaf:
        single_sym = root.left.symbol
        return bytes([single_sym] * total_symbols)
        
    # Tăng tốc: thay vì duyệt cây từng bit, dựng sẵn bảng chuyển trạng thái theo BYTE.
    #   table[node_id][byte] = (các ký hiệu phát ra khi đọc 8 bit của byte, nút đang đứng sau đó)
    # Kết quả giải mã hoàn toàn giống duyệt từng bit (MSB -> LSB), chỉ nhanh hơn ~10 lần.
    internal = []
    stack = [root]
    while stack:
        node = stack.pop()
        if not node.is_leaf:
            internal.append(node)
            stack.extend(child for child in (node.left, node.right) if child is not None)
    node_id = {id(n): i for i, n in enumerate(internal)}

    table = []
    for start in internal:
        row = []
        for byte_val in range(256):
            node = start
            emitted = bytearray()
            for bit_pos in range(7, -1, -1):
                node = node.right if (byte_val >> bit_pos) & 1 else node.left
                if node.is_leaf:
                    emitted.append(node.symbol)
                    node = root
            row.append((bytes(emitted), node_id[id(node)]))
        table.append(row)

    decoded = bytearray()
    state = node_id[id(root)]
    for byte_val in packed_data:
        emitted, state = table[state][byte_val]
        decoded += emitted
        if len(decoded) >= total_symbols:
            # Các bit đệm cuối cùng có thể sinh thêm ký hiệu thừa -> cắt bỏ
            return bytes(decoded[:total_symbols])

    raise ValueError(f"Số byte giải mã ({len(decoded)}) không đủ so với kỳ vọng ({total_symbols})")


def compress_huffman(image: np.ndarray) -> bytes:
    """
    Nén ảnh numpy thành chuỗi byte định dạng nhị phân chuẩn Huffman.
    Đóng gói header:
      - Magic: 4 bytes (b"HUF1")
      - Height: uint32 (4 bytes)
      - Width: uint32 (4 bytes)
      - Channels: uint8 (1 byte)
      - Total bytes gốc: uint32 (4 bytes)
      - Số ký hiệu duy nhất K: uint16 (2 bytes)
      - Bảng tần số: K phần tử, mỗi phần tử gồm (symbol: uint8, freq: uint32) -> 5 bytes/ký hiệu
      - Bitstream payload
    """
    if image.dtype != np.uint8:
        image = image.astype(np.uint8)
        
    shape = image.shape
    if len(shape) == 2:
        h, w = shape
        c = 1
    elif len(shape) == 3:
        h, w, c = shape
    else:
        raise ValueError("Ảnh phải có 2 hoặc 3 chiều")
        
    raw_bytes = image.tobytes()
    total_bytes = len(raw_bytes)
    
    if total_bytes == 0:
        return b""
        
    # 1. Đếm tần số
    freq_table = dict(Counter(raw_bytes))
    
    # 2. Xây dựng cây Huffman và bảng mã
    tree = build_huffman_tree(freq_table)
    codes = build_codes(tree)
    
    # 3. Mã hóa bitstream
    packed_payload, total_bits = huffman_encode_bytes(raw_bytes, codes)
    
    # 4. Đóng gói Header
    # Magic (4s), H (I), W (I), C (B), TotalBytes (I), K (H)
    k = len(freq_table)
    header_fixed = struct.pack(">4sIIBIH", MAGIC_HUF, h, w, c, total_bytes, k)
    
    # Bảng tần số (symbol, freq)
    freq_data = bytearray()
    for sym in sorted(freq_table.keys()):
        freq_data.extend(struct.pack(">BI", sym, freq_table[sym]))
        
    return header_fixed + bytes(freq_data) + packed_payload


def decompress_huffman(compressed_data: bytes) -> np.ndarray:
    """
    Giải mã chuỗi byte Huffman thành mảng ảnh numpy gốc.
    """
    if len(compressed_data) < 19:
        raise ValueError("Dữ liệu nén không đủ độ dài header Huffman")
        
    magic, h, w, c, total_bytes, k = struct.unpack(">4sIIBIH", compressed_data[:19])
    if magic != MAGIC_HUF:
        raise ValueError("Định dạng file không hợp lệ, không phải header HUF1")
        
    offset = 19
    freq_table = {}
    for _ in range(k):
        sym, freq = struct.unpack(">BI", compressed_data[offset:offset + 5])
        freq_table[sym] = freq
        offset += 5
        
    packed_payload = compressed_data[offset:]
    
    # Tái tạo cây Huffman từ bảng tần số
    tree = build_huffman_tree(freq_table)
    
    # Giải mã payload
    raw_bytes = huffman_decode_bytes(packed_payload, tree, total_bytes)
    
    arr = np.frombuffer(raw_bytes, dtype=np.uint8)
    if c == 1:
        return arr.reshape((h, w))
    else:
        return arr.reshape((h, w, c))

