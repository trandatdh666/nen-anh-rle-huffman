/**
 * build_slides.js — Tạo slide thuyết trình Đề tài 30 (Nhóm 30) từ số liệu thực nghiệm.
 *
 * Số liệu đọc trực tiếp từ output/compression_results.json và output/dataset_summary.json,
 * nên hãy chạy `python -X utf8 main.py` trước.
 *
 * Cài đặt & chạy:
 *   npm install pptxgenjs@3.12.0
 *   node build_slides.js
 */
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const OUT = process.argv[2] || path.join("BaoCao", "Đề tài 30 - Nhóm 30 - Nén ảnh RLE và Huffman.pptx");
const ASSET_DIR = process.argv[3] || "output";

// ---------------------------------------------------------------- dữ liệu
const results = JSON.parse(fs.readFileSync("output/compression_results.json", "utf8"));
const dataset = JSON.parse(fs.readFileSync("output/dataset_summary.json", "utf8"));
const IMG = Object.fromEntries(results.images.map((r) => [r.name, r]));
const REP = ["Ảnh nhị phân (Tài liệu)", "Ảnh nhị phân (Otsu)", "Ảnh xám", "Ảnh màu RGB"].map((n) => IMG[n]);
const OV = dataset.overview;
const N_DATA = dataset.images.length;
const n2 = (v) => v.toFixed(2);
const cr = (v) => `${v.toFixed(2)}x`;
const totalChecks = REP.length * 3 + N_DATA * 3 * 3;
const totalOk =
  REP.reduce((s, r) => s + ["rle", "huffman", "hybrid"].filter((k) => r[`${k}_integrity`].sha256_match).length, 0) +
  ["bin", "gray", "color"].reduce((s, k) => s + OV[k].lossless_count * 3, 0);

// ---------------------------------------------------------------- theme
const THEME = {
  name: "Nen anh RLE Huffman",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1B1F27", lt1: "FFFFFF", dk2: "14213D", lt2: "F1F4F8",
    accent1: "2B5C8F", // RLE
    accent2: "E26D5C", // Huffman
    accent3: "7B2CBF", // RLE + Huffman
    accent4: "2A9D8F", // đúng / toàn vẹn
    accent5: "E9A23B", // nhấn
    accent6: "5B6573", // chữ phụ
    hlink: "2B5C8F", folHlink: "7B2CBF",
  },
};
const HEX = THEME.colors;
const SERIES = [HEX.accent1, HEX.accent2, HEX.accent3];

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333" x 7.5"
pres.title = "Nén ảnh không mất dữ liệu bằng RLE và Huffman";
pres.author = "Nhóm 30";
pres.subject = "Đề tài 30";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
// Dùng mã màu cố định (không phụ thuộc theme) để chạy `node build_slides.js` ở đâu cũng ra đúng màu
const C = {
  text1: HEX.dk1, text2: HEX.dk2, background1: HEX.lt1, background2: HEX.lt2,
  accent1: HEX.accent1, accent2: HEX.accent2, accent3: HEX.accent3,
  accent4: HEX.accent4, accent5: HEX.accent5, accent6: HEX.accent6,
};
const W = 13.333;

// ---------------------------------------------------------------- layouts
const FOOTER = "Nhóm 30  ·  Đề tài 30  ·  Nén ảnh không mất dữ liệu bằng RLE và Huffman";
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.85,
        fontSize: 32, bold: true, color: C.text2, valign: "middle", align: "left", margin: 0 }, text: "" } },
    { text: { text: FOOTER, options: { x: 0.6, y: 7.0, w: 9, h: 0.3, fontSize: 10, color: C.accent6, margin: 0 } } },
  ],
  slideNumber: { x: 12.2, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: C.accent6, align: "right" },
});
pres.defineSlideMaster({
  title: "DARK",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.3, w: 11.7, h: 1.6,
        fontSize: 44, bold: true, color: C.background1, valign: "top", align: "left", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 4.1, w: 11.7, h: 1.2,
        fontSize: 20, color: "CADCFC", valign: "top", align: "left", margin: 0 }, text: "" } },
  ],
});

// ---------------------------------------------------------------- helpers
function txt(slide, text, o) {
  slide.addText(text, { isTextBox: true, margin: 0, fontSize: 16, color: C.text1, valign: "top", ...o });
}
function card(slide, x, y, w, h, fill, name) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, rectRadius: 0.12, fill: { color: fill || C.background2 }, line: { type: "none" }, objectName: name,
  });
}
function badge(slide, x, y, label, fill, size = 0.55) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: size, h: size, fill: { color: fill }, line: { type: "none" } });
  slide.addText(String(label), { isTextBox: true, x, y, w: size, h: size, align: "center", valign: "middle",
    fontSize: size > 0.5 ? 18 : 13, bold: true, color: C.background1, margin: 0 });
}
function bullets(slide, items, o) {
  slide.addText(
    items.map((t, i) => ({ text: t, options: { bullet: { indent: 16 }, breakLine: i < items.length - 1 } })),
    { isTextBox: true, margin: 0, fontSize: 16, color: C.text1, valign: "top", paraSpaceAfter: 8, ...o }
  );
}
// Dải pixel minh hoạ (motif của deck): values = mảng 0/255
function pixelStrip(slide, x, y, values, size = 0.42, dark = C.text2, light = C.background1, border = "C9D1DC") {
  values.forEach((v, i) => {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x + i * size, y, w: size, h: size, fill: { color: v === 0 ? dark : light },
      line: { color: border, width: 0.75 },
    });
  });
}
function content(title, section) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  return s;
}
const axisFont = { catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt",
  legendFontFace: "+mn-lt", catAxisLabelFontSize: 13, valAxisLabelFontSize: 11, dataLabelFontSize: 11,
  legendFontSize: 13, catAxisLabelColor: "1B1F27", valAxisLabelColor: "5B6573", dataLabelColor: "1B1F27" };
