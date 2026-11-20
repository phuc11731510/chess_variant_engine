# -*- coding: utf-8 -*-
"""Mô tả quy tắc (Phần 1) và nhận xét cho từng ví dụ (Phần 3)."""

EFFECT = ("Thực hiện một nước đi chọn ô $B$ nghĩa là: xóa quân đối phương ở ô $B$ nếu có; xóa quân $Z$ khỏi ô $A$; "
          "đặt quân $Z$ vừa xóa vào ô $B$. Nếu ô $B$ có quân cùng phe với $Z$ thì không có nước đi nào chọn ô $B$.")
EFFECT_CJ = ("Riêng nước đi của quy tắc bắt nhảy (ô cam trên ảnh) có hiệu ứng khác: gọi $H$ là ô nằm chính giữa $A$ và $B$, tức $H=\\frac{A+B}{2}$; "
             "thực hiện nước đi này nghĩa là: xóa quân đối phương ở ô $H$; xóa quân $Z$ khỏi ô $A$; đặt quân $Z$ vừa xóa vào ô $B$. "
             "Ô $B$ của nước này luôn là ô trống.")

RAY = ("Trong các quy tắc dưới đây, \"các ô giữa trống\" của ô $B=A+k\\,d$ nghĩa là mọi ô $A+i\\,d$ với $1\\le i\lt k$ đều không có quân nào "
       "(quân cùng phe hay quân đối phương đều tính là có quân).")

