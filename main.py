"""
Chương trình chính: main.py
Đề tài 30: Nén ảnh không mất dữ liệu bằng RLE và Huffman
Nhóm 30: Trần Quốc Đạt (Trưởng Nhóm), Lê Văn Duy

Chức năng:
  1. Thử nghiệm chuyên sâu trên bộ ảnh đại diện (Ảnh nhị phân tài liệu, Ảnh nhị phân Otsu, Ảnh xám, Ảnh màu)
  2. Tự động quét và đánh giá toàn bộ tập ảnh thực tế trong thư mục images/ (7 ảnh phong cảnh)
  3. Tính toán Histogram, Shannon Entropy H(X) và giới hạn lý thuyết nguồn tin
  4. Nén & giải mã RLE (hỗ trợ Planar RLE cho ảnh màu) và Huffman bit-level (.rle, .huf)
  5. Kiểm tra tính toàn vẹn tuyệt đối (MSE = 0.0, PSNR = Inf dB, SHA-256 match)
  6. Xuất biểu đồ trực quan hóa và bảng báo cáo tổng hợp
"""

import os
import sys
import time
import json
import math
import argparse
from typing import Dict, Any, List
import cv2
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rle import compress_rle, decompress_rle
from huffman import compress_huffman, decompress_huffman, build_codes, build_huffman_tree
from hybrid import compress_rle_huffman, decompress_rle_huffman
from metrics import (
    compute_entropy,
    compute_channel_entropies,
    compute_huffman_avg_length,
    compute_compression_metrics,
    compute_run_stats,
    check_shannon_bound,
    verify_image_integrity,
)
from dataset_generator import ensure_sample_images
from visualize import (
    plot_histograms_and_entropy,
    plot_compression_comparison,
    plot_visual_integrity,
)


def _encode_save_decode(image, encoder, decoder, filepath, h, w, orig_size):
    """
    Nén -> ghi file nhị phân ra đĩa -> ĐỌC LẠI file từ đĩa -> giải mã -> đo đạc & kiểm tra toàn vẹn.
    Giải mã từ file trên đĩa (không dùng bytes trong RAM) để chứng minh file nén tự chứa đủ thông tin.
    """
    t0 = time.perf_counter()
    comp = encoder(image)
    t_enc = time.perf_counter() - t0
    with open(filepath, "wb") as f:
        f.write(comp)

    with open(filepath, "rb") as f:
        comp_from_disk = f.read()
    t0 = time.perf_counter()
    decoded = decoder(comp_from_disk)
    t_dec = time.perf_counter() - t0

    metrics = compute_compression_metrics(orig_size, os.path.getsize(filepath), h, w)
    metrics.update({"enc_time_ms": t_enc * 1000, "dec_time_ms": t_dec * 1000, "filepath": filepath})
    return metrics, verify_image_integrity(image, decoded), decoded


def explain_result(res: Dict[str, Any]) -> List[str]:
    """Sinh lời giải thích khả năng nén dựa trên histogram, entropy và thống kê dải chạy."""
    H = res["entropy"]
    rs = res["run_stats"]
    l_avg = res["huffman_l_avg"]
    lines = []
    lines.append(
        f"Histogram có {res['unique_symbols']} mức khác nhau, H(X) = {H:.4f} bit/pixel. "
        f"Huffman đạt L_avg = {l_avg:.4f} bit (thỏa H <= L_avg < H+1: "
        f"{'ĐÚNG' if res['shannon_bound_ok'] else 'SAI'}), nên CR(Huffman) ~ 8/L_avg = {8 / l_avg:.2f}x "
        f"(thực tế {res['huffman']['compression_ratio']:.2f}x, chênh lệch nhỏ do header + bảng tần số)."
    )
    if H < 1.0 and l_avg <= 1.0 + 1e-9:
        lines.append(
            f"Huffman gán mỗi pixel ít nhất 1 bit nên với ảnh 2 mức L_avg = 1 bit dù H = {H:.3f} < 1 "
            f"-> Huffman bị chặn ở 8x, không đạt được 8/H = {res['theoretical_max_cr']:.2f}x."
        )
    lines.append(
        f"Thống kê dải: {rs['num_runs']} dải, độ dài TB = {rs['avg_run_length']:.2f} pixel, "
        f"{rs['single_run_percent']:.1f}% dải dài 1. Mỗi dải tốn 2 byte nên RLE chỉ có lợi khi độ dài TB > 2 "
        f"-> CR(RLE) ~ {rs['rle_cr_estimate']:.2f}x (thực tế {res['rle']['compression_ratio']:.2f}x)."
    )
    if res["rle"]["compression_ratio"] > res["theoretical_max_cr"]:
        lines.append(
            "RLE vượt 8/H(X) vì 8/H(X) chỉ là giới hạn khi mã hóa TỪNG PIXEL ĐỘC LẬP (entropy bậc 0, chỉ dựa vào "
            "histogram); RLE khai thác thêm tương quan giữa các pixel liền kề mà histogram không thể hiện."
        )
    if res["rle"]["compression_ratio"] < 1.0:
        lines.append(
            "RLE làm PHÌNH dữ liệu vì các pixel liền kề trong ảnh tự nhiên thường khác nhau (dải rất ngắn) "
            "-> gần như mỗi pixel tốn 2 byte."
        )
    best = max((("RLE", res["rle"]), ("Huffman", res["huffman"]), ("RLE+Huffman", res["hybrid"])),
               key=lambda kv: kv[1]["compression_ratio"])
    lines.append(f"Phương pháp tốt nhất cho ảnh này: {best[0]} ({best[1]['compression_ratio']:.2f}x).")
    return lines


