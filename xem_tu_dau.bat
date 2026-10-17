@echo off
rem Xem mang NN doi moi nhat tu dau (GPU tich hop DirectML, 15 giay moi nuoc, tham so nhu luc sinh du lieu).
rem Space = tam dung / tiep tuc. Doi mang: sua duong dan --model ben duoi.
rem --temperature 0.5 --temp-cutoff 0 = chon nuoc voi nhiet do 0.5 suot ca van.
rem Bo hai co nay = dung nhu sinh du lieu (nhiet do 1.0 trong 32 nua nuoc dau, sau do nuoc tot nhat).
start "" "D:\chess_variant\gui\build\windows\x64\runner\Release\fairyzero_gui.exe" --engine "D:\chess_variant\custom_engine\build-dml\custom_engine.exe" --model "D:\chess_variant\models\gen79.onnx" --provider dml --movetime 15000 --self-play --temperature 0.5 --temp-cutoff 0