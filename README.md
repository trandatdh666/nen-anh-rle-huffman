# BÁO CÁO BÀI TẬP LỚN: ĐỀ TÀI 30
# NÉN ẢNH KHÔNG MẤT DỮ LIỆU BẰNG RLE VÀ HUFFMAN

## 1. Giới thiệu tổng quan
Dự án cài đặt trọn vẹn và so sánh hai giải thuật nén ảnh không mất dữ liệu (lossless compression) kinh điển trong xử lý ảnh và lý thuyết thông tin:
- **Run-Length Encoding (RLE)**: Khai thác tính dư thừa không gian (spatial redundancy) của các pixel liền kề có cùng giá trị.
- **Huffman Coding**: Khai thác tính dư thừa thống kê (statistical redundancy / symbol frequency) dựa trên entropy Shannon để xây dựng bộ mã tiền tố tối ưu (prefix-free variable length code).

Chương trình được xây dựng hoàn chỉnh bằng Python (sử dụng thư viện `opencv-python`, `numpy`, `matplotlib`) với:
1. Đóng gói file nhị phân chuẩn định dạng (`.rle` và `.huf`), có header chứa kích thước, số kênh và bảng tần số giúp giải mã độc lập 100%.
2. Tính toán **Histogram** và **Shannon Entropy** $H(X)$ để giải thích giới hạn lý thuyết nén.
3. So sánh thực nghiệm trên **3 loại ảnh**:
   - **Ảnh nhị phân (Binary Image)**
   - **Ảnh xám (Grayscale Image)**
   - **Ảnh màu RGB (Color Image)**
4. Đánh giá tính toàn vẹn tuyệt đối (Lossless Verification): Kiểm tra từng pixel, sai lệch tuyệt đối cực đại ($MaxDiff = 0$), $MSE = 0$, $PSNR = \infty$, và khớp mã băm mật mã $SHA-256$.

---

## 2. Cấu trúc thư mục dự án
```text
BTL2/
├── rle.py                 # Cài đặt mã hóa & giải mã RLE nhị phân
├── huffman.py             # Cài đặt mã hóa & giải mã Huffman bit-level
├── hybrid.py              # (Mở rộng) Nén kết hợp RLE -> Huffman
├── metrics.py             # Histogram, Entropy, thống kê dải chạy, định lý Shannon, MSE, PSNR, SHA-256
├── dataset_generator.py   # Bộ sinh ảnh tổng hợp (Nhị phân, Xám, Màu)
├── visualize.py           # Vẽ biểu đồ Histogram, So sánh hiệu năng, Bản đồ sai lệch
├── main.py                # Chương trình chính thực thi toàn bộ pipeline
├── test_codecs.py         # Kiểm thử tự động (round-trip lossless, entropy, Shannon, prefix-free)
├── images/                # Ảnh đầu vào: 7 ảnh phong cảnh thực tế (*.png)
│   └── synthetic/         # Ảnh tổng hợp: binary_document.png, grayscale_sample.png, color_sample.png
└── output/                # Thư mục lưu trữ kết quả đầu ra
    ├── compressed_files/  # Các file nén nhị phân thực tế (*.rle, *.huf, *.rlh)
    ├── figures/           # Sơ đồ & biểu đồ xuất từ slide (RLE, cây Huffman, quy trình kiểm tra...) để chèn báo cáo
    ├── histograms_and_entropy.png
    ├── compression_comparison.png
    ├── visual_integrity.png
    ├── compression_report.txt
    └── compression_results.json
```

---

## 3. Cơ sở lý thuyết

### 3.1. Thuật toán RLE (Run-Length Encoding)
- **Nguyên lý**: Biểu diễn các chuỗi pixel liên tiếp có cùng giá trị bằng các cặp $(L, V)$ trong đó $L$ là độ dài dải (Run length) và $V$ là giá trị pixel (Pixel value).
- **Đóng gói nhị phân**: Mỗi cặp $(L, V)$ được lưu dưới dạng 2 byte `uint8` ($1 \le L \le 255$). Nếu dải dài hơn 255, tách thành nhiều cặp.
- **Khả năng nén**:
  - Tối ưu khi ảnh có các vùng đồng nhất lớn (như ảnh nhị phân, văn bản đen trắng, mặt nạ phân đoạn).
  - Kém hiệu quả đối với ảnh tự nhiên (ảnh xám, ảnh màu) do các pixel liền kề luôn có sự dao động nhỏ về cường độ sáng $\rightarrow L = 1 \Rightarrow$ kích thước tăng gấp đôi (Data Expansion).

### 3.2. Thuật toán Huffman Coding
- **Nguyên lý**: 
  1. Thống kê tần số xuất hiện của từng giá trị byte (0–255).
  2. Dùng cấu trúc hàng đợi ưu tiên (min-heap) để ghép 2 nút có tần số nhỏ nhất cho đến khi tạo thành cây nhị phân (Huffman Tree).
  3. Duyệt cây từ gốc đến lá để gán từ mã: nhánh trái gán '0', nhánh phải gán '1'. Ký hiệu xuất hiện nhiều có từ mã ngắn, ký hiệu ít xuất hiện có từ mã dài.
  4. Đóng gói các bit thành chuỗi byte nhị phân kèm header lưu bảng tần số để giải mã.
