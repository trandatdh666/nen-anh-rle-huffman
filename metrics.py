"""
Module: metrics.py
Tính toán Histogram, Entropy Shannon, các chỉ số nén (Compression Ratio, Space Saving, Bitrate)
và các độ đo kiểm tra tính toàn vẹn (Lossless Verification: MSE, PSNR, SHA-256).
"""

import math
import hashlib
from typing import Dict, Tuple, Any
import numpy as np

def compute_histogram(image: np.ndarray) -> np.ndarray:
    """
    Tính histogram cho ảnh (trên toàn bộ pixel của ảnh xám hoặc gộp các kênh màu).
    Trả về mảng 256 phần tử biểu thị số lần xuất hiện của mỗi mức xám từ 0 đến 255.
    """
    flat = image.ravel()
    hist = np.bincount(flat, minlength=256)
    return hist

def compute_entropy(image: np.ndarray) -> Tuple[float, np.ndarray, np.ndarray]:
    """
    Tính Shannon Entropy:
      H(X) = - sum(p_k * log2(p_k)) với p_k > 0
    Trả về:
      - entropy: giá trị entropy (bits/pixel hoặc bits/symbol)
      - probabilities: phân bố xác suất p_k (256 phần tử)
      - hist: số lượng pixel cho mỗi mức xám
    """
    flat = image.ravel()
    n_pixels = len(flat)
    if n_pixels == 0:
        return 0.0, np.zeros(256), np.zeros(256)
        
    hist = np.bincount(flat, minlength=256)
    probs = hist / n_pixels
    
    # Chỉ tính log2 cho các xác suất > 0
    non_zero = probs[probs > 0]
    entropy = -np.sum(non_zero * np.log2(non_zero))
    
    return float(entropy), probs, hist

def compute_channel_entropies(image: np.ndarray) -> Dict[str, float]:
    """
    Tính entropy theo từng kênh cho ảnh màu hoặc ảnh xám.
    """
    res = {}
    if image.ndim == 2:
        ent, _, _ = compute_entropy(image)
        res["Gray"] = ent
    elif image.ndim == 3:
        # OpenCV đọc ảnh màu theo thứ tự kênh B, G, R
        if image.shape[2] == 3:
            channel_names = ["B", "G", "R"]
        else:
            channel_names = [f"Kênh {i}" for i in range(image.shape[2])]
        for c in range(image.shape[2]):
            ent, _, _ = compute_entropy(image[:, :, c])
            res[channel_names[c]] = ent
        ent_all, _, _ = compute_entropy(image)
        res["Tổng hợp"] = ent_all
    return res