def process_single_image(
    name: str,
    image: np.ndarray,
    out_dir: str = "output"
) -> Dict[str, Any]:
    """
    Xử lý nén, giải mã, đo lường và kiểm tra toàn vẹn cho một ảnh cụ thể.
    """
    os.makedirs(out_dir, exist_ok=True)
    comp_dir = os.path.join(out_dir, "compressed_files")
    os.makedirs(comp_dir, exist_ok=True)
    
    h, w = image.shape[:2]
    c = 1 if image.ndim == 2 else image.shape[2]
    orig_bytes = image.tobytes()
    orig_size = len(orig_bytes)
    orig_bpp = (orig_size * 8) / (h * w)
    
    # 1. Tính Histogram và Shannon Entropy
    entropy_val, probs, hist = compute_entropy(image)
    channel_entropies = compute_channel_entropies(image)
    theoretical_max_cr = 8.0 / entropy_val if entropy_val > 0 else float('inf')
    
    run_stats = compute_run_stats(image)
    safe_name = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in name.lower())

    # 2. Nén và giải mã RLE (giải mã từ file .rle đọc lại từ đĩa)
    rle_metrics, rle_integrity, rle_decoded = _encode_save_decode(
        image, compress_rle, decompress_rle, os.path.join(comp_dir, f"{safe_name}.rle"), h, w, orig_size)

    # 3. Nén và giải mã Huffman (giải mã từ file .huf)
    from collections import Counter
    freq_table = dict(Counter(orig_bytes))
    tree = build_huffman_tree(freq_table)
    codes = build_codes(tree)
    l_avg, redundancy = compute_huffman_avg_length(freq_table, codes)
    huf_metrics, huf_integrity, huf_decoded = _encode_save_decode(
        image, compress_huffman, decompress_huffman, os.path.join(comp_dir, f"{safe_name}.huf"), h, w, orig_size)

    # 4. Mở rộng: kết hợp RLE -> Huffman (file .rlh)
    hyb_metrics, hyb_integrity, _ = _encode_save_decode(
        image, compress_rle_huffman, decompress_rle_huffman, os.path.join(comp_dir, f"{safe_name}.rlh"),
        h, w, orig_size)

    return {
        "name": name,
        "shape": image.shape,
        "channels": c,
        "orig_size": orig_size,
        "orig_bpp": orig_bpp,
        "entropy": entropy_val,
        "channel_entropies": channel_entropies,
        "theoretical_max_cr": theoretical_max_cr,
        "huffman_l_avg": l_avg,
        "huffman_redundancy": redundancy,
        "unique_symbols": len(freq_table),
        "shannon_bound_ok": check_shannon_bound(entropy_val, l_avg),
        "run_stats": run_stats,
        "hybrid": hyb_metrics,
        "hybrid_integrity": hyb_integrity,
        "rle": rle_metrics,
        "rle_integrity": rle_integrity,
        "rle_decoded": rle_decoded,
        "huffman": huf_metrics,
        "huffman_integrity": huf_integrity,
        "huffman_decoded": huf_decoded,
        "image": image,
    }