- **Độ dài từ mã trung bình ($L_{avg}$)**:
  $$L_{avg} = \sum_{k=0}^{255} p_k \cdot l_k \quad (\text{bits/symbol})$$
  trong đó $p_k$ là xác suất xuất hiện của mức xám $k$, $l_k$ là độ dài từ mã của mức xám $k$.

### 3.3. Định lý Shannon và Entropy
- **Shannon Entropy**:
  $$H(X) = - \sum_{k=0}^{255} p_k \log_2(p_k) \quad (\text{với } p_k > 0)$$
- **Định lý mã hóa nguồn của Shannon**:
  $$H(X) \le L_{avg} < H(X) + 1$$
  Entropy $H(X)$ đại diện cho **cận dưới lý thuyết** về số bit trung bình tối thiểu trên mỗi pixel để mã hóa không mất dữ liệu.
- **Độ dư thừa (Redundancy)**:
  $$R = L_{avg} - H(X) \ge 0$$
- **Giới hạn nén bậc 0**:
  $$CR_{0} = \frac{8}{H(X)}$$
  Đây là giới hạn khi **mã hóa từng pixel độc lập** (chỉ dựa vào histogram). Lưu ý:
  - Huffman gán mỗi ký hiệu ít nhất 1 bit nên $L_{avg} \ge \max(H, 1)$, tức Huffman không vượt quá $8\times$ trên ảnh 8-bit. Với ảnh nhị phân ($H < 1$), Huffman bị chặn ở $8\times$ dù $8/H > 8$.
  - RLE **có thể vượt** $8/H$ vì nó khai thác tương quan giữa các pixel liền kề, một thông tin mà histogram (entropy bậc 0) không thể hiện.

### 3.4. Thống kê dải chạy (giải thích khả năng nén của RLE)
Entropy chỉ giải thích được Huffman. Để giải thích RLE, chương trình đếm các dải liên tiếp cùng giá trị (theo đúng thứ tự quét của RLE):
$$\bar{L}_{run} = \frac{N_{pixel}}{N_{run}}, \qquad CR_{RLE} \approx \frac{N_{pixel}}{2 \cdot N_{run}} = \frac{\bar{L}_{run}}{2}$$
Mỗi dải tốn 2 byte, nên RLE chỉ có lợi khi độ dài dải trung bình $\bar{L}_{run} > 2$.

### 3.5. Mở rộng: kết hợp RLE → Huffman
Chuỗi byte sau RLE vẫn còn dư thừa thống kê (ví dụ count = 255 và value ∈ {0, 255} lặp lại rất nhiều), nên tiếp tục nén bằng Huffman. Đây là nguyên lý của chuẩn fax CCITT Group 3 (Modified Huffman).

---

## 4. Các độ đo đánh giá (Evaluation Metrics)
1. **Tỷ lệ nén (Compression Ratio - CR)**:
   $$CR = \frac{\text{Dung lượng gốc (Bytes)}}{\text{Dung lượng sau nén (Bytes)}}$$
   - $CR > 1$: Nén hiệu quả (kích thước giảm).
   - $CR < 1$: Phình dữ liệu (Data Expansion).
2. **Tỷ lệ tiết kiệm dung lượng (Space Saving %)**:
   $$\text{Saving} = \left(1 - \frac{\text{Dung lượng sau nén}}{\text{Dung lượng gốc}}\right) \times 100\%$$
3. **Tốc độ bit (Bitrate - bpp)**:
   $$\text{bpp} = \frac{\text{Dung lượng sau nén (Bytes)} \times 8}{\text{Chiều cao } \times \text{Chiều rộng}} \quad (\text{bits/pixel})$$
4. **Kiểm tra tính toàn vẹn (Lossless Verification)**:
   - **MSE (Mean Squared Error)**:
     $$MSE = \frac{1}{H \times W \times C} \sum_{x,y,c} \left(I_{orig}(x,y,c) - I_{decomp}(x,y,c)\right)^2$$
     Yêu cầu: $MSE = 0.0$.
   - **PSNR (Peak Signal-to-Noise Ratio)**:
     $$PSNR = 10 \log_{10}\left(\frac{255^2}{MSE}\right) = \infty \text{ dB}$$
   - **SHA-256 Hash**: So sánh mã băm của mảng pixel gốc và mảng pixel giải mã.

---

## 5. Hướng dẫn cài đặt và sử dụng

### 5.1. Cài đặt thư viện phụ thuộc
Chương trình yêu cầu Python 3.8+ và các thư viện trong `requirements.txt`:
```bash
python -m pip install -r requirements.txt
```

### 5.2. Chạy thử nghiệm mặc định
Chạy thực nghiệm trên ảnh tài liệu tổng hợp và các ảnh trong `images/`:
```bash
python -X utf8 main.py
```
Mỗi lần chạy sẽ cập nhật các biểu đồ, báo cáo và số liệu đo trong thư mục `output/`.
Các script tạo tài liệu sử dụng số liệu ở `output/compression_results.json`, vì vậy hãy chạy
`main.py` trước khi tạo slide hoặc báo cáo:
```bash
npm install && node build_slides.js     # slide PowerPoint (BaoCao/)
python -X utf8 create_word_report.py    # báo cáo Word
```

