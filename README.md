# Video Converter Script

Script Python để convert file MP4 sang MP3 và cắt thành các đoạn 15 phút.

## Yêu cầu

Cài đặt thư viện cần thiết:

```bash
pip install moviepy
```

**Lưu ý:** `moviepy` yêu cầu `ffmpeg` để hoạt động. Nếu chưa có ffmpeg, `moviepy` sẽ tự động tải về khi chạy lần đầu.

## Cách sử dụng

### Cách 1: Truyền đường dẫn file qua command line

```bash
python video_converter.py "path/to/your/video.mp4"
```

### Cách 2: Chạy script và nhập đường dẫn khi được yêu cầu

```bash
python video_converter.py
```

Sau đó nhập đường dẫn file MP4 khi được hỏi.

## Kết quả

Script sẽ tạo:

1. **File MP3 đầy đủ** trong thư mục `output/`
   - Ví dụ: `output/video_name.mp3`

2. **Các đoạn 15 phút** trong thư mục `output/segments/`
   - Ví dụ:
     - `output/segments/video_name_part01.mp3`
     - `output/segments/video_name_part02.mp3`
     - `output/segments/video_name_part03.mp3`
     - ...

## Tùy chỉnh

Để thay đổi độ dài mỗi đoạn, sửa tham số `segment_duration` trong hàm `split_audio_into_segments()`:

- Mặc định: `900` giây (15 phút)
- 10 phút: `600` giây
- 20 phút: `1200` giây
- 30 phút: `1800` giây

## Ví dụ

```bash
python video_converter.py "C:\Videos\my_video.mp4"
```

Kết quả:
```
output/
  ├── my_video.mp3
  └── segments/
      ├── my_video_part01.mp3
      ├── my_video_part02.mp3
      └── my_video_part03.mp3
```
