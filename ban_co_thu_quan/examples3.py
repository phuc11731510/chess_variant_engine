# -*- coding: utf-8 -*-
from examples import sq, L
from examples import EXAMPLES as E1
from examples2 import EXAMPLES as E2

EXAMPLES = {
    'R': E2['R'],
    'Q1': E2['Q1'],
    'Q2': [('Chỉ có Z trên bàn trống', 'e5', '', ''),
           ('Ăn kề bên theo cột, trượt chéo và bắt bằng cách nhảy qua một quân', 'e5', 'c5 c3', 'e6 f5 e8 a5 g7 e3'),
           ('Z ở góc bàn cờ', 'a1', 'a3', 'a7 d1 a2 c3'),
           ('Quân đầu tiên sau quân bị nhảy qua là quân cùng phe', 'e5', 'e7 e9 h5', 'e10 j5 d5 b5')],
    'Q3': E2['Q3'],
    'Q4': [('Chỉ có Z trên bàn trống', 'e5', '', ''),
           ('Quân đối phương ở ô Mã và trên các dãy chéo', 'e5', 'f4 d7 b2', 'f7 g7 h8 c3 a1 h2'),
           ('Giới hạn 4 ô của đoạn sau khi bắt chéo', 'a1', 'c3', 'h8 b3 e1 i5'),
           ('Giới hạn 4 ô của đoạn đầu và quân đối phương đứng kề', 'c3', 'h8', 'j10 b2 a1 a4')],
    'Q5': E2['Q6'],
    'Q6': [('Chỉ có Z trên bàn trống', 'e5', '', ''),
           ('Quân ở các ô nhảy tới', 'e5', 'h5 b2', 'e7 h6 c5 e2 d8'),
           ('Z ở gần mép bàn cờ', 'b2', 'b5', 'e3 d2 a5'),
           ('Ô Lạc đà không thuộc bốn vector chong chóng', 'e5', '', 'f8 h4 b6 d2 d8 b4')],
    'Q7': [('Chỉ có Z trên bàn trống', 'e5', '', ''),
           ('Quân làm bàn đạp nằm trong 3 ô đầu', 'e5', 'e7 c5', 'e8 g5 h5 e3'),
           ('Bàn đạp cách 4 ô không dùng được, ô đáp nằm ngoài bàn', 'b9', 'b5 e9', 'b10 a9'),
           ('Quân đứng kề Z', 'e5', 'f5', 'e6 d5 e4 g5 c5 h8')],
    'Q8': [('Chỉ có Z trên bàn trống', 'e5', '', ''),
           ('Chặng đầu bị chặn và ô cản của chặng hai', 'e5', 'd5 f7', 'f5 c7 g3 e4'),
           ('Z ở gần mép bàn cờ', 'b1', 'b2', 'a1 d1 c3'),
           ('Nước nhảy 2 ô ngang không bị quân ở giữa cản', 'e5', 'f5 d5', 'g5 c5 e7')],
    'Q9': E2['Q9'],
    'Q10': [('Chỉ có Z trên bàn trống', 'e5', '', ''),
            ('Dãy ngang dừng khi gặp quân, ô cản của nước nhảy chéo 3', 'e5', 'h5 f6', 'b5 a5 e6 h2'),
            ('Z ở gần mép bàn cờ', 'a10', 'd10', 'a9 d7'),
            ('Ô cản thứ hai của nước nhảy chéo 3', 'd4', 'f6 c4', 'g1 f2 a7')],
    'Q11': E2['Q11'],
    'Q12': E2['Q12'],
}
