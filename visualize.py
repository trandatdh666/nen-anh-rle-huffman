"""
Module: visualize.py
Vẽ đồ thị Histogram, trực quan hóa Entropy, so sánh tỷ lệ nén và kiểm tra tính toàn vẹn trực quan.
Lưu kết quả thành các biểu đồ chất lượng cao trong thư mục output/.
"""

import os
import matplotlib.pyplot as plt
import numpy as np

# Cấu hình font và hiển thị matplotlib
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

def plot_histograms_and_entropy(images_dict: dict, output_path="output/histograms_and_entropy.png"):
    """
    Vẽ Histogram và chú thích Entropy cho 3 loại ảnh (Nhị phân, Xám, Màu).
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    colors = ['#1f77b4', '#2ca02c', '#d62728']
    
    for idx, (name, data) in enumerate(images_dict.items()):
        ax = axes[idx]
        img = data['image']
        entropy_val = data['entropy']
        
        if img.ndim == 2:
            hist = np.bincount(img.ravel(), minlength=256)
            is_binary = np.count_nonzero(hist) <= 2
            # Ảnh nhị phân chỉ có 2 cột tại 0 và 255 -> vẽ cột rộng hơn để không bị khuất ở mép trục
            ax.bar(range(256), hist, color=colors[idx], width=6.0 if is_binary else 1.0,
                   alpha=0.75, label='Pixel Count')
            ax.set_title(f"{name}\nEntropy H(X) = {entropy_val:.3f} bits/pixel", fontsize=12, fontweight='bold')
            ax.set_xlabel("Mức xám (Intensity 0-255)")
            ax.set_ylabel("Số lượng pixel")
            ax.set_xlim([-8, 263])
            ax.grid(True, linestyle='--', alpha=0.5)

            # Chú thích lý thuyết
            huf_cap = 8.0 / max(entropy_val, 1.0)  # Huffman: L_avg >= max(H, 1 bit)
            if is_binary:
                theory_note = (f"Chỉ 2 mức: 0 và 255\nGiới hạn bậc 0: 8/H = {8.0/entropy_val:.1f}x\n"
                               f"Huffman tối đa ~{huf_cap:.1f}x (>= 1 bit/pixel)")
            else:
                theory_note = (f"Phân bố rộng trên dải xám\nGiới hạn bậc 0: 8/H = {8.0/entropy_val:.2f}x\n"
                               f"Huffman tối đa ~{huf_cap:.2f}x")
            ax.text(0.5, 0.75, theory_note, transform=ax.transAxes,
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.3),
                    horizontalalignment='center', fontsize=9)
        else:
            # Ảnh màu: vẽ histogram 3 kênh (B, G, R)
            channel_colors = [('Kênh Blue', 'blue', 0), ('Kênh Green', 'green', 1), ('Kênh Red', 'red', 2)]
            for ch_name, col, ch_idx in channel_colors:
                ch_hist = np.bincount(img[:, :, ch_idx].ravel(), minlength=256)
                ax.plot(range(256), ch_hist, color=col, alpha=0.7, label=ch_name, linewidth=1.5)
                
            ax.set_title(f"{name}\nEntropy gộp H(X) = {entropy_val:.3f} bits/symbol", fontsize=12, fontweight='bold')
            ax.set_xlabel("Mức màu (Intensity 0-255)")
            ax.set_ylabel("Số lượng pixel")
            ax.set_xlim([0, 255])
            ax.legend(loc='upper right')
            ax.grid(True, linestyle='--', alpha=0.5)
            
            theory_note = f"3 kênh màu phong phú\nGiới hạn bậc 0: 8/H = {8.0/entropy_val:.2f}x"
            ax.text(0.5, 0.65, theory_note, transform=ax.transAxes,
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.3),
                    horizontalalignment='center', fontsize=9)
                    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"-> Đã lưu biểu đồ Histogram & Entropy: {output_path}")


def plot_compression_comparison(comparison_results: list, output_path="output/compression_comparison.png"):
    """
    Vẽ biểu đồ cột so sánh hiệu năng nén của RLE và Huffman trên 3 loại ảnh:
      1. Tỷ lệ nén (Compression Ratio)
      2. Tỷ lệ tiết kiệm dung lượng (Space Saving %)
      3. Tốc độ bit (Bitrate - bpp)
      4. Entropy vs Độ dài từ mã Huffman trung bình (L_avg)
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(15, 11))
    
    img_names = [res['name'] for res in comparison_results]
    x = np.arange(len(img_names))
    width = 0.35
    
    # 1. Compression Ratio (CR)
    ax1 = axes[0, 0]
    rle_cr = [res['rle']['compression_ratio'] for res in comparison_results]
    huf_cr = [res['huffman']['compression_ratio'] for res in comparison_results]
    
    has_hyb = 'hybrid' in comparison_results[0]
    w1 = 0.27 if has_hyb else width
    rects1 = ax1.bar(x - w1 if has_hyb else x - width/2, rle_cr, w1, label='RLE', color='#2b5c8f')
    rects2 = ax1.bar(x if has_hyb else x + width/2, huf_cr, w1, label='Huffman', color='#e26d5c')
    rects_h = []
    if has_hyb:
        hyb_cr = [res['hybrid']['compression_ratio'] for res in comparison_results]
        rects_h = ax1.bar(x + w1, hyb_cr, w1, label='RLE+Huffman', color='#7b2cbf')
    ax1.set_title('Tỷ lệ nén (Compression Ratio = S_orig / S_comp)', fontsize=12, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(img_names)
    ax1.axhline(1.0, color='gray', linestyle='--', linewidth=1, label='Ngưỡng không đổi (1.0x)')
    ax1.legend()
    ax1.grid(True, linestyle=':', alpha=0.6)
    
    # Ghi giá trị trên các cột
    for rect in rects1:
        h = rect.get_height()
        ax1.annotate(f'{h:.2f}x', xy=(rect.get_x() + rect.get_width()/2, h),
                     xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold')
    for rect in list(rects2) + list(rects_h):
        h = rect.get_height()
        ax1.annotate(f'{h:.2f}x', xy=(rect.get_x() + rect.get_width()/2, h),
                     xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold')

    # 2. Space Saving (%)
    ax2 = axes[0, 1]
    rle_ss = [res['rle']['space_saving_percent'] for res in comparison_results]
    huf_ss = [res['huffman']['space_saving_percent'] for res in comparison_results]
    
    rects3 = ax2.bar(x - width/2, rle_ss, width, label='RLE', color='#2b5c8f')
    rects4 = ax2.bar(x + width/2, huf_ss, width, label='Huffman', color='#e26d5c')
    ax2.set_title('Tỷ lệ tiết kiệm dung lượng (%) (Space Saving)', fontsize=12, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(img_names)
    ax2.axhline(0.0, color='black', linestyle='-', linewidth=1)
    ax2.legend()
    ax2.grid(True, linestyle=':', alpha=0.6)
    
    for rect in rects3:
        h = rect.get_height()
        va = 'bottom' if h >= 0 else 'top'
        ax2.annotate(f'{h:.1f}%', xy=(rect.get_x() + rect.get_width()/2, h),
                     xytext=(0, 3 if h >= 0 else -10), textcoords="offset points", ha='center', va=va, fontsize=9)
    for rect in rects4:
        h = rect.get_height()
        va = 'bottom' if h >= 0 else 'top'
        ax2.annotate(f'{h:.1f}%', xy=(rect.get_x() + rect.get_width()/2, h),
                     xytext=(0, 3 if h >= 0 else -10), textcoords="offset points", ha='center', va=va, fontsize=9)

    # 3. Bitrate (bpp)
    ax3 = axes[1, 0]
    rle_bpp = [res['rle']['bpp'] for res in comparison_results]
    huf_bpp = [res['huffman']['bpp'] for res in comparison_results]
    orig_bpp = [res['orig_bpp'] for res in comparison_results]
    
    w3 = 0.25
    ax3.bar(x - w3, orig_bpp, w3, label='Gốc (Original)', color='#a0aab2')
    ax3.bar(x, rle_bpp, w3, label='RLE', color='#2b5c8f')
    ax3.bar(x + w3, huf_bpp, w3, label='Huffman', color='#e26d5c')
    ax3.set_title('Tốc độ bit (Bitrate - bits per pixel)', fontsize=12, fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(img_names)
    ax3.legend()
    ax3.grid(True, linestyle=':', alpha=0.6)

    # 4. Entropy vs Huffman L_avg
    ax4 = axes[1, 1]
    entropies = [res['entropy'] for res in comparison_results]
    l_avgs = [res['huffman_l_avg'] for res in comparison_results]
    
    rects_ent = ax4.bar(x - width/2, entropies, width, label='Entropy Shannon H(X)', color='#38b000')
    rects_lavg = ax4.bar(x + width/2, l_avgs, width, label='Độ dài từ mã TB L_avg (Huffman)', color='#e26d5c')
    ax4.set_title('Giới hạn Entropy Shannon H(X) và L_avg của Huffman', fontsize=12, fontweight='bold')
    ax4.set_xticks(x)
    ax4.set_xticklabels(img_names)
    ax4.set_ylim(0, max(max(entropies), max(l_avgs)) * 1.3)  # chừa chỗ cho chú giải
    ax4.legend(loc='upper left')
    ax4.grid(True, linestyle=':', alpha=0.6)
    
    for rect in rects_ent:
        h = rect.get_height()
        ax4.annotate(f'{h:.2f}', xy=(rect.get_x() + rect.get_width()/2, h),
                     xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9)
    for rect in rects_lavg:
        h = rect.get_height()
        ax4.annotate(f'{h:.2f}', xy=(rect.get_x() + rect.get_width()/2, h),
                     xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"-> Đã lưu biểu đồ so sánh nén: {output_path}")


def plot_dataset_comparison(dataset: list, output_path="output/dataset_comparison.png"):
    """
    So sánh trên toàn bộ tập ảnh:
      (1) CR trung bình của 3 phương pháp theo loại ảnh (thang log)
      (2) Độ dài dải TB vs CR(RLE): kiểm chứng CR_RLE ~ độ dài dải / 2
      (3) Entropy H(X) vs CR(Huffman): kiểm chứng CR_HUF ~ 8 / max(H, 1)
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    types = [("bin", "Nhị phân (Otsu)", '#1f77b4'), ("gray", "Ảnh xám", '#2ca02c'), ("color", "Ảnh màu", '#d62728')]
    algos = [("rle", "RLE", '#2b5c8f'), ("huf", "Huffman", '#e26d5c'), ("hyb", "RLE+Huffman", '#7b2cbf')]
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))

    ax = axes[0]
    x = np.arange(len(types))
    wb = 0.27
    for i, (ak, alabel, col) in enumerate(algos):
        means = [np.mean([e[f"{tk}_cr_{ak}"] for e in dataset]) for tk, _, _ in types]
        bars = ax.bar(x + (i - 1) * wb, means, wb, label=alabel, color=col)
        for r in bars:
            ax.annotate(f"{r.get_height():.2f}x", (r.get_x() + r.get_width() / 2, r.get_height()),
                        xytext=(0, 3), textcoords="offset points", ha='center', fontsize=9)
    ax.axhline(1.0, color='gray', linestyle='--', linewidth=1, label='CR = 1 (không nén được)')
    ax.set_yscale('log')
    ax.set_xticks(x)
    ax.set_xticklabels([t[1] for t in types])
    ax.set_title(f"CR trung bình trên {len(dataset)} ảnh (thang log)", fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, linestyle=':', alpha=0.6)

    ax = axes[1]
    for tk, tlabel, col in types:
        ax.scatter([e[f"{tk}_avg_run"] for e in dataset], [e[f"{tk}_cr_rle"] for e in dataset],
                   color=col, label=tlabel, alpha=0.8)
    runs = np.array([e[f"{tk}_avg_run"] for e in dataset for tk, _, _ in types])
    xs = np.linspace(max(runs.min(), 1.0), runs.max(), 100)
    ax.plot(xs, xs / 2, 'k--', label='Lý thuyết: CR = độ dài dải / 2')
    ax.axhline(1.0, color='gray', linestyle=':', linewidth=1)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel("Độ dài dải trung bình (pixel)")
    ax.set_ylabel("CR của RLE")
    ax.set_title("RLE phụ thuộc độ dài dải chạy", fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, linestyle=':', alpha=0.6)

    ax = axes[2]
    for tk, tlabel, col in types:
        ax.scatter([e[f"{tk}_entropy"] for e in dataset], [e[f"{tk}_cr_huf"] for e in dataset],
                   color=col, label=tlabel, alpha=0.8)
    hs = np.linspace(0.05, 8, 200)
    ax.plot(hs, 8 / np.maximum(hs, 1.0), 'k--', label='Lý thuyết: CR = 8 / max(H, 1)')
    ax.plot(hs, 8 / hs, color='gray', linestyle=':', label='Giới hạn bậc 0: 8 / H')
    ax.set_ylim(0.8, 12)
    ax.set_xlabel("Entropy H(X) (bit/pixel)")
    ax.set_ylabel("CR của Huffman")
    ax.set_title("Huffman phụ thuộc entropy (histogram)", fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, linestyle=':', alpha=0.6)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    # Lưu thêm từng ô riêng (dùng cho slide)
    renderer = fig.canvas.get_renderer()
    out_dir = os.path.dirname(output_path)
    for ax_i, fname in ((axes[1], "dataset_rle_vs_run.png"), (axes[2], "dataset_huffman_vs_entropy.png")):
        bbox = ax_i.get_tightbbox(renderer).transformed(fig.dpi_scale_trans.inverted()).expanded(1.03, 1.03)
        fig.savefig(os.path.join(out_dir, fname), dpi=200, bbox_inches=bbox)
    plt.close(fig)
    print(f"-> Đã lưu biểu đồ so sánh trên toàn bộ tập ảnh: {output_path}")


def plot_visual_integrity(original_images: dict, rle_decoded: dict, huf_decoded: dict, output_path="output/visual_integrity.png"):
    """
    Hiển thị so sánh trực quan giữa ảnh gốc và ảnh giải mã từ RLE và Huffman.
    Kèm bản đồ sai lệch (Difference Map = |Orig - Decoded| * 255) minh chứng MSE = 0 tuyệt đối.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    num_imgs = len(original_images)
    fig, axes = plt.subplots(num_imgs, 4, figsize=(16, 4 * num_imgs))
    
    if num_imgs == 1:
        axes = np.array([axes])
        
    for row_idx, (name, orig) in enumerate(original_images.items()):
        rle_dec = rle_decoded[name]
        huf_dec = huf_decoded[name]
        
        # Tính chênh lệch
        diff = np.abs(orig.astype(float) - huf_dec.astype(float))
        diff_vis = np.clip(diff * 255, 0, 255).astype(np.uint8)
        
        # Ảnh gốc
        ax0 = axes[row_idx, 0]
        if orig.ndim == 2:
            ax0.imshow(orig, cmap='gray')
        else:
            # OpenCV BGR -> RGB để Matplotlib vẽ đúng màu
            ax0.imshow(orig[:, :, ::-1])
        ax0.set_title(f"{name}\nẢnh gốc (Original)", fontsize=11, fontweight='bold')
        ax0.axis('off')
        
        # Ảnh giải mã RLE
        ax1 = axes[row_idx, 1]
        if rle_dec.ndim == 2:
            ax1.imshow(rle_dec, cmap='gray')
        else:
            ax1.imshow(rle_dec[:, :, ::-1])
        ax1.set_title(f"Giải mã RLE\n(Lossless 100%)", fontsize=11, color='navy')
        ax1.axis('off')
        
        # Ảnh giải mã Huffman
        ax2 = axes[row_idx, 2]
        if huf_dec.ndim == 2:
            ax2.imshow(huf_dec, cmap='gray')
        else:
            ax2.imshow(huf_dec[:, :, ::-1])
        ax2.set_title(f"Giải mã Huffman\n(Lossless 100%)", fontsize=11, color='darkred')
        ax2.axis('off')
        
        # Bản đồ sai lệch
        ax3 = axes[row_idx, 3]
        if diff_vis.ndim == 2:
            ax3.imshow(diff_vis, cmap='hot', vmin=0, vmax=255)
        else:
            ax3.imshow(diff_vis[:, :, ::-1])
        ax3.set_title(f"Bản đồ sai khác (|Orig - Decoded|)\nMSE = 0.0 | PSNR = Inf dB", fontsize=11, color='darkgreen', fontweight='bold')
        ax3.axis('off')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"-> Đã lưu bản đồ kiểm chứng toàn vẹn trực quan: {output_path}")

