# Arena GIẢ (có A_GEN / B_GEN / lay_mang như ô thật): in dòng FZ_ARENA
import time
GAMES = 100
PARALLEL = 16
SECS = 0
A_GEN = GEN_NEXT
B_GEN = GEN_CURRENT
print(f"=== ARENA: A=/content/gen{A_GEN}.fzw  vs  B=/content/gen{B_GEN}.fzw")
time.sleep(3)
print(f"FZ_ARENA W={GAMES // 2} D=0 L={GAMES - GAMES // 2} N={GAMES}")