### 5.3. Chạy kiểm thử tự động
```bash
python -X utf8 -m unittest test_codecs -v
```

### 5.4. Chạy thử nghiệm trên ảnh tùy chọn của người dùng
Người dùng có thể truyền vào bất kỳ file ảnh nào:
```bash
python main.py --image path/to/your_image.png
```

---

## 6. Phân tích kết quả thực nghiệm

| Loại ảnh | Kích thước | Số mức | $H(X)$ | $L_{avg}$ | Độ dài dải TB | CR (RLE) | CR (HUF) | CR (RLE+HUF) | Toàn vẹn |
|---|---|---|---|---|---|---|---|---|---|
| **Nhị phân (tài liệu)** | 512x512 | 2 | 0.7245 | 1.0000 | 89.13 | **38.09x** | 7.99x | **64.46x** | MSE=0, SHA-256 khớp |
| **Nhị phân (Otsu)** | 490x735 | 2 | 0.8849 | 1.0000 | 9.81 | 4.88x | 7.99x | **11.24x** | MSE=0, SHA-256 khớp |
| **Ảnh xám thực tế** | 490x735 | 253 | 7.4222 | 7.4574 | 1.16 | 0.58x (phình) | **1.07x** | 0.93x | MSE=0, SHA-256 khớp |
| **Ảnh màu thực tế** | 490x735x3 | 256 | 7.5624 | 7.5859 | 1.15 | 0.58x (phình) | **1.05x** | 0.91x | MSE=0, SHA-256 khớp |

### 6.1. Tổng kết trên toàn bộ 28 ảnh thực tế (`images/*.png`)
Mỗi ảnh được tách thành 3 phiên bản (nhị phân Otsu, xám, màu), nén bằng 3 phương pháp và **giải mã lại để kiểm tra**: 84/84 phiên bản × 3 phương pháp đều khớp SHA-256.

| Loại ảnh | H(X) TB | CR RLE (TB / trung vị) | CR Huffman (TB / trung vị) | CR RLE+Huffman (TB / trung vị) | Thắng nhiều nhất |
|---|---|---|---|---|---|
| Nhị phân (Otsu) | 0.882 | 20.97x / 14.76x | 7.99x / 7.99x | **38.25x / 25.35x** | RLE+Huffman 28/28 |
| Ảnh xám | 7.120 | 1.38x / 0.69x | 1.27x / **1.06x** | 2.05x / 1.06x | Huffman 14, RLE+Huffman 14 |
| Ảnh màu | 7.219 | 1.35x / 0.67x | 1.26x / **1.05x** | 2.10x / 1.04x | Huffman 14, RLE+Huffman 14 |

Trung bình của ảnh xám/màu bị kéo lên bởi `trang_khuyet_dem_den.png` (gần như toàn đen, H = 0.54); nên dùng **trung vị** để đại diện cho ảnh điển hình. Biểu đồ `output/dataset_comparison.png` cho thấy CR(RLE) ≈ độ dài dải TB / 2 và CR(Huffman) ≈ 8 / max(H, 1) trên toàn bộ tập ảnh.

Lưu ý: 21 ảnh mới vốn là JPEG, đã được chuyển sang PNG; phép chuyển này không làm mất dữ liệu (đã kiểm tra trùng khớp từng pixel), nhưng nội dung ảnh vẫn mang nhiễu khối của JPEG.

Mọi trường hợp đều thỏa $H \le L_{avg} < H + 1$. Ảnh giải mã được tạo bằng cách **đọc lại file nén từ đĩa**, không dùng dữ liệu trong RAM.

### Nhận xét & Kết luận:
1. **Đối với ảnh nhị phân**:
   - RLE đạt hiệu năng nén phi thường ($38.09\times$, tiết kiệm khoảng $97.4\%$ dung lượng) trên ảnh tài liệu do có những dải pixel liên tiếp hàng trăm pixel trắng/đen.
   - Huffman đạt $7.99\times$ (tiết kiệm $87.5\%$), gần như tiệm cận mức tối đa lý thuyết ($8/1 = 8\times$) khi biểu diễn mỗi pixel bằng đúng 1 bit.
2. **Đối với ảnh xám và ảnh màu**:
   - Trên ảnh xám và màu thực tế trong lần chạy hiện tại, RLE bị phình dữ liệu ($CR \approx 0.58\times$), còn Huffman đạt lần lượt $1.07\times$ và $1.05\times$.
   - Huffman tận dụng sự chênh lệch phân bố xác suất; độ dài từ mã trung bình gần entropy Shannon. Kết quả mới nhất được lưu trong `output/compression_results.json`.
3. **Tính toàn vẹn**:
   - Tất cả các trường hợp đều có $MSE = 0.0$, $PSNR = \infty$ dB và mã hash SHA-256 trùng khớp $100\%$, chứng minh tính không mất dữ liệu tuyệt đối.