DESC = {
    'K': f"""<p>{EFFECT}</p><p>{RAY}</p><ol>
<li>Với mỗi $d\\in\\{{(1,0),(-1,0)\\}}$ và mỗi số nguyên $k\\ge 1$: có nước đi chọn ô $B=A+k\\,d$ khi $B$ nằm trong bàn cờ, các ô giữa trống, và $B$ không có quân cùng phe.</li>
<li>Với mỗi $d\\in\\{{(0,1),(0,-1)\\}}$: có nước đi chọn ô $B=A+d$ khi $B$ nằm trong bàn cờ và không có quân cùng phe.</li>
<li>Với mỗi $v=(p,q)$, $p,q\\in\\{{3,-3\\}}$ (bốn vector): có nước đi chọn ô $B=A+v$ khi $B$ nằm trong bàn cờ, $B$ không có quân cùng phe, và hai ô cản $A+\\tfrac13 v$, $A+\\tfrac23 v$ đều không có quân.</li>
</ol><p>Ba quy tắc không bao giờ chọn cùng một ô $B$: ô của quy tắc 1 có hiệu tung độ với $A$ bằng 0, ô của quy tắc 2 có hiệu hoành độ bằng 0, ô của quy tắc 3 có cả hai hiệu khác 0.</p>""",

    'P1': f"""<p>{EFFECT}</p><p>{RAY}</p><ol>
<li>Với mỗi $d\\in\\{{(1,0),(-1,0),(0,1),(0,-1)\\}}$: có nước đi chọn ô $B=A+d$ khi $B$ nằm trong bàn cờ và không có quân cùng phe.</li>
<li>Với mỗi $u=(u_1,u_2)$, $u_1,u_2\\in\\{{1,-1\\}}$, đặt $P=A+u$.
<ul><li>(2a) Có nước đi chọn ô $B=P$ khi $P$ nằm trong bàn cờ và không có quân cùng phe.</li>
<li>(2b) Chỉ khi $P$ nằm trong bàn cờ và không có quân nào: với mỗi $d\\in\\{{(u_1,0),(0,u_2)\\}}$ và mỗi số nguyên $k\\ge1$, có nước đi chọn ô $B=P+k\\,d$ khi $B$ nằm trong bàn cờ, mọi ô $P+i\\,d$ với $1\\le i\lt k$ không có quân, và $B$ không có quân cùng phe.</li></ul></li>
</ol><p>Không có hai quy tắc (hay hai giá trị $u$) nào chọn cùng một ô $B$, vì mỗi ô chỉ có đúng một cách biểu diễn trong các dạng trên.</p>""",

    'P2': f"""<p>{EFFECT}</p><p>{RAY}</p><ol>
<li>Với mỗi $d\\in\\{{(1,1),(-1,1),(1,-1),(-1,-1)\\}}$ và mỗi $k\\ge1$: có nước đi chọn ô $B=A+k\\,d$ khi $B$ nằm trong bàn cờ, các ô giữa trống, và $B$ không có quân cùng phe.</li>
<li>Với mỗi $d\\in\\{{(1,0),(-1,0),(0,1),(0,-1)\\}}$ và mỗi $k\\ge1$: có nước đi chọn ô $B=A+k\\,d$ khi $B$ nằm trong bàn cờ, các ô giữa trống, và $B$ <b>không có quân nào</b>.</li>
<li>Với mỗi $d\\in\\{{(1,0),(-1,0),(0,1),(0,-1)\\}}$: gọi $h$ là số nguyên nhỏ nhất, $h\\ge1$, sao cho ô $A+h\\,d$ nằm trong bàn cờ và có quân (quân thuộc phe nào cũng được; quân này không bị xóa); nếu không có $h$ như vậy thì quy tắc này không có nước theo $d$. Có nước đi chọn ô $B=A+k\\,d$ với $k>h$ khi $B$ nằm trong bàn cờ, $B$ <b>có quân đối phương</b>, và mọi ô $A+i\\,d$ với $h\lt i\lt k$ không có quân.</li>
</ol><p>Ba quy tắc không bao giờ chọn cùng một ô: quy tắc 1 chỉ dùng vector chéo, còn trên các vector thẳng thì quy tắc 2 chỉ chọn ô trống và quy tắc 3 chỉ chọn ô có quân đối phương.</p>""",

    'P3': f"""<p>{EFFECT}</p><p>{RAY}</p><ol>
<li>Với mỗi $v\\in\\{{(\\pm1,\\pm2),(\\pm2,\\pm1)\\}}$ (tám vector): có nước đi chọn ô $B=A+v$ khi $B$ nằm trong bàn cờ và không có quân cùng phe.</li>
<li>Với mỗi $v\\in\\{{(\\pm3,\\pm3)\\}}$ (bốn vector): có nước đi chọn ô $B=A+v$ khi $B$ nằm trong bàn cờ và không có quân cùng phe (không có ô cản).</li>
<li>Với mỗi $d\\in\\{{(\\pm1,\\pm1)\\}}$ và mỗi $k\\in\\{{1,2,3,4\\}}$: có nước đi chọn ô $B=A+k\\,d$ khi $B$ nằm trong bàn cờ, các ô giữa trống, và $B$ không có quân nào.</li>
<li>Với mỗi $d\\in\\{{(\\pm1,\\pm1)\\}}$: gọi $h$ là số nhỏ nhất trong $\\{{1,2,3,4\\}}$ sao cho ô $A+h\\,d$ nằm trong bàn cờ và có quân (phe nào cũng được, không bị xóa); nếu không có thì không có nước theo $d$. Có nước đi chọn ô $B=A+(h+j)\\,d$ với $j\\in\\{{1,2,3,4\\}}$ khi $B$ nằm trong bàn cờ, $B$ có quân đối phương, và mọi ô $A+i\\,d$ với $h\lt i\lt h+j$ không có quân.</li>
</ol><p>Một ô có thể được nhiều quy tắc cùng chọn (ví dụ ô $A+(3,3)$ có thể được quy tắc 2, 3 hoặc 4 chọn); khi đó vẫn chỉ là một nước đi.</p>""",

    'P4': f"""<p>{EFFECT}</p><ol>
<li>Với mỗi $v=(p,q)$ có $\\{{|p|,|q|\\}}=\\{{1,2\\}}$ (tám vector): có nước đi chọn ô $B=A+v$ khi $B$ nằm trong bàn cờ, $B$ không có quân cùng phe, và ô cản không có quân. Ô cản là $A+(\\operatorname{{sgn}} p,0)$ nếu $|p|=2$, và là $A+(0,\\operatorname{{sgn}} q)$ nếu $|q|=2$.</li>
<li>Với mỗi $v=(p,q)$ có $\\{{|p|,|q|\\}}=\\{{2,3\\}}$ (tám vector): có nước đi chọn ô $B=A+v$ khi $B$ nằm trong bàn cờ và không có quân cùng phe.</li>
<li>Với mỗi $v\\in\\{{(3,1),(-1,3),(-3,-1),(1,-3)\\}}$ (chỉ bốn vector này): có nước đi chọn ô $B=A+v$ khi $B$ nằm trong bàn cờ và không có quân cùng phe.</li>
</ol><p>Ba quy tắc không bao giờ chọn cùng một ô (các vector có độ dài khác nhau). Bốn vector của quy tắc 3 không đối xứng qua trục nào nhưng xoay $90^\\circ$ thì giữ nguyên tập, nên quân của hai phe có cùng tập vector.</p>""",

    'P5': f"""<p>{EFFECT}</p><p>{RAY}</p><ol>
<li>Với mỗi $d\\in\\{{(1,0),(-1,0),(0,1),(0,-1)\\}}$: có nước đi chọn ô $B=A+d$ khi $B$ nằm trong bàn cờ và không có quân cùng phe.</li>
<li>Với mỗi $v\\in\\{{(\\pm2,\\pm2)\\}}$: có nước đi chọn ô $B=A+v$ khi $B$ nằm trong bàn cờ và không có quân cùng phe (không có ô cản).</li>
<li>Với mỗi $d\\in\\{{(0,1),(0,-1)\\}}$ và mỗi $k\\ge1$: có nước đi chọn ô $B=A+k\\,d$ khi $B$ nằm trong bàn cờ, các ô giữa trống, và $B$ không có quân cùng phe.</li>
<li>Với mỗi $v\\in\\{{(2,0),(-2,0)\\}}$: có nước đi chọn ô $B=A+v$ khi $B$ nằm trong bàn cờ và không có quân cùng phe (không có ô cản).</li>
</ol><p>Ô $A+(0,1)$ và $A+(0,-1)$ có thể được cả quy tắc 1 và quy tắc 3 chọn; khi đó vẫn chỉ là một nước đi. Ngoài ra không có hai quy tắc nào chọn cùng một ô.</p>""",

    'P6': f"""<p>{EFFECT}</p><ol>
<li>Với mỗi $v\\in\\{{(3,0),(-3,0),(0,3),(0,-3)\\}}$: có nước đi chọn ô $B=A+v$ khi $B$ nằm trong bàn cờ và không có quân cùng phe (không có ô cản).</li>
<li>Với mỗi $u=(u_1,u_2)$, $u_1,u_2\\in\\{{1,-1\\}}$, đặt $P=A+u$.
<ul><li>(2a) Có nước đi chọn ô $B=P$ khi $P$ nằm trong bàn cờ và không có quân cùng phe.</li>
<li>(2b) Chỉ khi $P$ nằm trong bàn cờ và không có quân nào: với mỗi $w\\in\\{{(2u_1,0),(0,2u_2)\\}}$, có nước đi chọn ô $B=P+w$ khi $B$ nằm trong bàn cờ và không có quân cùng phe (ô nằm giữa $P$ và $B$ không được xét).</li></ul></li>
</ol><p>Không có hai quy tắc nào chọn cùng một ô.</p>""",

    'P7': f"""<p>{EFFECT}</p><p>{EFFECT_CJ}</p><ol>
<li>Với mỗi $v\\in\\{{(\\pm1,\\pm2),(\\pm2,\\pm1)\\}}$: có nước đi chọn ô $B=A+v$ khi $B$ nằm trong bàn cờ và không có quân cùng phe.</li>
<li>Với mỗi $u\\in\\{{(\\pm1,\\pm1)\\}}$: có nước đi chọn ô $B=A+u$ khi $B$ nằm trong bàn cờ và <b>không có quân nào</b>.</li>
<li>(Bắt nhảy, ô cam.) Với mỗi $u\\in\\{{(\\pm1,\\pm1)\\}}$: có nước đi chọn ô $B=A+2u$ khi ô $H=A+u$ có quân đối phương, $B$ nằm trong bàn cờ, và $B$ không có quân nào.</li>
</ol><p>Ba quy tắc không bao giờ chọn cùng một ô.</p>""",

    'P8': f"""<p>{EFFECT}</p><ol>
<li>Với mỗi $d\\in\\{{(1,0),(-1,0),(0,1),(0,-1)\\}}$ và $k\\in\\{{1,2\\}}$: có nước đi chọn ô $B=A+k\\,d$ khi $B$ nằm trong bàn cờ, $B$ không có quân cùng phe, và nếu $k=2$ thì ô $A+d$ không có quân.</li>
<li>Với mỗi $d\\in\\{{(1,0),(-1,0),(0,1),(0,-1)\\}}$: gọi $h$ là số nhỏ nhất, $h\\ge1$, sao cho ô $A+h\\,d$ nằm trong bàn cờ và có quân (phe nào cũng được, không bị xóa); nếu không có thì không có nước theo $d$. Có nước đi chọn ô $B=A+(h+1)\\,d$ khi $B$ nằm trong bàn cờ và không có quân cùng phe.</li>
</ol><p>Hai quy tắc không bao giờ chọn cùng một ô: quy tắc 2 chọn ô cách $A$ ít nhất 2 bước, và khi đó ô $A+d$ hoặc một ô gần hơn có quân nên quy tắc 1 không tới được ô đó.</p>""",

    'P9': f"""<p>{EFFECT}</p><ol>
<li>Với mỗi $v=(p,q)$ có $\\{{|p|,|q|\\}}=\\{{1,2\\}}$: có nước đi chọn ô $B=A+v$ khi $B$ nằm trong bàn cờ, $B$ không có quân cùng phe, và ô cản không có quân. Ô cản là $A+(\\operatorname{{sgn}} p,0)$ nếu $|p|=2$, và là $A+(0,\\operatorname{{sgn}} q)$ nếu $|q|=2$.</li>
<li>Với mỗi $v\\in\\{{(\\pm2,\\pm2)\\}}$: có nước đi chọn ô $B=A+v$ khi $B$ nằm trong bàn cờ và không có quân cùng phe (không có ô cản).</li>
</ol><p>Hai quy tắc không bao giờ chọn cùng một ô.</p>""",

    'P10': f"""<p>{EFFECT}</p><ol>
<li>Với mỗi $v\\in\\{{(3,0),(-3,0),(0,3),(0,-3)\\}}$: có nước đi chọn ô $B=A+v$ khi $B$ nằm trong bàn cờ và không có quân cùng phe (không có ô cản).</li>
<li>Với mỗi $d\\in\\{{(\\pm1,\\pm1)\\}}$: gọi $h$ là số nhỏ nhất, $h\\ge1$, sao cho ô $A+h\\,d$ nằm trong bàn cờ và có quân (phe nào cũng được, không bị xóa); nếu không có thì không có nước theo $d$. Có nước đi chọn ô $B=A+(h+1)\\,d$ khi $B$ nằm trong bàn cờ và không có quân cùng phe.</li>
</ol><p>Hai quy tắc không bao giờ chọn cùng một ô.</p>""",

    'P11': f"""<p>{EFFECT}</p><ol>
<li>Với mỗi $v=(p,q)$ có $\\{{|p|,|q|\\}}=\\{{1,3\\}}$ (tám vector): có nước đi chọn ô $B=A+v$ khi $B$ nằm trong bàn cờ, $B$ không có quân cùng phe, và hai ô cản đều không có quân. Nếu $|p|=3$ thì hai ô cản là $A+(\\operatorname{{sgn}} p,0)$ và $A+(2\\operatorname{{sgn}} p,\\operatorname{{sgn}} q)$; nếu $|q|=3$ thì hai ô cản là $A+(0,\\operatorname{{sgn}} q)$ và $A+(\\operatorname{{sgn}} p,2\\operatorname{{sgn}} q)$.</li>
<li>Với mỗi $v\\in\\{{(3,2),(-2,3),(-3,-2),(2,-3)\\}}$ (chỉ bốn vector này): có nước đi chọn ô $B=A+v$ khi $B$ nằm trong bàn cờ và không có quân cùng phe.</li>
</ol><p>Hai quy tắc không bao giờ chọn cùng một ô. Bốn vector của quy tắc 2 xoay $90^\\circ$ thì giữ nguyên tập, nên quân của hai phe có cùng tập vector.</p>""",

    'P12': f"""<p>{EFFECT}</p><p>{EFFECT_CJ}</p><ol>
<li>Với mỗi $d\\in\\{{(1,0),(-1,0),(0,1),(0,-1)\\}}$: có nước đi chọn ô $B=A+d$ khi $B$ nằm trong bàn cờ và <b>không có quân nào</b>.</li>
<li>(Bắt nhảy, ô cam.) Với mỗi $d\\in\\{{(1,0),(-1,0),(0,1),(0,-1)\\}}$: có nước đi chọn ô $B=A+2d$ khi ô $H=A+d$ có quân đối phương, $B$ nằm trong bàn cờ, và $B$ không có quân nào.</li>
</ol><p>Hai quy tắc không bao giờ chọn cùng một ô.</p>""",
}

