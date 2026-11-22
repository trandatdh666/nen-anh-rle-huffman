"""
Kiểm thử tự động: tính đúng đắn (lossless round-trip) của RLE, Huffman, RLE+Huffman
và các đại lượng lý thuyết (entropy, định lý Shannon, thống kê dải chạy).

Chạy:  python -m unittest test_codecs -v
"""

import unittest
from collections import Counter

import numpy as np

from rle import compress_rle, decompress_rle, rle_decode_bytes
from huffman import compress_huffman, decompress_huffman, build_huffman_tree, build_codes
from hybrid import compress_rle_huffman, decompress_rle_huffman
from metrics import (
    compute_entropy,
    compute_huffman_avg_length,
    compute_run_stats,
    check_shannon_bound,
    verify_image_integrity,
)

CODECS = {
    "RLE": (compress_rle, decompress_rle),
    "Huffman": (compress_huffman, decompress_huffman),
    "RLE+Huffman": (compress_rle_huffman, decompress_rle_huffman),
}


def _cases():
    rng = np.random.default_rng(42)
    return {
        "1x1": np.array([[7]], np.uint8),
        "ảnh hằng": np.full((50, 70), 200, np.uint8),
        "dải > 255": np.zeros((1, 1000), np.uint8),
        "nhị phân ngẫu nhiên": rng.integers(0, 2, (31, 17)).astype(np.uint8) * 255,
        "xám ngẫu nhiên 256 mức": rng.integers(0, 256, (64, 64), dtype=np.uint8),
        "màu ngẫu nhiên": rng.integers(0, 256, (20, 30, 3), dtype=np.uint8),
        "màu hằng": np.full((10, 10, 3), 5, np.uint8),
        "màu không vuông, ít mức": rng.integers(0, 4, (7, 13, 3), dtype=np.uint8),
    }


class TestLosslessRoundTrip(unittest.TestCase):
    def test_all_codecs_all_cases(self):
        for case_name, img in _cases().items():
            for codec_name, (enc, dec) in CODECS.items():
                with self.subTest(case=case_name, codec=codec_name):
                    out = dec(enc(img))
                    integ = verify_image_integrity(img, out)
                    self.assertTrue(integ["is_identical"])
                    self.assertEqual(integ["mse"], 0.0)
                    self.assertTrue(integ["sha256_match"])

    def test_rle_rejects_corrupt_payload(self):
        with self.assertRaises(ValueError):
            rle_decode_bytes(b"\x03", 3)

    def test_wrong_magic_rejected(self):
        img = np.zeros((4, 4), np.uint8)
        with self.assertRaises(ValueError):
            decompress_rle(compress_huffman(img))
        with self.assertRaises(ValueError):
            decompress_huffman(compress_rle(img))


class TestTheory(unittest.TestCase):
    def test_entropy_known_values(self):
        self.assertAlmostEqual(compute_entropy(np.full((8, 8), 9, np.uint8))[0], 0.0)
        half = np.array([[0, 255] * 8] * 4, np.uint8)
        self.assertAlmostEqual(compute_entropy(half)[0], 1.0)
        uniform = np.arange(256, dtype=np.uint8).reshape(16, 16)
        self.assertAlmostEqual(compute_entropy(uniform)[0], 8.0)

    def test_shannon_source_coding_theorem(self):
        rng = np.random.default_rng(1)
        for _ in range(20):
            k = int(rng.integers(2, 256))
            img = rng.integers(0, k, (32, 32)).astype(np.uint8)
            freq = dict(Counter(img.tobytes()))
            codes = build_codes(build_huffman_tree(freq))
            l_avg, _ = compute_huffman_avg_length(freq, codes)
            h = compute_entropy(img)[0]
            self.assertTrue(check_shannon_bound(h, l_avg), (h, l_avg))

    def test_huffman_prefix_free(self):
        rng = np.random.default_rng(2)
        img = rng.integers(0, 50, (40, 40)).astype(np.uint8)
        codes = list(build_codes(build_huffman_tree(dict(Counter(img.tobytes())))).values())
        for a in codes:
            for b in codes:
                if a != b:
                    self.assertFalse(b.startswith(a))

    def test_run_stats_matches_rle_size(self):
        rng = np.random.default_rng(3)
        for img in [np.zeros((10, 600), np.uint8),
                    rng.integers(0, 3, (30, 30)).astype(np.uint8),
                    rng.integers(0, 2, (10, 12, 3)).astype(np.uint8)]:
            rs = compute_run_stats(img)
            payload_len = len(compress_rle(img)) - 13  # trừ header 13 byte
            self.assertEqual(rs["rle_pairs_estimate"] * 2, payload_len)


if __name__ == "__main__":
    unittest.main(verbosity=2)