const tableHead = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.dk2 }, align: "center", valign: "middle" } });
const cell = (t, o = {}) => ({ text: String(t), options: { align: "center", valign: "middle", ...o } });

// ================================================================ 1. Bìa
pres.addSection({ title: "Mở đầu" });
{
  const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Mở đầu" });
  txt(s, "BÀI TẬP LỚN  ·  ĐỀ TÀI 30", { x: 0.8, y: 1.55, w: 8, h: 0.4, fontSize: 16, bold: true, color: C.accent5, charSpacing: 2 });
  s.addText("Nén ảnh không mất dữ liệu bằng RLE và Huffman", { placeholder: "title" });
  s.addText("Nhóm 30  —  Trần Quốc Đạt (Trưởng nhóm)  ·  Lê Văn Duy", { placeholder: "body" });
  // motif: dải pixel và các cặp RLE tương ứng
  const px = [255, 255, 255, 255, 255, 0, 0, 0, 255, 255, 255, 255];
  pixelStrip(s, 0.8, 5.55, px, 0.4, "0B1426", "FFFFFF", "3A4A6B");
  txt(s, "→   (5, 255)  (3, 0)  (4, 255)      12 byte → 6 byte", { x: 5.85, y: 5.6, w: 7, h: 0.35, fontSize: 16, color: "CADCFC", fontFace: "Courier New" });
  s.addNotes("Giới thiệu đề tài 30: nén ảnh không mất dữ liệu bằng RLE và Huffman. Dải ô vuông minh hoạ ý tưởng RLE: 12 pixel được thay bằng 3 cặp (độ dài, giá trị).");
}

// ================================================================ 2. Phân công
{
  const s = content("Thành viên và phân công", "Mở đầu");
  const people = [
    { init: "Đ", name: "Trần Quốc Đạt", role: "Trưởng nhóm", fill: C.accent1, items: [
      "Quản lý tiến độ, tích hợp toàn bộ chương trình",
      "Cài đặt RLE và Planar RLE cho ảnh màu",
      "Mô-đun histogram, entropy, giới hạn lý thuyết (metrics.py)",
      "Báo cáo: Mở đầu, Chương 1 và Chương 2" ] },
    { init: "D", name: "Lê Văn Duy", role: "Thành viên", fill: C.accent2, items: [
      "Cây Huffman (min-heap), đóng gói và giải mã bitstream",
      "Kiểm tra toàn vẹn: so pixel, MSE, PSNR, SHA-256",
      "Thu thập bộ ảnh, chạy và đo đạc thực nghiệm",
      "Slide thuyết trình và báo cáo Chương 3" ] },
  ];
  people.forEach((p, i) => {
    const x = 0.6 + i * 6.2;
    card(s, x, 1.55, 5.9, 4.1, C.background2, `card-${p.init}`);
    badge(s, x + 0.4, 1.9, p.init, p.fill, 0.9);
    txt(s, p.name, { x: x + 1.55, y: 1.95, w: 4.1, h: 0.45, fontSize: 22, bold: true, color: C.text2, fontFace: "Cambria" });
    txt(s, p.role, { x: x + 1.55, y: 2.42, w: 4.1, h: 0.35, fontSize: 15, color: C.accent6 });
    bullets(s, p.items, { x: x + 0.45, y: 3.2, w: 5.1, h: 2.3, fontSize: 17 });
  });
  s.addNotes("Phân công công việc của hai thành viên.");
}

// ================================================================ 3. Đề bài
{
  const s = content("Đề bài yêu cầu 4 việc", "Mở đầu");
  const reqs = [
    ["Mã hóa và giải mã RLE, Huffman", "rle.py, huffman.py — file .rle/.huf có header, giải mã độc lập. Mở rộng: RLE+Huffman (hybrid.py)"],
    ["Histogram và entropy để giải thích khả năng nén", "metrics.py — H(X), L_avg, kiểm tra H ≤ L_avg < H+1, thống kê độ dài dải chạy"],
    ["So sánh tỷ lệ nén: nhị phân, xám, màu", `4 ảnh đại diện + ${N_DATA} ảnh thực tế × 3 phiên bản × 3 phương pháp`],
    ["Kiểm tra toàn vẹn ảnh giải mã", "Đọc lại file nén từ đĩa, giải mã, so từng pixel, MSE, PSNR, SHA-256"],
  ];
  reqs.forEach(([head, body], i) => {
    const x = 0.6 + (i % 2) * 6.2, y = 1.55 + Math.floor(i / 2) * 2.55;
    card(s, x, y, 5.9, 2.3, C.background2, `req-${i + 1}`);
    badge(s, x + 0.35, y + 0.35, i + 1, C.accent3);
    txt(s, head, { x: x + 1.1, y: y + 0.35, w: 4.55, h: 0.6, fontSize: 19, bold: true, color: C.text2, valign: "middle" });
    txt(s, body, { x: x + 1.1, y: y + 1.05, w: 4.55, h: 1.1, fontSize: 15, color: C.text1 });
  });
  s.addNotes("Bóc tách đề bài thành 4 yêu cầu và chỉ ra phần cài đặt tương ứng trong chương trình.");
}

