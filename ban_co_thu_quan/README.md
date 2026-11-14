# Bàn cờ biến thể 10x10: thử quân và luyện tập

Trang tĩnh: `index.html` (bàn cờ thử quân + chế độ luyện tập nước đi), `bieu_tuong_quan.html` (bảng biểu tượng), `anh_vi_du_bo_3.html` (ảnh ví dụ nước đi).

- Dựng lại trang bàn cờ: `python build_board.py` (ghép `board_template.html`, engine `betza_sim.js` và biểu tượng trong `svg/` thành `index.html`).
- Dựng lại bảng biểu tượng: `python build_svgs.py` rồi `python build_svg_gallery.py`.
- Còn lại là tài nguyên thiết kế: engine Betza (`betza_sim.js`), kiểm tra thế khởi đầu (`verify_fast.js`, `random_setup_ef.js`), tìm quân (`milp2.py`, `search*.js`), kiểm tra tàn cuộc (`endgame.js`), ảnh ví dụ.
