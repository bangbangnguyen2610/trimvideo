#!/usr/bin/env python3
"""
Script đơn giản convert MP4 sang MP3 và cắt thành các đoạn 25 phút
Sử dụng ffmpeg trực tiếp
"""

import os
import sys
import subprocess
from pathlib import Path


def check_ffmpeg():
    """Kiểm tra ffmpeg đã cài chưa"""
    try:
        result = subprocess.run(['ffmpeg', '-version'],
                              capture_output=True,
                              text=True,
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_video_duration(video_path):
    """Lấy độ dài video (giây)"""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]

    result = subprocess.run(cmd,
                           capture_output=True,
                           text=True,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

    try:
        return float(result.stdout.strip())
    except:
        return None


def convert_to_mp3(video_path, output_folder="output"):
    """Convert MP4 sang MP3"""
    try:
        # Tạo thư mục output
        os.makedirs(output_folder, exist_ok=True)

        # Tên file output
        video_name = Path(video_path).stem
        mp3_path = os.path.join(output_folder, f"{video_name}.mp3")

        print(f"Đang convert sang MP3...")

        # Lệnh ffmpeg
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vn',  # Không copy video
            '-acodec', 'libmp3lame',
            '-q:a', '2',  # Chất lượng cao
            '-y',  # Overwrite nếu file đã tồn tại
            mp3_path
        ]

        # Chạy ffmpeg
        result = subprocess.run(cmd,
                               capture_output=True,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

        if result.returncode == 0:
            print(f"✓ Convert thành công: {mp3_path}")
            return mp3_path
        else:
            print(f"✗ Lỗi khi convert: {result.stderr.decode('utf-8', errors='ignore')}")
            return None

    except Exception as e:
        print(f"✗ Lỗi: {str(e)}")
        return None


def split_audio(audio_path, segment_duration=1500, output_folder="output"):
    """Cắt audio thành các đoạn"""
    try:
        # Tạo thư mục segments
        segments_folder = os.path.join(output_folder, "segments")
        os.makedirs(segments_folder, exist_ok=True)

        # Lấy độ dài audio
        duration = get_video_duration(audio_path)
        if duration is None:
            print("✗ Không thể lấy thông tin độ dài audio")
            return

        # Tính số đoạn
        num_segments = int(duration / segment_duration) + (1 if duration % segment_duration > 0 else 0)

        print(f"\nĐang cắt thành {num_segments} đoạn (mỗi đoạn ~25 phút)...")

        audio_name = Path(audio_path).stem

        # Cắt từng đoạn
        for i in range(num_segments):
            start_time = i * segment_duration
            segment_path = os.path.join(segments_folder, f"{audio_name}_part{i+1:02d}.mp3")

            cmd = [
                'ffmpeg',
                '-i', audio_path,
                '-ss', str(start_time),
                '-t', str(segment_duration),
                '-acodec', 'copy',  # Copy codec, không encode lại
                '-y',
                segment_path
            ]

            result = subprocess.run(cmd,
                                   capture_output=True,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

            if result.returncode == 0:
                print(f"✓ Đã tạo đoạn {i+1}/{num_segments}: {segment_path}")
            else:
                print(f"✗ Lỗi tạo đoạn {i+1}")

        print(f"\n✓ Hoàn thành! Các đoạn đã lưu trong: {segments_folder}")

    except Exception as e:
        print(f"✗ Lỗi: {str(e)}")


def main():
    print("=" * 70)
    print("SCRIPT CONVERT MP4 SANG MP3 VÀ CẮT THÀNH CÁC ĐOẠN 25 PHÚT")
    print("=" * 70)

    # Kiểm tra ffmpeg
    print("\n[1/4] Kiểm tra ffmpeg...")
    if not check_ffmpeg():
        print("✗ Không tìm thấy ffmpeg!")
        print("\nVui lòng cài đặt ffmpeg:")
        print("1. Tải từ: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip")
        print("2. Giải nén và thêm vào PATH")
        print("3. Hoặc chạy: winget install ffmpeg")
        return

    print("✓ ffmpeg đã sẵn sàng")

    # Lấy đường dẫn video
    print("\n[2/4] Lấy đường dẫn video...")
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
    else:
        video_path = input("\nNhập đường dẫn file MP4: ").strip().strip('"')

    # Kiểm tra file
    if not os.path.exists(video_path):
        print(f"✗ Không tìm thấy file: {video_path}")
        return

    if not video_path.lower().endswith('.mp4'):
        print("✗ File không phải MP4")
        return

    print(f"✓ Tìm thấy file: {video_path}")

    # Tạo folder output theo tên video
    video_name = Path(video_path).stem
    video_folder = Path(video_path).parent
    output_folder = os.path.join(video_folder, f"{video_name}_output")

    print(f"✓ Thư mục output: {output_folder}")

    # Convert sang MP3
    print(f"\n[3/4] Convert sang MP3...")
    mp3_path = convert_to_mp3(video_path, output_folder)

    if mp3_path is None:
        print("✗ Không thể convert")
        return

    # Cắt thành các đoạn
    print(f"\n[4/4] Cắt thành các đoạn 25 phút...")
    split_audio(mp3_path, segment_duration=1500, output_folder=output_folder)

    print("\n" + "=" * 70)
    print("HOÀN THÀNH!")
    print("=" * 70)


if __name__ == "__main__":
    main()