// ================================================================ 4. RLE
pres.addSection({ title: "Cơ sở lý thuyết" });
{
  const s = content("RLE: thay dải pixel lặp bằng cặp (độ dài, giá trị)", "Cơ sở lý thuyết");
  txt(s, "Ví dụ một hàng ảnh nhị phân", { x: 0.6, y: 1.55, w: 6, h: 0.4, fontSize: 16, bold: true, color: C.accent6 });
  const px = [255, 255, 255, 255, 255, 0, 0, 0, 255, 255, 255, 255];
  pixelStrip(s, 0.6, 2.05, px, 0.5);
  const groups = [[0, 5, "(5, 255)"], [5, 3, "(3, 0)"], [8, 4, "(4, 255)"]];
  groups.forEach(([start, len, label]) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6 + start * 0.5 + 0.04, y: 2.7, w: len * 0.5 - 0.08, h: 0.48,
      rectRadius: 0.08, fill: { color: C.accent1 }, line: { type: "none" } });
    s.addText(label, { isTextBox: true, x: 0.6 + start * 0.5, y: 2.7, w: len * 0.5, h: 0.48, align: "center", valign: "middle",
      fontSize: 15, bold: true, color: C.background1, fontFace: "Courier New", margin: 0 });
  });
  txt(s, "12 pixel (12 byte)  →  3 cặp (6 byte)", { x: 0.6, y: 3.35, w: 6, h: 0.4, fontSize: 16, color: C.text1 });
  card(s, 0.6, 4.1, 6.0, 2.55, C.background2, "rle-formula");
  txt(s, "Khi nào RLE có lợi?", { x: 0.9, y: 4.3, w: 5.5, h: 0.4, fontSize: 18, bold: true, color: C.text2 });
  txt(s, "CR(RLE) ≈ độ dài dải trung bình / 2", { x: 0.9, y: 4.8, w: 5.5, h: 0.5, fontSize: 22, bold: true, color: C.accent1, fontFace: "Cambria" });
  txt(s, "Mỗi dải tốn 2 byte, nên dải trung bình phải dài hơn 2 pixel. Ảnh tự nhiên có dải ≈ 1.2 pixel → RLE làm phình dữ liệu.",
    { x: 0.9, y: 5.45, w: 5.5, h: 1.1, fontSize: 15 });
  txt(s, "Cài đặt trong rle.py", { x: 7.2, y: 1.55, w: 5.5, h: 0.4, fontSize: 16, bold: true, color: C.accent6 });
  bullets(s, [
    "Mỗi dải → cặp (count, value), mỗi số 1 byte",
    "Dải dài hơn 255 pixel được tách thành nhiều cặp",
    "Ảnh màu: Planar RLE — nén lần lượt từng kênh B, G, R để không làm gãy dải",
    "Header 13 byte: RLE1 · Height · Width · Channels",
    "Giải mã kiểm tra số byte khớp H × W × C và độ dài payload chẵn",
    "Độ phức tạp O(N), chỉ duyệt một lượt",
  ], { x: 7.2, y: 2.05, w: 5.5, h: 4.6 });
  s.addNotes("RLE khai thác dư thừa không gian: các pixel liền kề giống nhau. Công thức CR xấp xỉ độ dài dải trung bình chia 2 sẽ được kiểm chứng ở phần thực nghiệm.");
}

