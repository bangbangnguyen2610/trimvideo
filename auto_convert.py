#!/usr/bin/env python3
"""
Script tự động tìm file MP4 mới nhất trong thư mục và xử lý
Gọi convert_with_gemini.py để transcribe và summary
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Fix encoding for Vietnamese
sys.stdout.reconfigure(encoding='utf-8')

# Thư mục cần tìm file MP4
DOWNLOAD_FOLDER = r"C:\Users\admin\Downloads\Tổng hợp MM"


def find_newest_mp4(folder_path):
    """Tìm file MP4 mới nhất trong thư mục"""
    try:
        # Kiểm tra thư mục có tồn tại không
        if not os.path.exists(folder_path):
            print(f"✗ Không tìm thấy thư mục: {folder_path}")
            return None

        # Tìm tất cả file MP4
        mp4_files = []
        for file in os.listdir(folder_path):
            if file.lower().endswith('.mp4'):
                file_path = os.path.join(folder_path, file)
                # Lấy thời gian sửa đổi
                mtime = os.path.getmtime(file_path)
                mp4_files.append((file_path, mtime))

        # Kiểm tra có file MP4 nào không
        if not mp4_files:
            print(f"✗ Không tìm thấy file MP4 nào trong: {folder_path}")
            return None

        # Sắp xếp theo thời gian (mới nhất trước)
        mp4_files.sort(key=lambda x: x[1], reverse=True)

        # File mới nhất
        newest_file = mp4_files[0][0]
        newest_time = datetime.fromtimestamp(mp4_files[0][1])

        print(f"✓ Tìm thấy file MP4 mới nhất:")
        print(f"  - File: {os.path.basename(newest_file)}")
        print(f"  - Thời gian: {newest_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  - Đường dẫn: {newest_file}")

        return newest_file

    except Exception as e:
        print(f"✗ Lỗi khi tìm file: {str(e)}")
        return None


def main():
    print("=" * 70)
    print("TỰ ĐỘNG XỬ LÝ VIDEO MP4 MỚI NHẤT")
    print("=" * 70)

    # Tìm file MP4 mới nhất
    print(f"\nTìm file MP4 mới nhất trong thư mục...")
    print(f"Thư mục: {DOWNLOAD_FOLDER}")

    video_path = find_newest_mp4(DOWNLOAD_FOLDER)

    if video_path is None:
        print("\n✗ Không thể tiếp tục do không tìm thấy file MP4")
        return

    print(f"\n{'=' * 70}")
    print("GỌI CONVERT_WITH_GEMINI.PY ĐỂ XỬ LÝ FILE")
    print("=" * 70)

    # Gọi script convert_with_gemini.py với đường dẫn file vừa tìm được
    script_dir = os.path.dirname(os.path.abspath(__file__))
    convert_script = os.path.join(script_dir, "convert_with_gemini.py")

    # Chạy script với Python
    result = subprocess.run(
        [sys.executable, convert_script, video_path],
        capture_output=False  # Hiển thị output trực tiếp
    )

    if result.returncode == 0:
        print("\n" + "=" * 70)
        print("HOÀN THÀNH TẤT CẢ!")
        print("=" * 70)
    else:
        print("\n✗ Có lỗi xảy ra khi xử lý file")


if __name__ == "__main__":
    main()
