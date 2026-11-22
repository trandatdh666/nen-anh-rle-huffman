"""
Module: dataset_generator.py
Tạo ảnh mẫu tổng hợp nếu cần (lưu riêng vào images/synthetic/ để không ghi đè ảnh người dùng):
  1. binary_document.png: Ảnh văn bản/sơ đồ nhị phân (có các dải trắng/đen đồng nhất lớn)
  2. grayscale_sample.png: Ảnh xám tổng hợp
  3. color_sample.png: Ảnh màu tổng hợp
"""

import os
import cv2
import numpy as np

def generate_binary_document(width=512, height=512) -> np.ndarray:
    """
    Tạo ảnh nhị phân mô phỏng tài liệu/bản vẽ kỹ thuật:
    Nền trắng (255), chữ và hình vẽ đen (0), có các dải đồng nhất lớn.
    """
    img = np.full((height, width), 255, dtype=np.uint8)
    
    # Khối hình học
    cv2.rectangle(img, (40, 40), (200, 150), 0, -1)
    cv2.circle(img, (380, 100), 60, 0, -1)
    cv2.rectangle(img, (260, 220), (460, 320), 0, 4)
    cv2.circle(img, (120, 260), 50, 0, 4)
    
    # Các dòng kẻ mô phỏng văn bản
    for y in range(360, 480, 25):
        cv2.line(img, (50, y), (460, y), 0, 5)
        
    cv2.putText(img, "LOSSLESS COMPRESSION", (40, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)
    cv2.putText(img, "NHOM 30 - DE TAI 30", (60, 500), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 0, 2)
    
    _, binary = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
    return binary

def generate_grayscale_image(width=512, height=512) -> np.ndarray:
    """Tạo ảnh xám gradient mượt"""
    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, height)
    xx, yy = np.meshgrid(x, y)
    gradient = 180 * (np.sin(2 * np.pi * xx) * np.cos(2 * np.pi * yy) + 1) / 2
    r = np.sqrt((xx - 0.5) ** 2 + (yy - 0.5) ** 2)
    waves = 50 * (np.sin(20 * np.pi * r) + 1) / 2
    base = np.clip(gradient + waves, 0, 255).astype(np.uint8)
    return cv2.GaussianBlur(base, (7, 7), 2)

def generate_color_image(width=512, height=512) -> np.ndarray:
    """Tạo ảnh màu đồ họa phong cảnh"""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height // 2):
        factor = y / (height // 2)
        img[y, :] = [int(240 - factor * 40), int(200 - factor * 70), int(120 - factor * 90)]
    for y in range(height // 2, height):
        factor = (y - height // 2) / (height // 2)
        img[y, :] = [int(40 + factor * 20), int(160 - factor * 60), int(50 - factor * 20)]
    cv2.circle(img, (120, 100), 55, (40, 220, 255), -1)
    cv2.rectangle(img, (260, 240), (440, 420), (160, 220, 240), -1)
    return img

def ensure_sample_images(output_dir="images/synthetic"):
    os.makedirs(output_dir, exist_ok=True)
    bin_p = os.path.join(output_dir, "binary_document.png")
    gray_p = os.path.join(output_dir, "grayscale_sample.png")
    col_p = os.path.join(output_dir, "color_sample.png")
    
    if not os.path.exists(bin_p):
        cv2.imwrite(bin_p, generate_binary_document())
    if not os.path.exists(gray_p):
        cv2.imwrite(gray_p, generate_grayscale_image())
    if not os.path.exists(col_p):
        cv2.imwrite(col_p, generate_color_image())
    return bin_p, gray_p, col_p