// ================================================================ 5. Huffman
{
  const s = content("Huffman: ký hiệu càng hay gặp, mã càng ngắn", "Cơ sở lý thuyết");
  // cây ví dụ: A 0.5, B 0.25, C 0.125, D 0.125
  const nodes = {
    r: [3.2, 1.75, "1.0"], n1: [4.45, 2.85, "0.5"], n2: [5.55, 3.95, "0.25"],
    A: [1.95, 2.85, "A\n0.5"], B: [3.35, 3.95, "B\n.25"], C: [4.45, 5.05, "C\n.125"], D: [6.65, 5.05, "D\n.125"],
  };
  const edges = [["r", "A", "0"], ["r", "n1", "1"], ["n1", "B", "0"], ["n1", "n2", "1"], ["n2", "C", "0"], ["n2", "D", "1"]];
  const R = 0.36;
  edges.forEach(([a, b, bit]) => {
    const [x1, y1] = nodes[a], [x2, y2] = nodes[b];
    const left = x2 < x1;
    s.addShape(pres.shapes.LINE, { x: Math.min(x1, x2) + R, y: y1 + R, w: Math.abs(x2 - x1), h: y2 - y1,
      flipH: left, line: { color: "9AA5B4", width: 1.5 } });
    txt(s, bit, { x: (x1 + x2) / 2 + R + (left ? -0.38 : 0.12), y: (y1 + y2) / 2 + R - 0.22, w: 0.3, h: 0.3,
      fontSize: 15, bold: true, color: C.accent3, align: "center" });
  });
  Object.entries(nodes).forEach(([k, [x, y, label]]) => {
    const leaf = ["A", "B", "C", "D"].includes(k);
    s.addShape(pres.shapes.OVAL, { x, y, w: 2 * R, h: 2 * R, fill: { color: leaf ? C.accent2 : C.background2 },
      line: { color: leaf ? C.accent2 : "9AA5B4", width: 1 } });
    s.addText(label, { isTextBox: true, x, y, w: 2 * R, h: 2 * R, align: "center", valign: "middle", margin: 0,
      fontSize: leaf ? 11 : 12, bold: leaf, color: leaf ? C.background1 : C.text1 });
  });
  txt(s, "Mã:  A = 0   B = 10   C = 110   D = 111", { x: 0.6, y: 6.1, w: 6.6, h: 0.4, fontSize: 16, fontFace: "Courier New", color: C.text2, bold: true });
  txt(s, "L_avg = 0.5·1 + 0.25·2 + 0.125·3·2 = 1.75 bit = H(X)", { x: 0.6, y: 6.5, w: 6.6, h: 0.35, fontSize: 14, color: C.accent6 });

  txt(s, "Cài đặt trong huffman.py", { x: 7.6, y: 1.55, w: 5.1, h: 0.4, fontSize: 16, bold: true, color: C.accent6 });
  bullets(s, [
    "Đếm tần số 256 mức byte của ảnh",
    "Min-heap: ghép 2 nút có tần số nhỏ nhất đến khi còn 1 gốc",
    "Trái = 0, phải = 1 → mã tiền tố (không mã nào là đầu của mã khác)",
    "Đóng gói bit thật vào byte, header lưu bảng tần số để dựng lại cây",
  ], { x: 7.6, y: 2.05, w: 5.1, h: 2.6 });
  card(s, 7.6, 4.75, 5.1, 1.95, C.background2, "huf-bound");
  txt(s, "H(X) ≤ L_avg < H(X) + 1", { x: 7.9, y: 4.95, w: 4.6, h: 0.5, fontSize: 22, bold: true, color: C.accent2, fontFace: "Cambria" });
  txt(s, "Mỗi pixel tốn ít nhất 1 bit → Huffman trên ảnh 8-bit không vượt quá 8x.", { x: 7.9, y: 5.55, w: 4.6, h: 1.0, fontSize: 15 });
  s.addNotes("Huffman khai thác dư thừa thống kê: phân bố histogram không đều. Cây ví dụ cho L_avg đúng bằng entropy vì xác suất là luỹ thừa của 1/2.");
}

// ================================================================ 6. Entropy
{
  const s = content("Entropy giải thích Huffman, độ dài dải giải thích RLE", "Cơ sở lý thuyết");
  card(s, 0.6, 1.55, 5.0, 5.1, C.text2, "entropy-card");
  txt(s, "Entropy Shannon (bậc 0)", { x: 0.95, y: 1.85, w: 4.4, h: 0.4, fontSize: 16, bold: true, color: C.accent5 });
  txt(s, "H(X) = − Σ pₖ · log₂ pₖ", { x: 0.95, y: 2.4, w: 4.4, h: 0.6, fontSize: 26, bold: true, color: C.background1, fontFace: "Cambria" });
  txt(s, "pₖ lấy từ histogram: tỉ lệ pixel có mức xám k.", { x: 0.95, y: 3.15, w: 4.4, h: 0.7, fontSize: 15, color: "CADCFC" });
  txt(s, "8 / H(X)", { x: 0.95, y: 4.1, w: 4.4, h: 0.6, fontSize: 26, bold: true, color: C.background1, fontFace: "Cambria" });
  txt(s, "là giới hạn nén khi mã hóa TỪNG PIXEL ĐỘC LẬP — chỉ dựa vào histogram, bỏ qua quan hệ giữa các pixel cạnh nhau.",
    { x: 0.95, y: 4.8, w: 4.4, h: 1.5, fontSize: 15, color: "CADCFC" });

  const b = IMG["Ảnh nhị phân (Tài liệu)"], g = IMG["Ảnh xám"];
  const facts = [
    [C.accent2, "Ảnh xám: Huffman sát entropy",
      `H = ${n2(g.entropy)} bit, L_avg = ${n2(g.huffman_l_avg)} bit → CR ≈ 8/L_avg = ${cr(g.huffman.compression_ratio)}. Histogram trải rộng nên gần như không nén được.`],
    [C.accent2, "Ảnh nhị phân: Huffman bị chặn ở 8x",
      `H = ${n2(b.entropy)} < 1 bit nhưng mỗi pixel vẫn tốn 1 bit → ${cr(b.huffman.compression_ratio)}, không đạt 8/H = ${cr(b.theoretical_max_cr)}.`],
    [C.accent1, "RLE vượt cả 8/H — vì sao?",
      `RLE đạt ${cr(b.rle.compression_ratio)} vì khai thác dải dài trung bình ${b.run_stats.avg_run_length.toFixed(1)} pixel — thông tin mà histogram không chứa.`],
  ];
  facts.forEach(([col, head, body], i) => {
    const y = 1.55 + i * 1.75;
    badge(s, 6.1, y + 0.05, i + 1, col);
    txt(s, head, { x: 6.9, y, w: 5.8, h: 0.45, fontSize: 19, bold: true, color: C.text2 });
    txt(s, body, { x: 6.9, y: y + 0.5, w: 5.8, h: 1.1, fontSize: 15 });
  });
  s.addNotes("Đây là câu hỏi hay gặp: vì sao RLE lại vượt giới hạn 8/H? Vì 8/H chỉ đúng cho mã hóa từng pixel độc lập.");
}

