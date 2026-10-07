@echo off
rem Xem mang NN doi moi nhat tu dau (GPU tich hop DirectML, 15 giay moi nuoc, tham so nhu luc sinh du lieu).
rem Space = tam dung / tiep tuc. Doi mang: sua duong dan --model ben duoi.
start "" "D:\chess_variant\gui\build\windows\x64\runner\Release\fairyzero_gui.exe" --engine "D:\chess_variant\custom_engine\build-dml\custom_engine.exe" --model "D:\chess_variant\models\gen35.onnx" --provider dml --movetime 15000 --self-play