REMARK = {
    'K': [
        "Trên bàn trống, quy tắc 1 chọn cả 9 ô còn lại của hàng 5, quy tắc 2 chọn e6 và e4, quy tắc 3 chọn bốn ô h8, b8, h2, b2.",
        "Ô a5 có D nhưng không có nước nào chọn nó, vì dãy theo $(-1,0)$ đã dừng sau D ở b5. Ô f6 có D nhưng không thuộc quy tắc nào, và chính nó là ô cản làm mất ô h8. Ô h2 có D được chọn vì hai ô cản f4 và g3 đều trống.",
        "Các vector $(0,1)$, $(-3,3)$, $(-3,-3)$, $(3,3)$ cho ô nằm ngoài bàn cờ nên không có nước tương ứng. Ô g10 có D nhưng không được chọn, vì dãy theo $(1,0)$ dừng trước T ở d10.",
        "Ô g1 có D nhưng không được chọn: ô cản thứ nhất e3 trống nhưng ô cản thứ hai f2 có quân. Ô g7 bị mất vì ô cản thứ hai f6 có T. Ô a7 có D được chọn vì b6 và c5 trống.",
    ],
    'P1': [
        "Có 4 ô kề thẳng, 4 ô kề chéo, và 28 ô của chặng hai: mỗi ô kề chéo $P$ mở ra hai dãy thẳng đi ra xa $A$.",
        "Ô f6 có D: được chọn nhưng không mở chặng hai, nên f7, g6 và các ô sau đó không được chọn. Ô d6 có T: mất cả d6 lẫn hai dãy qua d6. Ô h4 có D nhưng không được chọn, vì dãy từ f4 theo $(1,0)$ dừng trước T ở g4.",
        "Từ góc a1 chỉ có một ô kề chéo nằm trong bàn là b2. Dãy từ b2 theo $(1,0)$ dừng sau D ở f2. Dãy từ b2 theo $(0,1)$ đi hết tới b10, vì T ở a5 không nằm trên dãy đó.",
        "Ô d8 có D nhưng không được chọn, vì dãy từ d4 theo $(0,1)$ dừng trước T ở d5. Ô h2 có D nhưng không được chọn, vì dãy từ d2 theo $(1,0)$ đã dừng sau D ở e2.",
    ],
    'P2': [
        "Trên bàn trống, quy tắc 3 không có nước nào vì không có quân để nhảy qua. Có 17 ô chéo và 18 ô thẳng.",
        "Ô e4 và h5 có D nằm trên cột và hàng của Z, nhưng quy tắc 2 không chọn ô có quân, còn quy tắc 3 không chọn quân đầu tiên trên dãy. Ô e2 được chọn nhờ nhảy qua e4, và D ở e4 không bị xóa. Ô c3 có D được quy tắc 1 chọn, vì trên đường chéo được chọn ô có quân đối phương.",
        "Ô f1 được chọn sau khi nhảy qua T ở c1, ô a6 được chọn sau khi nhảy qua D ở a3: quân bị nhảy qua thuộc phe nào cũng được và không bị xóa.",
        "Ô e9 có D nhưng không có nước nào chọn nó: theo $(0,1)$ quân đầu tiên là T ở e6, và quân đầu tiên sau e6 là T ở e8. Ô c5 có D nhưng không được chọn, còn b5 được chọn nhờ nhảy qua c5.",
    ],
    'P3': [
        "Bốn ô h8, b8, h2, b2 được cả quy tắc 2 và quy tắc 3 chọn; mỗi ô vẫn chỉ là một nước đi, nên tổng là 24 chứ không phải 28.",
        "Ô g7 có D nhưng không được chọn: quy tắc 3 chỉ chọn ô trống, còn quy tắc 4 không chọn quân đầu tiên trên dãy. Ô h8 được quy tắc 2 và quy tắc 4 cùng chọn. Ô c3 có D không bị chọn, vì quân đầu tiên sau c3 là T ở b2.",
        "Theo $(1,1)$, quân đầu tiên là T ở c3; quân tiếp theo là D ở h8, cách c3 năm bước, vượt quá giới hạn 4 bước nên không bắt được. Ô b3 có D được quy tắc 1 chọn.",
        "Theo $(1,1)$, quân đầu tiên là T ở h8, cách $A$ năm bước, nên quy tắc 4 không có nước theo hướng này dù j10 có D. Ô b2 có D đứng kề nên không được chọn, nhưng a1 được chọn nhờ nhảy qua b2. Ô f6 được quy tắc 2 và quy tắc 3 cùng chọn.",
    ],
    'P4': [
        "Có 8 ô kiểu Mã, 8 ô của quy tắc 2 và 4 ô của quy tắc 3, tổng 20.",
        "T ở e6 là ô cản của f7 và d7; T ở f5 là ô cản của g6 và g4, nên g4 có D vẫn không được chọn. Quy tắc 2 và 3 không có ô cản nên đủ cả. Ô f8 có D nhưng vector $(1,3)$ không thuộc quy tắc 3.",
        "Ô d3 và d1 bị loại vì ô cản c2 có T. Các vector cho ô ngoài bàn cờ bị bỏ.",
        "Các ô f8 $(1,3)$, d2 $(-1,-3)$, h4 $(3,-1)$ có D và có dạng $(\\pm1,\\pm3)$ hoặc $(\\pm3,\\pm1)$, nhưng không thuộc bốn vector $(3,1),(-1,3),(-3,-1),(1,-3)$, nên không có nước nào chọn chúng.",
    ],
    'P5': [
        "Ô e6 và e4 được quy tắc 1 và quy tắc 3 cùng chọn; mỗi ô vẫn là một nước đi, nên tổng là 17.",
        "T ở e8 chặn dãy theo $(0,1)$ nên e9, e10 không được chọn. Dãy theo $(0,-1)$ dừng sau D ở e2. Ô c5 có D được quy tắc 4 chọn, ô f5 có D được quy tắc 1 chọn.",
        "Ô a1 có D được quy tắc 1 và quy tắc 3 cùng chọn; ô a3 cũng vậy. Ô b2 có D được quy tắc 1 chọn.",
        "Bốn ô kề thẳng đều có quân, nhưng quy tắc 2 và quy tắc 4 là nước nhảy không có ô cản, nên g7, c7, g3, c3, g5, c5 vẫn được chọn.",
    ],
    'P6': [
        "Có 4 ô của quy tắc 1, 4 ô kề chéo và 8 ô của chặng hai (mỗi ô kề chéo $P$ mở ra hai ô $P+(2u_1,0)$ và $P+(0,2u_2)$).",
        "Ô f6 có D: chọn được f6 nhưng mất h6 và f8. Ô d6 có T: mất d6, b6 và d8. Ô d4 có D: chọn được d4 nhưng mất b4 và d2. Ô e8 và h5 có D được quy tắc 1 chọn; b4 có D không được chọn vì nó chỉ đến được qua d4.",
        "Ô kề chéo nằm trong bàn là c2 và a2. Ô c2 có D nên không có chặng hai qua c2 (mất e2 và c4). Từ a2, ô $a2+(-2,0)$ nằm ngoài bàn, ô $a2+(0,2)=a4$ được chọn.",
        "g6 nằm giữa f6 và h6, f7 nằm giữa f6 và f8, nhưng chặng hai là nước nhảy nên h6 và f8 vẫn được chọn. Ô d3 có D không thuộc quy tắc nào và không cản d2.",
    ],
    'P7': [
        "Không có quân đối phương nên không có nước bắt nhảy; có 8 ô kiểu Mã và 4 ô kề chéo.",
        "Các ô f6, d6, f4 có D đứng kề chéo: quy tắc 2 không chọn chúng. Chỉ g7 là ô cam (xóa D ở f6), vì c7 và g3 không trống. Ô f7 có D được quy tắc 1 chọn.",
        "Các ô c10, a10, a8 có D nhưng ô $B$ tương ứng nằm ngoài bàn cờ. D ở c8 bị xóa qua nước chọn ô d7.",
        "Mọi ô $B$ của nước bắt nhảy đều bị chiếm (g7 có T; c7, c3, g3 có D), nên không có ô cam. Bốn D kề chéo không bị nước nào xóa.",
    ],
    'P8': [
        "Không có quân nào để nhảy qua nên quy tắc 2 không có nước; chỉ có 8 ô của quy tắc 1.",
        "Ô h5 có D không được chọn (quy tắc 1 chỉ tới g5), nhưng i5 được chọn nhờ nhảy qua h5. Ô a5 có D được chọn nhờ nhảy qua T ở b5. Ô e3 có D được quy tắc 1 chọn, và e2 được chọn nhờ nhảy qua e3. Ô e9 có D được chọn nhờ nhảy qua T ở e8.",
        "Ô ngay sau j9, a9 và b10 nằm ngoài bàn cờ. Ô ngay sau b4 là b3, có T.",
        "Bốn ô kề thẳng đều có quân nên quy tắc 1 chỉ chọn được ba ô có D (không chọn f5 vì có T), còn quy tắc 2 chọn bốn ô ngay sau bốn quân kề đó. Ô g5 có D chỉ được chọn nhờ nhảy qua T ở f5.",
    ],
    'P9': [
        "Có 8 ô kiểu Mã và 4 ô của quy tắc 2, tổng 12.",
        "T ở e6 là ô cản của f7 và d7, nên d7 có D không được chọn. T ở d5 là ô cản của c6 và c4, nên c4 có D không được chọn. Ô f6 có D không thuộc quy tắc nào.",
        "Chỉ còn 2 nước là b4 và c4. Ô c3 và c1 bị loại vì ô cản b2 có D.",
        "f6 và d4 nằm giữa $A$ với g7 và c3, nhưng quy tắc 2 không có ô cản nên g7 và c3 vẫn được chọn.",
    ],
    'P10': [
        "Không có quân nào trên đường chéo nên quy tắc 2 không có nước; chỉ có 4 ô của quy tắc 1.",
        "Theo $(1,1)$ quân đầu tiên là T ở g7, ô ngay sau là h8 có T, nên không có nước. Ô e8 có D được quy tắc 1 chọn. Ô b8 và h2 có D không bị xóa, vì chúng là quân bị nhảy qua.",
        "Quân đầu tiên theo $(-1,1)$ và $(-1,-1)$ nằm sát mép nên ô ngay sau nằm ngoài bàn. Theo $(1,1)$ quân đầu tiên là e5 và ô sau là f6 có T. Theo $(1,-1)$ không có quân nào. Chỉ còn 2 nước của quy tắc 1.",
        "Quân kề chéo được nhảy qua dù là T hay D. Ô g3 và c7 có D được chọn (quân ở đó bị xóa), còn f4, d6, d4 không bị xóa.",
    ],
    'P11': [
        "Có 8 ô của quy tắc 1 và 4 ô của quy tắc 2, tổng 12.",
        "T ở e6 là ô cản thứ nhất của f8 và d8, nên f8 có D không được chọn. T ở g6 là ô cản thứ hai của h6 (hai ô cản là f5 và g6), nên h6 có D không được chọn. T ở c6 là ô cản thứ hai của b6. Ô b4 và d2 có D được chọn.",
        "Ô e10 và e8 bị loại vì ô cản thứ nhất của cả hai là c9, có T.",
        "Ô g8 $(2,3)$ và h3 $(3,-2)$ có D và có dạng $(\\pm2,\\pm3)$ hoặc $(\\pm3,\\pm2)$, nhưng không thuộc bốn vector của quy tắc 2, nên không có nước nào chọn chúng.",
    ],
    'P12': [
        "Không có quân đối phương nên chỉ có 4 nước bước thẳng.",
        "Các ô f5, e6, e4 có D đứng kề: quy tắc 1 không chọn chúng. Ô g5 và e7 là ô cam. D ở e4 không bị xóa vì ô e3 không trống.",
        "D ở a10: ô $B$ tương ứng nằm ngoài bàn cờ. D ở a8: ô a7 có T. Chỉ còn ô c9 (xóa D ở b9).",
        "Hai D liền nhau ở e6 và e7: ô $B$ là e7 không trống nên không nhảy được; tương tự với d5 và c5. Chỉ còn nước chọn e4.",
    ],
}

NAMES = {
    'K': 'Quân hoàng gia', 'P1': 'Quân 1', 'P2': 'Quân 2', 'P3': 'Quân 3', 'P4': 'Quân 4', 'P5': 'Quân 5',
    'P6': 'Quân 6', 'P7': 'Quân 7', 'P8': 'Quân 8', 'P9': 'Quân 9', 'P10': 'Quân 10', 'P11': 'Quân 11', 'P12': 'Quân 12',
}