// ================================================================ 7. Divider
pres.addSection({ title: "Thực nghiệm" });
{
  const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Thực nghiệm" });
  txt(s, "PHẦN 2", { x: 0.8, y: 1.55, w: 6, h: 0.4, fontSize: 16, bold: true, color: C.accent5, charSpacing: 2 });
  s.addText("Kết quả thực nghiệm", { placeholder: "title" });
  s.addText(`4 ảnh đại diện phân tích chi tiết  ·  ${N_DATA} ảnh thực tế  ·  ${totalChecks} lần nén – giải mã`, { placeholder: "body" });
  pixelStrip(s, 0.8, 5.55, [0, 0, 255, 255, 255, 255, 255, 0, 0, 0, 255, 255], 0.4, "0B1426", "FFFFFF", "3A4A6B");
}

// ================================================================ 8. Histogram
{
  const s = content("Histogram quyết định khả năng nén của Huffman", "Thực nghiệm");
  s.addImage({ path: path.join(ASSET_DIR, "histograms_and_entropy.png"), x: 0.6, y: 1.4, w: 12.1, h: 3.36,
    altText: "Histogram và entropy của ảnh nhị phân, ảnh xám và ảnh màu" });
  const notes = [
    [C.text2, "Nhị phân", "Chỉ 2 cột (0 và 255), H < 1 bit → Huffman đạt mức trần 8x"],
    [C.accent4, "Ảnh xám", "253 mức trải rộng, H ≈ 7.4 bit → chỉ tiết kiệm khoảng 6%"],
    [C.accent2, "Ảnh màu", "3 kênh, 256 mức, H ≈ 7.6 bit → CR ≈ 1.05x"],
  ];
  notes.forEach(([col, head, body], i) => {
    const x = 0.6 + i * 4.1;
    card(s, x, 5.0, 3.85, 1.7, C.background2, `hist-note-${i}`);
    txt(s, head, { x: x + 0.3, y: 5.15, w: 3.3, h: 0.4, fontSize: 18, bold: true, color: col });
    txt(s, body, { x: x + 0.3, y: 5.6, w: 3.3, h: 1.0, fontSize: 15 });
  });
}

// ================================================================ 9. Bảng phân tích
{
  const s = content("Entropy và độ dài dải dự đoán đúng kết quả nén", "Thực nghiệm");
  const head = ["Ảnh", "Số mức", "H(X)", "L_avg", "8/H", "Dải TB", "CR RLE", "CR Huffman", "CR RLE+HUF"].map(tableHead);
  const rows = REP.map((r) => {
    const crs = [r.rle.compression_ratio, r.huffman.compression_ratio, r.hybrid.compression_ratio];
    const best = Math.max(...crs);
    const crCell = (v) => cell(cr(v), { bold: v === best, fill: { color: v === best ? "DDF2EE" : "FFFFFF" },
      color: v < 1 ? "B23A3A" : "1B1F27" });
    return [
      cell(r.name.replace(" RGB", ""), { align: "left", bold: true }), cell(r.unique_symbols), cell(n2(r.entropy)),
      cell(n2(r.huffman_l_avg)), cell(cr(r.theoretical_max_cr)), cell(r.run_stats.avg_run_length.toFixed(2)),
      crCell(crs[0]), crCell(crs[1]), crCell(crs[2]),
    ];
  });
  s.addTable([head, ...rows], { x: 0.6, y: 1.5, w: 12.1, colW: [2.6, 0.95, 0.95, 0.95, 1.05, 1.05, 1.4, 1.55, 1.6],
    fontSize: 15, fontFace: "Calibri", rowH: 0.55, border: { type: "solid", pt: 0.75, color: "D5DBE3" },
    fill: { color: "FFFFFF" }, color: "1B1F27" });
  const takeaways = [
    [C.accent1, `Dải TB > 2 thì RLE có lợi: ảnh tài liệu ${REP[0].run_stats.avg_run_length.toFixed(1)} pixel → ${cr(REP[0].rle.compression_ratio)}; ảnh xám ${REP[2].run_stats.avg_run_length.toFixed(2)} pixel → phình ${cr(REP[2].rle.compression_ratio)}`],
    [C.accent2, "L_avg luôn nằm giữa H và H+1 (định lý Shannon) — đúng trên cả 4 ảnh"],
    [C.accent3, `RLE rồi Huffman cho ảnh nhị phân tốt nhất: ${cr(REP[0].hybrid.compression_ratio)} và ${cr(REP[1].hybrid.compression_ratio)}`],
  ];
  takeaways.forEach(([col, t], i) => {
    s.addShape(pres.shapes.OVAL, { x: 0.65, y: 4.97 + i * 0.62, w: 0.22, h: 0.22, fill: { color: col }, line: { type: "none" } });
    txt(s, t, { x: 1.05, y: 4.85 + i * 0.62, w: 11.6, h: 0.5, fontSize: 16, valign: "middle" });
  });
  txt(s, "Ô tô xanh: phương pháp tốt nhất  ·  Chữ đỏ: phình dữ liệu (CR < 1)", { x: 0.6, y: 4.3, w: 12.1, h: 0.3, fontSize: 13, color: C.accent6 });
  s.addNotes("Ô tô xanh là phương pháp tốt nhất cho từng ảnh; chữ đỏ là trường hợp phình dữ liệu (CR < 1).");
}

