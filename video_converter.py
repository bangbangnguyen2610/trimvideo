#!/usr/bin/env python3
"""
Script convert MP4 sang MP3 và cắt thành các đoạn 15 phút
"""

import os
import sys
from moviepy.editor import VideoFileClip, AudioFileClip
from pathlib import Path


def convert_mp4_to_mp3(video_path, output_folder="output"):
    """
    Convert file MP4 sang MP3

    Args:
        video_path: Đường dẫn đến file MP4
        output_folder: Thư mục lưu file output

    Returns:
        Đường dẫn đến file MP3 đã convert
    """
    try:
        # Tạo thư mục output nếu chưa có
        os.makedirs(output_folder, exist_ok=True)

        # Load video
        video = VideoFileClip(video_path)

        # Lấy tên file không có extension
        video_name = Path(video_path).stem

        # Đường dẫn file MP3 output
        mp3_path = os.path.join(output_folder, f"{video_name}.mp3")

        # Extract audio và lưu thành MP3
        video.audio.write_audiofile(mp3_path, codec='mp3')

        # Đóng video để giải phóng tài nguyên
        video.close()

        print(f"✓ Đã convert thành công: {mp3_path}")
        return mp3_path

    except Exception as e:
        print(f"✗ Lỗi khi convert video: {str(e)}")
        return None


def split_audio_into_segments(audio_path, segment_duration=900, output_folder="output"):
    """
    Cắt file audio thành nhiều đoạn

    Args:
        audio_path: Đường dẫn đến file audio
        segment_duration: Độ dài mỗi đoạn (giây), mặc định 900s = 15 phút
        output_folder: Thư mục lưu các đoạn
    """
    try:
        # Tạo thư mục output nếu chưa có
        segments_folder = os.path.join(output_folder, "segments")
        os.makedirs(segments_folder, exist_ok=True)

        # Load audio
        audio = AudioFileClip(audio_path)

        # Tính tổng thời gian
        total_duration = audio.duration

        # Lấy tên file không có extension
        audio_name = Path(audio_path).stem

        # Số lượng đoạn
        num_segments = int(total_duration / segment_duration) + (1 if total_duration % segment_duration > 0 else 0)

        print(f"\nĐang cắt file thành {num_segments} đoạn (mỗi đoạn ~15 phút)...")

        # Cắt thành từng đoạn
        for i in range(num_segments):
            start_time = i * segment_duration
            end_time = min((i + 1) * segment_duration, total_duration)

            # Tạo segment
            segment = audio.subclip(start_time, end_time)

            # Tên file output
            segment_path = os.path.join(segments_folder, f"{audio_name}_part{i+1:02d}.mp3")

            # Lưu segment
            segment.write_audiofile(segment_path, codec='mp3')

            # Đóng segment
            segment.close()

            print(f"✓ Đã tạo đoạn {i+1}/{num_segments}: {segment_path}")

        # Đóng audio
        audio.close()

        print(f"\n✓ Hoàn thành! Đã cắt thành {num_segments} đoạn trong thư mục: {segments_folder}")

    except Exception as e:
        print(f"✗ Lỗi khi cắt audio: {str(e)}")


def main():
    """
    Hàm main
    """
    print("=" * 60)
    print("SCRIPT CONVERT MP4 SANG MP3 VÀ CẮT THÀNH CÁC ĐOẠN 15 PHÚT")
    print("=" * 60)

    # Lấy đường dẫn file video từ command line hoặc input
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
    else:
        video_path = input("\nNhập đường dẫn file MP4: ").strip().strip('"')

    # Kiểm tra file có tồn tại không
    if not os.path.exists(video_path):
        print(f"✗ Không tìm thấy file: {video_path}")
        return

    # Kiểm tra extension
    if not video_path.lower().endswith('.mp4'):
        print("✗ File không phải là MP4")
        return

    print(f"\n📹 Đang xử lý file: {video_path}\n")

    # Bước 1: Convert MP4 sang MP3
    print("BƯỚC 1: Convert MP4 sang MP3...")
    mp3_path = convert_mp4_to_mp3(video_path)

    if mp3_path is None:
        print("✗ Không thể tiếp tục do lỗi convert")
        return

    # Bước 2: Cắt MP3 thành các đoạn 15 phút
    print("\nBƯỚC 2: Cắt file thành các đoạn 15 phút...")
    split_audio_into_segments(mp3_path, segment_duration=900)

    print("\n" + "=" * 60)
    print("HOÀN THÀNH!")
    print("=" * 60)


if __name__ == "__main__":
    main()