def print_comparison_tables(results: list, title="BÁO CÁO KẾT QUẢ NÉN ẢNH LOSSLESS (RLE & HUFFMAN)"):
    """In bảng so sánh chi tiết ra terminal."""
    print("\n" + "=" * 115)
    print(f"{title:^115}")
    print("=" * 115)
    
    # Bảng 1: Thống kê Histogram & Entropy
    print("\n[BẢNG 1: THỐNG KÊ HISTOGRAM & ENTROPY SHANNON - GIẢI THÍCH KHẢ NĂNG NÉN CỦA HUFFMAN]")
    print("-" * 115)
    print(f"{'Loại ảnh':<25} | {'Kích thước':<12} | {'Số mức':>6} | {'H(X)':>7} | {'L_avg':>7} | "
          f"{'Dư thừa':>7} | {'H<=L<H+1':<8} | {'8/H (bậc 0)':>11}")
    print("-" * 115)
    for res in results:
        shape_str = "x".join(str(d) for d in res['shape'])
        print(f"{res['name']:<25} | {shape_str:<12} | {res['unique_symbols']:>6} | {res['entropy']:>7.4f} | "
              f"{res['huffman_l_avg']:>7.4f} | {res['huffman_redundancy']:>7.4f} | "
              f"{('Đúng' if res['shannon_bound_ok'] else 'SAI'):<8} | {res['theoretical_max_cr']:>10.2f}x")
    print("-" * 115)
    print("  Ghi chú: 8/H là giới hạn nén khi mã hóa TỪNG PIXEL ĐỘC LẬP (entropy bậc 0). "
          "Huffman còn bị chặn bởi L_avg >= 1 bit (tức <= 8x).")

    # Bảng 2: Thống kê dải chạy - giải thích khả năng nén của RLE
    print("\n[BẢNG 2: THỐNG KÊ DẢI CHẠY (RUN) - GIẢI THÍCH KHẢ NĂNG NÉN CỦA RLE]")
    print("-" * 115)
    print(f"{'Loại ảnh':<25} | {'Số dải':>10} | {'Độ dài TB':>10} | {'% dải dài 1':>12} | "
          f"{'CR RLE ước lượng':>17} | {'CR RLE thực tế':>15}")
    print("-" * 115)
    for res in results:
        rs = res['run_stats']
        print(f"{res['name']:<25} | {rs['num_runs']:>10} | {rs['avg_run_length']:>10.2f} | "
              f"{rs['single_run_percent']:>11.1f}% | {rs['rle_cr_estimate']:>16.2f}x | "
              f"{res['rle']['compression_ratio']:>14.2f}x")
    print("-" * 115)
    print("  Ghi chú: mỗi dải tốn 2 byte (count, value) -> RLE chỉ có lợi khi độ dài dải trung bình > 2.")

    # Bảng 3: So sánh tỷ lệ nén
    print("\n[BẢNG 3: SO SÁNH TỶ LỆ NÉN (RLE vs HUFFMAN vs RLE+HUFFMAN)]")
    print("-" * 115)
    print(f"{'Loại ảnh':<25} | {'Gốc (B)':>9} | {'RLE (B)':>9} {'CR':>7} {'Saving':>8} | "
          f"{'HUF (B)':>9} {'CR':>7} {'Saving':>8} | {'RLE+HUF (B)':>11} {'CR':>7}")
    print("-" * 115)
    for res in results:
        r, hf, hb = res['rle'], res['huffman'], res['hybrid']
        print(f"{res['name']:<25} | {res['orig_size']:>9} | "
              f"{r['compressed_size']:>9} {r['compression_ratio']:>6.2f}x {r['space_saving_percent']:>7.1f}% | "
              f"{hf['compressed_size']:>9} {hf['compression_ratio']:>6.2f}x {hf['space_saving_percent']:>7.1f}% | "
              f"{hb['compressed_size']:>11} {hb['compression_ratio']:>6.2f}x")
    print("-" * 115)

    # Bảng 4: Kiểm tra tính toàn vẹn
    print("\n[BẢNG 4: KIỂM TRA TÍNH TOÀN VẸN - GIẢI MÃ TỪ FILE NÉN ĐỌC LẠI TỪ ĐĨA]")
    print("-" * 115)
    print(f"{'Loại ảnh':<25} | {'Thuật toán':<10} | {'Trùng 100%?':<12} | {'Max Diff':>8} | {'MSE':>6} | "
          f"{'PSNR (dB)':<12} | {'SHA-256 Khớp?'}")
    print("-" * 115)
    for res in results:
        for algo, integ in [("RLE", res['rle_integrity']), ("Huffman", res['huffman_integrity']),
                            ("RLE+HUF", res['hybrid_integrity'])]:
            ident_str = "ĐÚNG" if integ['is_identical'] else "SAI"
            psnr_str = "Inf (vô cực)" if math.isinf(integ['psnr']) else f"{integ['psnr']:.2f}"
            sha_str = "KHỚP" if integ['sha256_match'] else "KHÁC"
            print(f"{res['name']:<25} | {algo:<10} | {ident_str:<12} | {integ['max_abs_diff']:>8.1f} | "
                  f"{integ['mse']:>6.1f} | {psnr_str:<12} | {sha_str}")
    print("-" * 115)

    # Phần 5: Giải thích khả năng nén
    print("\n[PHẦN 5: GIẢI THÍCH KHẢ NĂNG NÉN DỰA TRÊN HISTOGRAM, ENTROPY VÀ DẢI CHẠY]")
    for res in results:
        print(f"\n  * {res['name']}:")
        for line in explain_result(res):
            print(f"    - {line}")