// ================================================================ 10. Biểu đồ CR 4 ảnh
{
  const s = content("So sánh tỷ lệ nén trên 4 ảnh đại diện", "Thực nghiệm");
  const labels = ["Nhị phân (tài liệu)", "Nhị phân (Otsu)", "Ảnh xám", "Ảnh màu"];
  s.addChart(pres.charts.BAR, [
    { name: "RLE", labels, values: REP.map((r) => +r.rle.compression_ratio.toFixed(2)) },
    { name: "Huffman", labels, values: REP.map((r) => +r.huffman.compression_ratio.toFixed(2)) },
    { name: "RLE+Huffman", labels, values: REP.map((r) => +r.hybrid.compression_ratio.toFixed(2)) },
  ], { x: 0.6, y: 1.4, w: 8.4, h: 5.35, barDir: "col", barGrouping: "clustered", barGapWidthPct: 60,
    chartColors: SERIES, valAxisLogScaleBase: 10, valAxisMinVal: 0.1, valAxisMaxVal: 100,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0.00"x"',
    showLegend: true, legendPos: "b", valGridLine: { color: "E3E7ED", size: 0.5 }, catGridLine: { style: "none" },
    showTitle: true, title: "Tỷ lệ nén CR (thang log, CR < 1 là phình dữ liệu)", titleFontSize: 14, titleColor: "5B6573",
    titleFontFace: "+mn-lt", ...axisFont });
  const pts = [
    [C.accent1, "RLE", "Rất mạnh trên ảnh có vùng đồng nhất, nhưng phình 1.7 lần trên ảnh xám và màu"],
    [C.accent2, "Huffman", "Ổn định: không bao giờ phình, nhưng bị chặn ở 8x"],
    [C.accent3, "RLE+Huffman", "Kết hợp cả hai loại dư thừa — tốt nhất với ảnh nhị phân"],
  ];
  pts.forEach(([col, head, body], i) => {
    const y = 1.55 + i * 1.75;
    card(s, 9.3, y, 3.45, 1.55, C.background2, `cr-note-${i}`);
    txt(s, head, { x: 9.55, y: y + 0.15, w: 3.0, h: 0.4, fontSize: 18, bold: true, color: col });
    txt(s, body, { x: 9.55, y: y + 0.55, w: 3.0, h: 0.95, fontSize: 14 });
  });
}

// ================================================================ 11. Dataset
{
  const s = content(`Trên ${N_DATA} ảnh thực tế: kết luận vẫn giữ nguyên`, "Thực nghiệm");
  const types = [["bin", "Nhị phân"], ["gray", "Ảnh xám"], ["color", "Ảnh màu"]];
  const labels = types.map((t) => t[1]);
  s.addChart(pres.charts.BAR, [
    { name: "RLE", labels, values: types.map(([k]) => +OV[k].cr_rle.median.toFixed(2)) },
    { name: "Huffman", labels, values: types.map(([k]) => +OV[k].cr_huf.median.toFixed(2)) },
    { name: "RLE+Huffman", labels, values: types.map(([k]) => +OV[k].cr_hyb.median.toFixed(2)) },
  ], { x: 0.6, y: 1.4, w: 7.4, h: 5.35, barDir: "col", barGrouping: "clustered", barGapWidthPct: 60,
    chartColors: SERIES, valAxisLogScaleBase: 10, valAxisMinVal: 0.1, valAxisMaxVal: 100,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0.00"x"',
    showLegend: true, legendPos: "b", valGridLine: { color: "E3E7ED", size: 0.5 }, catGridLine: { style: "none" },
    showTitle: true, title: `CR trung vị trên ${N_DATA} ảnh (thang log)`, titleFontSize: 14, titleColor: "5B6573",
    titleFontFace: "+mn-lt", ...axisFont });
  const head = ["Loại ảnh", "Thắng nhiều nhất"].map(tableHead);
  const rows = types.map(([k, l]) => {
    const w = OV[k].wins;
    const parts = [["RLE", w.RLE], ["Huffman", w.Huffman], ["RLE+HUF", w["RLE+HUF"]]].filter(([, v]) => v > 0)
      .map(([n, v]) => `${n} ${v}/${N_DATA}`).join(", ");
    return [cell(l, { align: "left", bold: true }), cell(parts, { align: "left" })];
  });
  s.addTable([head, ...rows], { x: 8.3, y: 1.55, w: 4.4, colW: [1.4, 3.0], fontSize: 14, rowH: 0.5,
    border: { type: "solid", pt: 0.75, color: "D5DBE3" }, color: "1B1F27" });
  card(s, 8.3, 3.85, 4.4, 2.85, C.background2, "dataset-note");
  txt(s, "Vì sao dùng trung vị?", { x: 8.55, y: 4.0, w: 3.9, h: 0.4, fontSize: 17, bold: true, color: C.text2 });
  txt(s, `Ảnh trăng khuyết gần như toàn đen (H = 0.54) cho CR ảnh xám tới ${cr(OV.gray.cr_hyb.max)}, kéo trung bình lên ${cr(OV.gray.cr_hyb.mean)}. Trung vị phản ánh ảnh điển hình.`,
    { x: 8.55, y: 4.45, w: 3.9, h: 2.1, fontSize: 14 });
  s.addNotes(`Mỗi ảnh được tách thành 3 phiên bản: nhị phân (ngưỡng Otsu), xám và màu. Bộ gồm 7 ảnh cũ và 21 ảnh mới (chuyển từ JPEG sang PNG).`);
}

