import os
import sys

# 檢查是否為 PyInstaller 打包後執行的環境
# 若是，使用內部臨時資料夾；否則使用目前所在目錄
if getattr(sys, 'frozen', False):           # 判斷是否為打包後的執行檔
    base_path = sys._MEIPASS                # PyInstaller 打包後的臨時資料夾路徑
else:
    base_path = os.path.abspath(".")        # 當前執行檔所在的目錄
    
# 設定 FFmpeg 執行檔的路徑（支援打包後的相對路徑）
FFMPEG_PATH = os.path.join(base_path, "ffmpeg-master-latest-win64-gpl-shared", "bin", "ffmpeg.exe")