# -*- coding: utf-8 -*-
"""Thế cờ ví dụ cho từng quân: (mô tả ngắn, Z, danh sách T, danh sách D)."""


def sq(s):
    return ('abcdefghij'.index(s[0]) + 1, int(s[1:]))


def L(s):
    return [sq(t) for t in s.split()] if s else []


EXAMPLES = {
    'K': [
        ('Chỉ có Z trên bàn trống', 'e5', '', ''),
        ('Có quân chặn trên hàng, trên cột và trên đường chéo', 'e5', 'h5 e6 c7', 'b5 a5 e4 f6 h2'),
        ('Z ở gần mép bàn cờ', 'b10', 'd10', 'g10 b9'),
        ('Ô cản thứ hai của nước nhảy chéo 3 ô', 'd4', 'f6 c4', 'g1 f2 a7 j4'),
    ],
    'P1': [
        ('Chỉ có Z trên bàn trống', 'e5', '', ''),
        ('Chặng đầu bị chặn và chặng hai dừng khi gặp quân', 'e5', 'd6 g4 e6', 'f6 d2 e4 h4'),
        ('Z ở góc bàn cờ', 'a1', 'a5', 'f2 b1'),
        ('Ô có quân đối phương nhưng không có nước nào chọn nó', 'c3', 'd5', 'd8 g4 e2 b4 h2'),
    ],
    'P2': [
        ('Chỉ có Z trên bàn trống', 'e5', '', ''),
        ('Trượt chéo thường và bắt thẳng kiểu nhảy qua một quân', 'e5', 'e7 c5 g7', 'e9 a5 e4 e2 h5 c3'),
        ('Z ở góc bàn cờ', 'a1', 'c1', 'f1 a3 a6 d4'),
        ('Quân đầu tiên sau quân bị nhảy qua là quân cùng phe', 'e5', 'e6 e8 h5', 'e9 j5 b5 c5'),
    ],
    'P3': [
        ('Chỉ có Z trên bàn trống', 'e5', '', ''),
        ('Quân đối phương ở ô Mã, ô nhảy chéo 3 và trên đường chéo', 'e5', 'f4 d7 b2', 'f7 h8 g7 c3 a1 h2'),
        ('Giới hạn 4 ô của đoạn sau khi bắt chéo', 'a1', 'c3', 'h8 b3 e1 i5'),
        ('Giới hạn 4 ô của đoạn đầu và quân đối phương đứng kề', 'c3', 'h8', 'j10 b2 a1 a4'),
    ],
    'P4': [
        ('Chỉ có Z trên bàn trống', 'e5', '', ''),
        ('Ô cản của nước nhảy kiểu Mã', 'e5', 'e6 f5', 'd4 g4 c6 h6 f8'),
        ('Z ở gần mép bàn cờ', 'b2', 'c2', 'e3 a5 d5'),
        ('Ô Lạc đà không thuộc bốn vector của quy tắc 3', 'e5', 'h6', 'f8 d2 h4 b4 f2'),
    ],
    'P5': [
        ('Chỉ có Z trên bàn trống', 'e5', '', ''),
        ('Hai quy tắc cùng chọn một ô và dãy dọc bị chặn', 'e5', 'e8 c3', 'e2 g7 c5 f5'),
        ('Z ở gần mép bàn cờ', 'a2', 'a6', 'c4 a1 b2'),
        ('Nước nhảy không bị quân ở giữa cản', 'e5', 'f6 d5 f5 e6', 'g7 c5 g5 e4'),
    ],
    'P6': [
        ('Chỉ có Z trên bàn trống', 'e5', '', ''),
        ('Chặng đầu gặp quân cùng phe hoặc quân đối phương', 'e5', 'd6 g6', 'f6 d4 e8 h5 b4'),
        ('Z ở gần mép bàn cờ', 'b1', 'b4', 'c2 e1'),
        ('Chặng hai là nước nhảy nên không bị quân ở giữa cản', 'e5', 'g6 f7', 'h4 d3'),
    ],
    'P7': [
        ('Chỉ có Z trên bàn trống', 'e5', '', ''),
        ('Bắt nhảy chéo và quân đối phương đứng kề', 'e5', 'd4', 'f6 d6 c7 f4 g3 f7'),
        ('Z ở gần mép bàn cờ', 'b9', '', 'a10 c10 a8 c8 d10'),
        ('Ô B của nước bắt nhảy bị chiếm', 'e5', 'g7', 'f6 d6 c7 d4 c3 f4 g3'),
    ],
    'P8': [
        ('Chỉ có Z trên bàn trống', 'e5', '', ''),
        ('Nhảy qua quân đầu tiên trên hàng và cột', 'e5', 'e8 b5', 'e9 h5 e3 a5'),
        ('Ô ngay sau quân đầu tiên nằm ngoài bàn cờ hoặc có quân cùng phe', 'b9', 'b4 b3', 'b10 a9 j9'),
        ('Quân đứng kề Z', 'e5', 'f5', 'e6 d5 e4 g5 c5'),
    ],
    'P9': [
        ('Chỉ có Z trên bàn trống', 'e5', '', ''),
        ('Ô cản của nước nhảy kiểu Mã', 'e5', 'e6 d5', 'd7 c4 f3 f6'),
        ('Z ở gần mép bàn cờ', 'a2', 'b3', 'c4 b2'),
        ('Nước nhảy $(\\pm2,\\pm2)$ không bị cản', 'e5', 'f6 d4', 'g7 c3 c7'),
    ],
    'P10': [
        ('Chỉ có Z trên bàn trống', 'e5', '', ''),
        ('Nhảy qua quân đầu tiên trên đường chéo', 'e5', 'g7 c3 h8', 'b8 h2 e8'),
        ('Ô ngay sau quân đầu tiên nằm ngoài bàn cờ hoặc có quân cùng phe', 'b2', 'a1 e5 f6', 'a3 b5'),
        ('Quân đứng kề trên đường chéo', 'e5', 'f6', 'd4 f4 g3 d6 c7'),
    ],
    'P11': [
        ('Chỉ có Z trên bàn trống', 'e5', '', ''),
        ('Hai ô cản của nước nhảy kiểu Lạc đà', 'e5', 'e6 g6 c6', 'f8 h6 d2 b4'),
        ('Z ở gần mép bàn cờ', 'b9', 'c9', 'e8 c6'),
        ('Ô Ngựa vằn không thuộc bốn vector của quy tắc 2', 'e5', 'h7', 'g8 c8 b3 g2 h3'),
    ],
    'P12': [
        ('Chỉ có Z trên bàn trống', 'e5', '', ''),
        ('Bắt nhảy thẳng và quân đối phương đứng kề', 'e5', 'd5', 'e6 f5 e4 e3'),
        ('Z ở gần mép bàn cờ', 'a9', 'a7', 'a10 b9 a8'),
        ('Hai quân đối phương liền nhau trên một cột', 'e5', 'f5', 'e6 e7 d5 c5'),
    ],
}