// ================================================================ 12. Lý thuyết vs thực nghiệm
{
  const s = content("Lý thuyết khớp thực nghiệm trên toàn bộ tập ảnh", "Thực nghiệm");
  const imgW = 5.4, imgH = imgW * 1166 / 1332;
  s.addImage({ path: path.join(ASSET_DIR, "dataset_rle_vs_run.png"), x: 0.6, y: 1.35, w: imgW, h: imgH,
    altText: "CR của RLE theo độ dài dải trung bình" });
  s.addImage({ path: path.join(ASSET_DIR, "dataset_huffman_vs_entropy.png"), x: 7.3, y: 1.35, w: imgW, h: imgH,
    altText: "CR của Huffman theo entropy" });
  txt(s, "Mọi điểm nằm trên đường CR = dải TB / 2. Ảnh có dải rất dài nằm thấp hơn vì mỗi cặp chỉ đếm tối đa 255 pixel.",
    { x: 0.6, y: 1.4 + imgH + 0.1, w: imgW, h: 0.8, fontSize: 14, color: C.accent6 });
  txt(s, "CR(Huffman) bám đường 8 / max(H, 1). Ảnh trăng (H = 0.54) thấp hơn vì 236 mức hiếm nhận mã dài, L_avg > 1.",
    { x: 7.3, y: 1.4 + imgH + 0.1, w: imgW, h: 0.8, fontSize: 14, color: C.accent6 });
}

// ================================================================ 13. Toàn vẹn
{
  const s = content("Kiểm tra toàn vẹn: giải mã từ file trên đĩa", "Thực nghiệm");
  const steps = ["Ảnh gốc", "Nén", "Ghi file\n.rle .huf .rlh", "Đọc lại file\nvà giải mã", "So sánh\nvới ảnh gốc"];
  steps.forEach((t, i) => {
    const x = 0.6 + i * 2.5;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.6, w: 2.0, h: 1.15, rectRadius: 0.12,
      fill: { color: i === 4 ? C.accent4 : C.background2 }, line: { type: "none" } });
    s.addText(t, { isTextBox: true, x, y: 1.6, w: 2.0, h: 1.15, align: "center", valign: "middle", margin: 0.05,
      fontSize: 15, bold: true, color: i === 4 ? C.background1 : C.text2 });
    if (i < 4) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + 2.08, y: 2.0, w: 0.34, h: 0.35,
      fill: { color: "9AA5B4" }, line: { type: "none" } });
  });
  const stats = [[`${totalOk}/${totalChecks}`, "lần giải mã trùng SHA-256"], ["0", "sai lệch pixel lớn nhất"],
    ["0.0", "MSE"], ["∞ dB", "PSNR"]];
  stats.forEach(([big, small], i) => {
    const x = 0.6 + i * 3.1;
    card(s, x, 3.25, 2.85, 2.0, C.background2, `stat-${i}`);
    txt(s, big, { x, y: 3.45, w: 2.85, h: 0.95, fontSize: i === 0 ? 40 : 48, bold: true, color: C.accent4, align: "center", fontFace: "Cambria" });
    txt(s, small, { x: x + 0.2, y: 4.5, w: 2.45, h: 0.6, fontSize: 15, color: C.accent6, align: "center" });
  });
  txt(s, `Gồm 4 ảnh đại diện × 3 phương pháp và ${N_DATA} ảnh × 3 phiên bản × 3 phương pháp. Ngoài ra có 7 bài kiểm thử tự động (test_codecs.py): ảnh 1×1, ảnh hằng, dải > 255, file hỏng, định lý Shannon, tính tiền tố của mã Huffman.`,
    { x: 0.6, y: 5.55, w: 12.1, h: 1.1, fontSize: 15 });
  s.addNotes("Giải mã từ file đọc lại trên đĩa, không dùng dữ liệu trong RAM, để chứng minh file nén tự chứa đủ thông tin.");
}

