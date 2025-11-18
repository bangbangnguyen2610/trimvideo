# Video Transcription & Meeting Summary Tool 🎙️🤖

Script Python tự động chuyển đổi video cuộc họp thành transcript (gỡ băng) và tóm tắt nội dung với Gemini AI.

## ✨ Tính năng

### 🎬 Script đơn giản - `convert_simple.py`
- Convert MP4 → MP3
- Cắt thành các đoạn 25 phút
- Không cần API key

### 🤖 Script với AI - `convert_with_gemini.py` (Khuyên dùng)
- Convert MP4 → MP3
- Cắt thành các đoạn 25 phút
- **Bước 1**: Tự động transcript (gỡ băng) theo chuẩn Clean Verbatim
- **Bước 2**: Tóm tắt cuộc họp và tạo Action Plan
- **Bước 3**: Upload transcript và summary lên Supabase
- Sử dụng Gemini AI 2.5 Flash

### ⚡ Script tự động - `auto_convert.py` (Tiện lợi nhất)
- Tự động tìm file MP4 mới nhất trong thư mục Downloads
- Không cần nhập đường dẫn file
- Gọi `convert_with_gemini.py` để xử lý tự động
- Upload kết quả lên Supabase

## 📋 Yêu cầu hệ thống

### 1. Cài đặt ffmpeg

**Windows:**
```bash
winget install ffmpeg
```

Hoặc tải từ: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg
```

### 2. Cài đặt thư viện Python

**Cho script đơn giản:**
```bash
# Chỉ cần ffmpeg, không cần thư viện Python
```

**Cho script với Gemini AI:**
```bash
pip install google-generativeai supabase
```

## 🚀 Cách sử dụng

### Script đơn giản (Không có AI)

```bash
python convert_simple.py "path/to/video.mp4"
```

### Script với Gemini AI (Khuyên dùng)

**Bước 1:** Cấu hình API key

Mở file `convert_with_gemini.py` và thay thế API key của bạn:

```python
GEMINI_API_KEY = "YOUR_API_KEY_HERE"
```

Lấy API key miễn phí tại: https://makersuite.google.com/app/apikey

**Bước 2:** Chạy script

```bash
python convert_with_gemini.py "path/to/video.mp4"
```

Hoặc chạy và nhập đường dẫn khi được hỏi:

```bash
python convert_with_gemini.py
```

### Script tự động (Tiện lợi nhất)

**Bước 1:** Cấu hình thư mục tìm kiếm

Mở file `auto_convert.py` và sửa đường dẫn thư mục:

```python
DOWNLOAD_FOLDER = r"C:\Users\admin\Downloads\Tổng hợp MM"
```

**Bước 2:** Chạy script

```bash
python auto_convert.py
```

Script sẽ:
1. Tự động tìm file MP4 mới nhất trong thư mục
2. Convert, transcribe, summary và upload lên Supabase
3. Không cần nhập đường dẫn file

## 📁 Kết quả

### Script đơn giản
```
video_name_output/
├── video_name.mp3              # File MP3 gốc
└── segments/
    ├── video_name_part01.mp3   # Đoạn 1 (25 phút)
    ├── video_name_part02.mp3   # Đoạn 2 (25 phút)
    └── ...
```

### Script với Gemini AI
```
video_name_output/
├── video_name.mp3                      # File MP3 gốc
├── segments/
│   ├── video_name_part01.mp3          # Đoạn 1 (25 phút)
│   ├── video_name_part02.mp3          # Đoạn 2 (25 phút)
│   └── ...
├── video_name_FULL_TRANSCRIPT.txt     # Gỡ băng đầy đủ (Clean Verbatim)
└── video_name_SUMMARY.txt             # Tóm tắt & Action Plan
```

## 📝 Format Transcript (Clean Verbatim)

Transcript được gỡ băng theo chuẩn Clean Verbatim với các quy tắc:

- ✅ Loại bỏ từ đệm, từ rác (à, ờ, ừm, hừm...)
- ✅ Loại bỏ âm thanh không phải lời nói ([ho], [cười]...)
- ✅ Sửa lỗi lặp từ khi người nói tự sửa
- ✅ Định danh người nói chính xác
- ✅ Thuật ngữ chuyên ngành chính xác

**Ví dụ:**
```
Anh Thiện: Nội dung về kênh online chúng ta cần tăng cường.

Phương Anh: Em đồng ý. Doanh số của ngành hàng Peri trên sàn đang tăng.

Anh Minh: Bên anh đang check lại model đó.
```

## 📊 Format Summary

File summary bao gồm:

- 🗣️ Chủ đề cuộc họp
- 📌 Các vấn đề chính được thảo luận
- ✅ Các quyết định & thống nhất
- ⚠️ Các rủi ro / Trở ngại được nêu
- ❓ Các vấn đề còn tồn đọng / Cần làm rõ
- 📋 Kế Hoạch Hành Động (Todo) với bảng phân công

## ⚙️ Tùy chỉnh

### Thay đổi độ dài mỗi đoạn

Mặc định: **25 phút** (1500 giây)

Để thay đổi, sửa tham số `segment_duration` khi gọi hàm `split_audio()`:

```python
# 10 phút
split_audio(mp3_path, segment_duration=600, output_folder=output_folder)

# 20 phút
split_audio(mp3_path, segment_duration=1200, output_folder=output_folder)

# 30 phút
split_audio(mp3_path, segment_duration=1800, output_folder=output_folder)
```

### Tùy chỉnh danh sách người tham gia

Sửa trong `TRANSCRIPT_PROMPT` ở file `convert_with_gemini.py`:

```python
Thành viên tham gia (Sử dụng tên này để định danh người nói):
- Sếp
- Anh Thiện (Lead MKT)
- Phương Anh (Lead sales online)
...
```

## 🛠️ Các công cụ bổ trợ

### `test_gemini_models.py`
Kiểm tra danh sách models Gemini có sẵn với API key của bạn:

```bash
python test_gemini_models.py
```

## 💡 Lưu ý

- Gemini API miễn phí có giới hạn quota
- Mỗi đoạn 25 phút tốn ~1-2 phút để transcript
- File transcript và summary được lưu dạng UTF-8
- Gemini 2.5 Flash hỗ trợ audio/video transcription tốt

## 🤝 Đóng góp

Mọi đóng góp đều được chào đón! Hãy tạo Pull Request hoặc Issue nếu có ý tưởng cải tiến.

## 📄 License

MIT License