DATASET_CODECS = {
    "rle": (compress_rle, decompress_rle),
    "huf": (compress_huffman, decompress_huffman),
    "hyb": (compress_rle_huffman, decompress_rle_huffman),
}


def _analyze_dataset_image(img: np.ndarray) -> Dict[str, Any]:
    """Phân tích đầy đủ 1 ảnh: entropy, dải chạy, CR của 3 phương pháp và kiểm tra giải mã."""
    h, w = img.shape[:2]
    ent = compute_entropy(img)[0]
    rs = compute_run_stats(img)
    row = {"entropy": ent, "avg_run": rs["avg_run_length"], "levels": int(len(np.unique(img)))}
    lossless = True
    for key, (enc, dec) in DATASET_CODECS.items():
        comp = enc(img)
        row[f"cr_{key}"] = img.nbytes / len(comp)
        row[f"bpp_{key}"] = len(comp) * 8 / (h * w)
        lossless &= verify_image_integrity(img, dec(comp))["sha256_match"]
    row["lossless"] = bool(lossless)
    return row


def run_benchmark_on_dataset(images_dir="images", out_dir="output"):
    """
    Chạy thực nghiệm trên TOÀN BỘ ảnh trong images_dir. Mỗi ảnh màu được tách thành 3 phiên bản:
    nhị phân (ngưỡng Otsu), xám, màu. Với mỗi phiên bản: tính H(X), độ dài dải TB, CR của
    RLE / Huffman / RLE+Huffman và GIẢI MÃ LẠI để kiểm tra toàn vẹn (SHA-256).
    """
    valid_files = [f for f in sorted(os.listdir(images_dir))
                   if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
    if not valid_files:
        return []

    types = [("bin", "Nhị phân (Otsu)"), ("gray", "Ảnh xám"), ("color", "Ảnh màu")]
    print("\n" + "=" * 125)
    print(f"{f'PHÂN TÍCH & SO SÁNH TRÊN TOÀN BỘ {len(valid_files)} ẢNH THỰC TẾ (DATASET)':^125}")
    print("=" * 125)

    dataset_summary = []
    for fname in valid_files:
        img_col = cv2.imread(os.path.join(images_dir, fname))
        if img_col is None:
            continue
        img_gray = cv2.cvtColor(img_col, cv2.COLOR_BGR2GRAY)
        _, img_bin = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        entry = {"filename": fname, "dimensions": f"{img_col.shape[1]}x{img_col.shape[0]}"}
        for key, img in (("bin", img_bin), ("gray", img_gray), ("color", img_col)):
            for k, v in _analyze_dataset_image(img).items():
                entry[f"{key}_{k}"] = v
        dataset_summary.append(entry)
        print(f"  [+] {fname} ({entry['dimensions']}) - xong")

    # Bảng chi tiết cho từng loại ảnh
    for key, label in types:
        print(f"\n[DATASET - {label.upper()}]")
        print("-" * 125)
        print(f"{'Tên file ảnh':<36} | {'Kích thước':>10} | {'Số mức':>6} | {'H(X)':>6} | {'Dải TB':>7} | "
              f"{'CR RLE':>7} | {'CR HUF':>7} | {'CR RLE+HUF':>10} | {'Tốt nhất':<11} | {'Toàn vẹn'}")
        print("-" * 125)
        for e in dataset_summary:
            crs = {"RLE": e[f"{key}_cr_rle"], "Huffman": e[f"{key}_cr_huf"], "RLE+HUF": e[f"{key}_cr_hyb"]}
            best = max(crs, key=crs.get)
            print(f"{e['filename'][:36]:<36} | {e['dimensions']:>10} | {e[f'{key}_levels']:>6} | "
                  f"{e[f'{key}_entropy']:>6.3f} | {e[f'{key}_avg_run']:>7.2f} | "
                  f"{crs['RLE']:>6.2f}x | {crs['Huffman']:>6.2f}x | {crs['RLE+HUF']:>9.2f}x | {best:<11} | "
                  f"{'KHỚP' if e[f'{key}_lossless'] else 'LỖI'}")
        print("-" * 125)

    # Bảng tổng kết theo loại ảnh
    n = len(dataset_summary)
    print(f"\n[TỔNG KẾT TRÊN {n} ẢNH: TRUNG BÌNH (TB) VÀ TRUNG VỊ (TV) THEO LOẠI ẢNH]")
    print("-" * 125)
    print(f"{'Loại ảnh':<17} | {'H(X) TB':>7} | {'Dải TB':>7} | {'CR RLE':^22} | {'CR Huffman':^22} | "
          f"{'CR RLE+Huffman':^22} | {'Toàn vẹn'}")
    print("-" * 125)
    overview = {}
    for key, label in types:
        def stat(field):
            vals = [e[f"{key}_{field}"] for e in dataset_summary]
            return float(np.mean(vals)), float(np.min(vals)), float(np.max(vals)), float(np.median(vals))
        st = {f: stat(f) for f in ("entropy", "avg_run", "cr_rle", "cr_huf", "cr_hyb")}
        ok = sum(e[f"{key}_lossless"] for e in dataset_summary)
        wins = {name: 0 for name in ("RLE", "Huffman", "RLE+HUF")}
        for e in dataset_summary:
            crs = {"RLE": e[f"{key}_cr_rle"], "Huffman": e[f"{key}_cr_huf"], "RLE+HUF": e[f"{key}_cr_hyb"]}
            wins[max(crs, key=crs.get)] += 1
        overview[key] = {"label": label, **{f: dict(zip(("mean", "min", "max", "median"), v)) for f, v in st.items()},
                         "lossless_count": ok, "wins": wins}
        fmt = lambda t: f"TB {t[0]:5.2f}x | TV {t[3]:5.2f}x"
        print(f"{label:<17} | {st['entropy'][0]:>7.3f} | {st['avg_run'][0]:>7.2f} | {fmt(st['cr_rle']):>22} | "
              f"{fmt(st['cr_huf']):>22} | {fmt(st['cr_hyb']):>22} | {ok}/{n} KHỚP")
    print("-" * 125)
    print("  Số lần thắng (CR cao nhất): " + "; ".join(
        f"{o['label']}: " + ", ".join(f"{k} {v}" for k, v in o["wins"].items()) for o in overview.values()))

    with open(os.path.join(out_dir, "dataset_summary.json"), "w", encoding="utf-8") as f:
        json.dump({"images": dataset_summary, "overview": overview}, f, indent=2, ensure_ascii=False)
    try:
        from visualize import plot_dataset_comparison
        plot_dataset_comparison(dataset_summary, os.path.join(out_dir, "dataset_comparison.png"))
    except ImportError:
        pass
    return dataset_summary


def run_pipeline(custom_image_path: str = None, out_dir: str = "output"):
    os.makedirs(out_dir, exist_ok=True)
    images_to_test = {}
    
    # 1. Đảm bảo có ảnh văn bản đồ họa nhị phân chuẩn hóa
    bin_doc_path, _, _ = ensure_sample_images("images/synthetic")
    doc_binary = cv2.imread(bin_doc_path, cv2.IMREAD_GRAYSCALE)
    images_to_test["Ảnh nhị phân (Tài liệu)"] = doc_binary
    
    # 2. Lựa chọn ảnh thực tế từ thư mục images/
    target_img_path = custom_image_path
    if not target_img_path or not os.path.isfile(target_img_path):
        # Ưu tiên chọn ảnh thực tế ruong_bac_thang_binh_minh hoặc dong_co_ven_ho_cay_lieu
        candidates = ["dong_co_ven_ho_cay_lieu.png", "ruong_bac_thang_binh_minh.png", "thung_lung_song_nui.png"]
        for c in candidates:
            p = os.path.join("images", c)
            if os.path.isfile(p):
                target_img_path = p
                break
                
    if target_img_path and os.path.isfile(target_img_path):
        print(f"\n[+] Sử dụng ảnh thực tế: {target_img_path}")
        real_col = cv2.imread(target_img_path)
        real_gray = cv2.cvtColor(real_col, cv2.COLOR_BGR2GRAY)
        _, real_bin = cv2.threshold(real_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        images_to_test["Ảnh nhị phân (Otsu)"] = real_bin
        images_to_test["Ảnh xám"] = real_gray
        images_to_test["Ảnh màu RGB"] = real_col
    else:
        print("[!] Không tìm thấy ảnh thực tế, sinh ảnh mẫu tổng hợp.")
        _, gray_p, col_p = ensure_sample_images("images/synthetic")
        images_to_test["Ảnh xám"] = cv2.imread(gray_p, cv2.IMREAD_GRAYSCALE)
        images_to_test["Ảnh màu RGB"] = cv2.imread(col_p, cv2.IMREAD_COLOR)

    # 3. Thực thi nén và đo đạc
    results = []
    hist_dict = {}
    rle_decoded_dict = {}
    huf_decoded_dict = {}
    orig_dict = {}
    
    for name, img in images_to_test.items():
        print(f"[+] Đang nén & kiểm tra toàn vẹn: {name} ({img.shape})...")
        res = process_single_image(name, img, out_dir=out_dir)
        results.append(res)
        hist_dict[name] = {"image": img, "entropy": res['entropy']}
        orig_dict[name] = img
        rle_decoded_dict[name] = res['rle_decoded']
        huf_decoded_dict[name] = res['huffman_decoded']
        
    # In bảng kết quả chi tiết
    print_comparison_tables(results)
    
    # 4. Chạy thêm quét toàn bộ ảnh thực tế trong images/ nếu có
    dataset_summary = []
    if os.path.isdir("images"):
        dataset_summary = run_benchmark_on_dataset("images", out_dir)

    # Persist only JSON-safe metrics; image arrays are used for plotting above.
    json_results = []
    metric_fields = (
        "original_size",
        "compressed_size",
        "compression_ratio",
        "space_saving_percent",
        "bpp",
        "enc_time_ms",
        "dec_time_ms",
    )
    for res in results:
        json_results.append({
            "name": res["name"],
            "shape": list(res["shape"]),
            "channels": res["channels"],
            "orig_size": res["orig_size"],
            "entropy": res["entropy"],
            "theoretical_max_cr": res["theoretical_max_cr"],
            "huffman_l_avg": res["huffman_l_avg"],
            "huffman_redundancy": res["huffman_redundancy"],
            "unique_symbols": res["unique_symbols"],
            "channel_entropies": res["channel_entropies"],
            "shannon_bound_ok": res["shannon_bound_ok"],
            "run_stats": res["run_stats"],
            "explanation": explain_result(res),
            "hybrid": {key: res["hybrid"][key] for key in metric_fields},
            "hybrid_integrity": {
                "is_identical": res["hybrid_integrity"]["is_identical"],
                "sha256_match": res["hybrid_integrity"]["sha256_match"],
            },
            "rle": {key: res["rle"][key] for key in metric_fields},
            "huffman": {key: res["huffman"][key] for key in metric_fields},
            "rle_integrity": {
                "is_identical": res["rle_integrity"]["is_identical"],
                "mse": res["rle_integrity"]["mse"],
                "psnr": "Infinity" if math.isinf(res["rle_integrity"]["psnr"]) else res["rle_integrity"]["psnr"],
                "sha256_match": res["rle_integrity"]["sha256_match"],
            },
            "huffman_integrity": {
                "is_identical": res["huffman_integrity"]["is_identical"],
                "mse": res["huffman_integrity"]["mse"],
                "psnr": "Infinity" if math.isinf(res["huffman_integrity"]["psnr"]) else res["huffman_integrity"]["psnr"],
                "sha256_match": res["huffman_integrity"]["sha256_match"],
            },
        })

    with open(os.path.join(out_dir, "compression_results.json"), "w", encoding="utf-8") as f:
        json.dump({"images": json_results, "dataset": dataset_summary}, f, indent=2, ensure_ascii=False)
        
    # 5. Vẽ và xuất biểu đồ
    print("\n[+] Đang tạo biểu đồ trực quan hóa...")
    # Chọn 3 đại diện cốt lõi (Nhị phân, Xám, Màu) để biểu đồ trực quan đẹp nhất
    core_keys = ["Ảnh nhị phân (Tài liệu)", "Ảnh xám", "Ảnh màu RGB"]
    core_hist = {k: hist_dict[k] for k in core_keys if k in hist_dict}
    core_results = [r for r in results if r['name'] in core_keys]
    core_orig = {k: orig_dict[k] for k in core_keys if k in orig_dict}
    core_rle_dec = {k: rle_decoded_dict[k] for k in core_keys if k in rle_decoded_dict}
    core_huf_dec = {k: huf_decoded_dict[k] for k in core_keys if k in huf_decoded_dict}
    
    plot_histograms_and_entropy(core_hist, output_path=os.path.join(out_dir, "histograms_and_entropy.png"))
    plot_compression_comparison(core_results, output_path=os.path.join(out_dir, "compression_comparison.png"))
    plot_visual_integrity(core_orig, core_rle_dec, core_huf_dec, output_path=os.path.join(out_dir, "visual_integrity.png"))
    
    # 6. Xuất báo cáo văn bản
    with open(os.path.join(out_dir, "compression_report.txt"), "w", encoding="utf-8") as f:
        f.write("=" * 90 + "\n")
        f.write("BÁO CÁO KỸ THUẬT: ĐỀ TÀI 30 - NÉN ẢNH KHÔNG MẤT DỮ LIỆU (RLE & HUFFMAN)\n")
        f.write("NHÓM 30: Trần Quốc Đạt (Trưởng Nhóm), Lê Văn Duy\n")
        f.write("=" * 90 + "\n\n")
        for res in results:
            f.write(f"[{res['name'].upper()}]:\n")
            f.write(f"  - Shape: {res['shape']}, Orig: {res['orig_size']} Bytes, Số mức: {res['unique_symbols']}\n")
            f.write(f"  - Entropy H(X): {res['entropy']:.4f} bits/symbol; theo kênh: "
                    + ", ".join(f"{k}={v:.4f}" for k, v in res['channel_entropies'].items()) + "\n")
            f.write(f"  - Huffman L_avg: {res['huffman_l_avg']:.4f} bit, dư thừa {res['huffman_redundancy']:.4f}, "
                    f"H <= L_avg < H+1: {res['shannon_bound_ok']}\n")
            rs = res['run_stats']
            f.write(f"  - Dải chạy: {rs['num_runs']} dải, độ dài TB {rs['avg_run_length']:.2f}, "
                    f"{rs['single_run_percent']:.1f}% dải dài 1\n")
            for label, key in [("RLE", "rle"), ("Huffman", "huffman"), ("RLE+Huffman", "hybrid")]:
                m = res[key]
                integ = res[f"{key}_integrity"]
                f.write(f"  - {label}: {m['compressed_size']} B, CR {m['compression_ratio']:.2f}x "
                        f"(Saving {m['space_saving_percent']:.1f}%, {m['bpp']:.3f} bpp) | "
                        f"Toàn vẹn: identical={integ['is_identical']}, MSE={integ['mse']}, "
                        f"PSNR={integ['psnr']}, SHA-256 match={integ['sha256_match']}\n")
            f.write("  - Giải thích:\n")
            for line in explain_result(res):
                f.write(f"      * {line}\n")
            f.write("\n")

    print(f"\n HOÀN THÀNH TOÀN BỘ QUÁ TRÌNH THỰC NGHIỆM!")
    print(f"Các file kết quả được lưu tại thư mục: '{out_dir}/'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Đề tài 30: Nén ảnh không mất dữ liệu bằng RLE và Huffman")
    parser.add_argument("--image", type=str, default=None, help="Đường dẫn file ảnh tùy chọn từ người dùng để thử nghiệm")
    parser.add_argument("--out-dir", type=str, default="output", help="Thư mục xuất báo cáo và biểu đồ")
    args = parser.parse_args()
    
    run_pipeline(custom_image_path=args.image, out_dir=args.out_dir)