// ================================================================ 14. Thời gian
{
  const s = content("Thời gian thực thi và độ phức tạp", "Thực nghiệm");
  const ms = (v) => `${Math.round(v)} ms`;
  const head = ["Ảnh", "RLE mã hóa", "RLE giải mã", "Huffman mã hóa", "Huffman giải mã", "RLE+HUF mã hóa", "RLE+HUF giải mã"].map(tableHead);
  const rows = REP.map((r) => [cell(`${r.name.replace(" RGB", "")} (${r.shape.join("×")})`, { align: "left", bold: true }),
    cell(ms(r.rle.enc_time_ms)), cell(ms(r.rle.dec_time_ms)), cell(ms(r.huffman.enc_time_ms)), cell(ms(r.huffman.dec_time_ms)),
    cell(ms(r.hybrid.enc_time_ms)), cell(ms(r.hybrid.dec_time_ms))]);
  s.addTable([head, ...rows], { x: 0.6, y: 1.5, w: 12.1, colW: [3.1, 1.45, 1.45, 1.5, 1.55, 1.5, 1.55], fontSize: 14,
    rowH: 0.55, border: { type: "solid", pt: 0.75, color: "D5DBE3" }, color: "1B1F27" });
  const cx = [["RLE", C.accent1, "O(N) — duyệt một lượt"], ["Huffman", C.accent2, "O(N + K log K), K ≤ 256 mức"],
    ["Giải mã Huffman", C.accent3, "Bảng tra theo byte: mỗi byte 1 lần tra thay vì 8 bước đi trên cây"]];
  cx.forEach(([head, col, body], i) => {
    const x = 0.6 + i * 4.1;
    card(s, x, 4.6, 3.85, 1.6, C.background2, `cx-${i}`);
    txt(s, head, { x: x + 0.3, y: 4.8, w: 3.3, h: 0.4, fontSize: 18, bold: true, color: col });
    txt(s, body, { x: x + 0.3, y: 5.3, w: 3.3, h: 1.1, fontSize: 15 });
  });
  s.addNotes("Thời gian là của lần chạy gần nhất trên máy của nhóm, bằng Python thuần; số đo thay đổi theo cấu hình máy.");
}

// ================================================================ 15. Kết luận
pres.addSection({ title: "Kết luận" });
{
  const s = content("Kết luận: chọn phương pháp theo loại ảnh", "Kết luận");
  const cols = [
    [C.text2, "Ảnh nhị phân", "RLE+Huffman", `Trung vị ${cr(OV.bin.cr_hyb.median)} trên ${N_DATA} ảnh. Dải dài → RLE mạnh; chuỗi cặp RLE vẫn lệch phân bố → Huffman nén tiếp.`, "Ứng dụng: fax CCITT, ảnh tài liệu quét, mặt nạ phân đoạn"],
    [C.accent2, "Ảnh xám, màu tự nhiên", "Huffman", `Trung vị ${cr(OV.gray.cr_huf.median)} (xám), ${cr(OV.color.cr_huf.median)} (màu). RLE phình xuống ${cr(OV.gray.cr_rle.median)} vì pixel liền kề hiếm khi trùng.`, "Huffman là tầng mã hóa entropy cuối trong JPEG, PNG, ZIP"],
    [C.accent3, "Ảnh có vùng mịn lớn", "RLE+Huffman", `Bầu trời, mây, nền tối: dải TB > 2 nên RLE+Huffman thắng ở ${OV.gray.wins["RLE+HUF"]}/${N_DATA} ảnh xám.`, "Hướng phát triển: DPCM / dự đoán pixel trước khi mã hóa entropy"],
  ];
  cols.forEach(([col, head, pick, body, app], i) => {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.55, 3.85, 4.3, C.background2, `concl-${i}`);
    txt(s, head, { x: x + 0.3, y: 1.8, w: 3.3, h: 0.45, fontSize: 18, bold: true, color: C.accent6 });
    txt(s, pick, { x: x + 0.3, y: 2.3, w: 3.3, h: 0.6, fontSize: 28, bold: true, color: col, fontFace: "Cambria" });
    txt(s, body, { x: x + 0.3, y: 3.1, w: 3.3, h: 1.6, fontSize: 16 });
    txt(s, app, { x: x + 0.3, y: 4.85, w: 3.3, h: 0.85, fontSize: 13, italic: true, color: C.accent6 });
  });
  card(s, 0.6, 6.1, 12.1, 0.65, C.text2, "concl-bottom");
  txt(s, "Không có phương pháp tốt nhất cho mọi ảnh: histogram (entropy) và độ dài dải chạy cho biết nên chọn phương pháp nào.",
    { x: 0.9, y: 6.1, w: 11.5, h: 0.65, fontSize: 16, bold: true, color: C.background1, valign: "middle" });
}

// ================================================================ 16. Cảm ơn
{
  const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Kết luận" });
  s.addText("Cảm ơn thầy cô và các bạn đã lắng nghe", { placeholder: "title" });
  s.addText("Hỏi đáp và trao đổi", { placeholder: "body" });
  pixelStrip(s, 0.8, 5.55, [255, 255, 0, 0, 0, 0, 255, 255, 255, 0, 0, 255], 0.4, "0B1426", "FFFFFF", "3A4A6B");
}

// ---------------------------------------------------------------- ghi file
(async () => {
  await pres.writeFile({ fileName: OUT });
  if (process.env.PPTX_APPLY_THEME) {
    const { applyTheme } = require(process.env.PPTX_APPLY_THEME);
    await applyTheme(OUT, THEME);
  }
  console.log("Đã tạo:", OUT);
})();
