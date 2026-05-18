import sys
from PySide6.QtWidgets import QApplication

from src.gui.app_main import AscetAgentMainWindow 
import os
import sys

# Xử lý đường dẫn cho PyInstaller khi đóng gói --onefile
if hasattr(sys, '_MEIPASS'):
    bundle_dir = sys._MEIPASS
    # Ép Windows tìm DLL trong thư mục tạm này
    if hasattr(os, 'add_dll_directory'):
        os.add_dll_directory(bundle_dir)
    # Cập nhật PATH cho chắc ăn
    os.environ['PATH'] = bundle_dir + os.pathsep + os.environ['PATH']

# Bây giờ mới import các module khác
try:
    import faiss
    print("Faiss loaded successfully inside EXE!")
except Exception as e:
    print(f"Faiss load failed: {e}")
    
def main():
    app = QApplication(sys.argv)
    window = AscetAgentMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()