def compute_run_stats(image: np.ndarray) -> Dict[str, float]:
    """
    Thống kê dải chạy (run) theo đúng thứ tự quét mà RLE sử dụng
    (ảnh xám/nhị phân: quét theo hàng; ảnh màu: Planar - từng kênh một).
    Đây là đại lượng giải thích khả năng nén của RLE, vì entropy bậc 0 H(X)
    chỉ phụ thuộc histogram và KHÔNG phản ánh tương quan giữa các pixel liền kề.

    Trả về:
      - num_runs: số dải liên tiếp cùng giá trị
      - avg_run_length: độ dài dải trung bình = số pixel / số dải
      - single_run_percent: % dải có độ dài 1 (dải gây phình dữ liệu)
      - rle_pairs_estimate: số cặp (count, value) RLE cần (tính cả tách dải > 255)
      - rle_cr_estimate: CR ước lượng = N / (2 * số cặp)  (bỏ qua header)
    """
    if image.ndim == 3:
        seq = np.concatenate([image[:, :, ch].ravel() for ch in range(image.shape[2])])
    else:
        seq = image.ravel()
    n = seq.size
    if n == 0:
        return {"num_runs": 0, "avg_run_length": 0.0, "single_run_percent": 0.0,
                "rle_pairs_estimate": 0, "rle_cr_estimate": float("inf")}

    # Vị trí bắt đầu mỗi dải: phần tử đầu tiên + mọi chỗ giá trị thay đổi
    change = np.flatnonzero(seq[1:] != seq[:-1]) + 1
    starts = np.concatenate(([0], change))
    lengths = np.diff(np.concatenate((starts, [n])))

    num_runs = int(lengths.size)
    pairs = int(np.sum((lengths + 254) // 255))  # mỗi dải dài L cần ceil(L/255) cặp
    return {
        "num_runs": num_runs,
        "avg_run_length": float(n / num_runs),
        "single_run_percent": float(np.mean(lengths == 1) * 100.0),
        "rle_pairs_estimate": pairs,
        "rle_cr_estimate": float(n / (2 * pairs)),
    }


def check_shannon_bound(entropy: float, l_avg: float, eps: float = 1e-9) -> bool:
    """Kiểm tra định lý mã hóa nguồn của Shannon cho mã Huffman: H <= L_avg < H + 1."""
    return (entropy - eps) <= l_avg < (entropy + 1.0)


def compute_huffman_avg_length(freq_table: Dict[int, int], codes: Dict[int, str]) -> Tuple[float, float]:
    """
    Tính độ dài từ mã trung bình (Average Code Length):
      L_avg = sum(p_k * len(code_k))
    Và độ dư thừa (Redundancy):
      R = L_avg - H
    """
    total_count = sum(freq_table.values())
    if total_count == 0:
        return 0.0, 0.0
        
    l_avg = 0.0
    h = 0.0
    for sym, count in freq_table.items():
        p = count / total_count
        l_avg += p * len(codes[sym])
        if p > 0:
            h -= p * math.log2(p)
            
    redundancy = l_avg - h
    return l_avg, redundancy

def compute_compression_metrics(orig_bytes_len: int, comp_bytes_len: int, h: int, w: int) -> Dict[str, float]:
    """
    Tính toán các chỉ số nén:
      - Tỷ lệ nén (Compression Ratio - CR): S_orig / S_comp
      - Tỷ lệ tiết kiệm dung lượng (Space Saving %): (1 - S_comp / S_orig) * 100%
      - Tốc độ bit (Bitrate - bpp): S_comp * 8 / (H * W) (bits per pixel)
    """
    if comp_bytes_len == 0:
        cr = float('inf')
        saving = 100.0
        bpp = 0.0
    else:
        cr = orig_bytes_len / comp_bytes_len
        saving = (1.0 - (comp_bytes_len / orig_bytes_len)) * 100.0
        bpp = (comp_bytes_len * 8) / (h * w)
        
    return {
        "original_size": orig_bytes_len,
        "compressed_size": comp_bytes_len,
        "compression_ratio": cr,
        "space_saving_percent": saving,
        "bpp": bpp
    }

def verify_image_integrity(original: np.ndarray, decompressed: np.ndarray) -> Dict[str, Any]:
    """
    Kiểm tra tính toàn vẹn tuyệt đối của ảnh giải mã so với ảnh gốc:
      1. Kích thước và kiểu dữ liệu
      2. Kiểm tra chính xác từng pixel (np.array_equal)
      3. Mean Squared Error (MSE): = 0.0 nếu không mất dữ liệu
      4. Peak Signal-to-Noise Ratio (PSNR): = vô cùng (infinity)
      5. Mã băm mật mã SHA-256 của chuỗi byte gốc và giải mã
    """
    shape_match = (original.shape == decompressed.shape)
    dtype_match = (original.dtype == decompressed.dtype)
    
    if not shape_match or not dtype_match:
        return {
            "is_identical": False,
            "shape_match": shape_match,
            "dtype_match": dtype_match,
            "mse": float("nan"),
            "psnr": float("nan"),
            "max_abs_diff": float("nan"),
            "sha256_orig": hashlib.sha256(original.tobytes()).hexdigest(),
            "sha256_decomp": hashlib.sha256(decompressed.tobytes()).hexdigest(),
        }
        
    is_identical = np.array_equal(original, decompressed)
    diff = np.abs(original.astype(np.float64) - decompressed.astype(np.float64))
    max_abs_diff = float(np.max(diff))
    mse = float(np.mean(diff ** 2))
    
    if mse == 0.0:
        psnr = float("inf")
    else:
        psnr = 10.0 * math.log10((255.0 ** 2) / mse)
        
    sha256_orig = hashlib.sha256(original.tobytes()).hexdigest()
    sha256_decomp = hashlib.sha256(decompressed.tobytes()).hexdigest()
    
    return {
        "is_identical": is_identical,
        "shape_match": shape_match,
        "dtype_match": dtype_match,
        "max_abs_diff": max_abs_diff,
        "mse": mse,
        "psnr": psnr,
        "sha256_orig": sha256_orig,
        "sha256_decomp": sha256_decomp,
        "sha256_match": (sha256_orig == sha256_decomp)
    }

