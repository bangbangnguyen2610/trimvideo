#!/usr/bin/env python3
"""
Script convert MP4 sang MP3, cắt thành các đoạn 25 phút, và tự động gửi lên Gemini để transcribe
"""

import os
import sys
import subprocess
import time
from pathlib import Path
import google.generativeai as genai
from supabase import create_client, Client

# Cấu hình Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyAWQEyRsWktylLDrejCxni43DBqEdrG_Ew')
genai.configure(api_key=GEMINI_API_KEY)

# Cấu hình Supabase
SUPABASE_URL = "https://yaawmtegpzhcqmgimvbn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlhYXdtdGVncHpoY3FtZ2ltdmJuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM0NDkwNTUsImV4cCI6MjA3OTAyNTA1NX0.qLLUaUg6s1VYxRbjNU-AXwSzy67VAdkhhtWntCLqqAQ"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Prompt cho Gemini - TRANSCRIPT CLEAN VERBATIM
TRANSCRIPT_PROMPT = """Nhiệm vụ: Gỡ băng file ghi âm cuộc họp theo tiêu chuẩn "Clean Verbatim" (Gỡ băng sạch).

Bối cảnh:

Chủ đề: Cuộc họp của [Tên bộ phận] về [Chủ đề cuộc họp].
Nội dung: Chứa nhiều thuật ngữ chuyên ngành bán lẻ ICT và tên riêng (sản phẩm, đối tác).

QUY TẮC BẮT BUỘC (1): ĐỘ CHÍNH XÁC THUẬT NGỮ

Đây là yêu cầu quan trọng nhất. Phải đảm bảo độ chính xác tuyệt đối cho các tên riêng và thuật ngữ sau:

Thành viên tham gia (Sử dụng tên này để định danh người nói):
- Sếp
- Anh Thiện (Lead MKT)
- Phương Anh (Lead sales online)
- Băng (report số)
- Anh Đạt (PM ngành hàng PC)
- Anh Tùng (PM ngành hàng Màn hình)
- Anh Viên (PM ngành laptop)
- Anh Minh (PM ngành Peri)
- Huyền (PM ngành Peri)
(Nếu có người nói khác không trong danh sách, dùng "Người nói X")

Thuật ngữ chuyên ngành (Viết chính xác):
- PC
- Laptop
- Màn hình
- Peri (viết tắt của Peripherals - phụ kiện)
- offline
- online
- sàn (chỉ Sàn TMĐT)

QUY TẮC BẮT BUỘC (2): XỬ LÝ NỘI DUNG (CLEAN VERBATIM)

- LOẠI BỎ: Tất cả từ đệm, từ rác (ví dụ: à, ờ, ừm, hừm, á, kiểu như, nói chung là...).
- LOẠI BỎ: Các âm thanh không phải lời nói (ví dụ: [ho], [hắng giọng], [cười]). Không cần ghi nhận.
- SỬA LỖI: Loại bỏ các từ lặp lại khi người nói tự sửa, tự lặp (ví dụ: "Tôi... tôi tôi tôi nghĩ là" -> ghi "Tôi nghĩ là").

QUY TẮC BẮT BUỘC (3): ĐỊNH DẠNG ĐẦU RA

Đây là quy tắc nghiêm ngặt để đảm bảo đầu ra đúng chuẩn.

- Không có nội dung thừa: Chỉ xuất kết quả gỡ băng. TUYỆT ĐỐI không thêm lời chào, lời giới thiệu hay ghi chú ngoài lề (ví dụ: "Chào bạn", "Dưới đây là...").
- Định dạng Markdown: Toàn bộ nội dung phải ở dạng Markdown.
- Định danh người nói: Bắt đầu mỗi lượt nói bằng tên người nói (lấy từ danh sách trên) và dấu hai chấm (ví dụ: Anh Thiện:).
- TÁCH DÒNG: LUÔN LUÔN xuống dòng cho mỗi lượt nói mới. (Sang người khác nói)

VÍ DỤ MẪU (BẮT BUỘC TUÂN THỦ):

Anh Thiện: Nội dung về kênh online chúng ta cần...

Phương Anh: Em đồng ý. Doanh số của ngành hàng Peri trên sàn đang tăng.

Anh Minh: Bên anh đang check lại model đó.

Hãy gỡ băng file audio/video này theo đúng format trên."""

# Prompt cho Summary (Bước 2)
SUMMARY_PROMPT = """Vai trò: Bạn là một trợ lý phân tích và tóm tắt cuộc họp chuyên nghiệp, có khả năng trích xuất thông tin quan trọng từ bản ghi cuộc họp thô.

Mục tiêu: Phân tích bản ghi cuộc họp dưới đây để tạo ra một bản tóm tắt cuộc họp (Meeting Summary) đầy đủ và một Kế Hoạch Hành Động (Action Plan) chi tiết.

RÀNG BUỘC QUAN TRỌNG: Tuyệt đối không được đưa ra bất kỳ đường dẫn, URL, file đính kèm, tham chiếu đến tên file (ví dụ: 29_09_Weekly meet... hoặc các định dạng như .pdf, .docx), hoặc các liên kết (🔗) nào trong phần trả lời.

Đầu ra chỉ là nội dung text theo định dạng yêu cầu.

Định dạng đầu ra BẮT BUỘC:

1. Tóm Tắt & Kế Hoạch Hành Động

2. Trình Bày Chi Tiết

🗣️ Chủ đề cuộc họp: [Tự điền dựa trên nội dung Transcript]

📌 Các vấn đề chính được thảo luận:

[Vấn đề 1]

[Vấn đề 2]

[Vấn đề 3]...

✅ Các quyết định & thống nhất:

[Quyết định/Thống nhất 1]

[Quyết định/Thống nhất 2]

[Quyết định/Thống nhất 3]...

⚠️ Các rủi ro / Trở ngại được nêu:

[Rủi ro/Trở ngại 1]

[Rủi ro/Trở ngại 2]

[Rủi ro/Trở ngại 3]...

❓ Các vấn đề còn tồn đọng / Cần làm rõ:

[Vấn đề còn tồn đọng 1]

[Vấn đề còn tồn đọng 2]

[Vấn đề còn tồn đọng 3]...

📋 Kế Hoạch Hành Động (Todo):

Hạng mục (Task)	Người phụ trách (Owner)	Deadline (Hạn chót)
[Hành động 1]	[Người A]	[Ngày/Thời gian]
[Hành động 2]	[Người B]	[Ngày/Thời gian]
[Hành động 3]	[Người C]	[Ngày/Thời gian]
...	...	...

Hãy phân tích transcript và trả về kết quả theo đúng format trên."""


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
    """Cắt audio thành các đoạn và trả về danh sách file"""
    try:
        # Tạo thư mục segments
        segments_folder = os.path.join(output_folder, "segments")
        os.makedirs(segments_folder, exist_ok=True)

        # Lấy độ dài audio
        duration = get_video_duration(audio_path)
        if duration is None:
            print("✗ Không thể lấy thông tin độ dài audio")
            return []

        # Tính số đoạn
        num_segments = int(duration / segment_duration) + (1 if duration % segment_duration > 0 else 0)

        print(f"\nĐang cắt thành {num_segments} đoạn (mỗi đoạn ~25 phút)...")

        audio_name = Path(audio_path).stem
        segment_files = []

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
                segment_files.append(segment_path)
            else:
                print(f"✗ Lỗi tạo đoạn {i+1}")

        print(f"\n✓ Hoàn thành! Các đoạn đã lưu trong: {segments_folder}")
        return segment_files

    except Exception as e:
        print(f"✗ Lỗi: {str(e)}")
        return []


def upload_to_gemini(file_path):
    """Upload file lên Gemini và trả về file object"""
    try:
        print(f"  📤 Đang upload file: {Path(file_path).name}...")

        uploaded_file = genai.upload_file(file_path)

        # Đợi file được xử lý
        while uploaded_file.state.name == "PROCESSING":
            print("  ⏳ Đang xử lý file...")
            time.sleep(2)
            uploaded_file = genai.get_file(uploaded_file.name)

        if uploaded_file.state.name == "FAILED":
            raise ValueError(f"Upload thất bại: {uploaded_file.state.name}")

        print(f"  ✓ Upload thành công!")
        return uploaded_file

    except Exception as e:
        print(f"  ✗ Lỗi upload: {str(e)}")
        return None


def transcribe_with_gemini(uploaded_file):
    """Gửi file đã upload lên Gemini để transcribe và phân tích"""
    try:
        print(f"  🤖 Đang gửi cho Gemini phân tích...")

        # Sử dụng model Gemini 2.5 Flash (hỗ trợ audio/video, nhanh và hiệu quả)
        model = genai.GenerativeModel("models/gemini-2.5-flash")

        # Gửi yêu cầu transcribe với prompt
        response = model.generate_content(
            [uploaded_file, TRANSCRIPT_PROMPT],
            request_options={"timeout": 600}  # Timeout 10 phút
        )

        print(f"  ✓ Phân tích hoàn thành!")
        return response.text

    except Exception as e:
        print(f"  ✗ Lỗi phân tích: {str(e)}")
        return None


def process_segments_with_gemini(segment_files, output_folder):
    """BƯỚC 1: Transcript tất cả các đoạn MP3"""
    transcripts = []

    print(f"\n{'='*70}")
    print(f"[5/6] BƯỚC 1: GỞ BĂNG (TRANSCRIPT) CÁC ĐOẠN AUDIO")
    print(f"{'='*70}\n")

    for idx, segment_file in enumerate(segment_files, 1):
        print(f"📋 Đang gỡ băng đoạn {idx}/{len(segment_files)}: {Path(segment_file).name}")

        # Upload file
        uploaded_file = upload_to_gemini(segment_file)
        if uploaded_file is None:
            print(f"  ⏭️  Bỏ qua đoạn này\n")
            continue

        # Transcribe
        transcript = transcribe_with_gemini(uploaded_file)
        if transcript is None:
            print(f"  ⏭️  Bỏ qua đoạn này\n")
            continue

        # Lưu kết quả
        transcripts.append({
            'segment': Path(segment_file).name,
            'content': transcript
        })

        print(f"  ✓ Hoàn thành gỡ băng đoạn {idx}\n")

        # Xóa file đã upload trên Gemini để tiết kiệm quota
        try:
            genai.delete_file(uploaded_file.name)
        except:
            pass

    return transcripts


def save_full_transcript(transcripts, output_folder, video_name):
    """Lưu toàn bộ transcript vào 1 file"""
    transcript_file = os.path.join(output_folder, f"{video_name}_FULL_TRANSCRIPT.txt")

    with open(transcript_file, 'w', encoding='utf-8') as f:
        f.write(f"GỞ BĂNG CUỘC HỌP - {video_name}\n")
        f.write("="*70 + "\n\n")

        for idx, item in enumerate(transcripts, 1):
            if idx > 1:
                f.write(f"\n{'─'*70}\n\n")
            f.write(item['content'])
            f.write("\n")

    print(f"\n✓ Đã lưu transcript tổng hợp: {transcript_file}")
    return transcript_file


def summarize_transcript(transcript_file):
    """BƯỚC 2: Summary file transcript"""
    print(f"\n{'='*70}")
    print(f"[6/6] BƯỚC 2: TÓM TẮT VÀ PHÂN TÍCH TRANSCRIPT")
    print(f"{'='*70}\n")

    try:
        # Đọc file transcript
        print(f"📖 Đang đọc file transcript...")
        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript_content = f.read()

        print(f"🤖 Đang gửi cho Gemini tóm tắt...")

        # Sử dụng Gemini để summary
        model = genai.GenerativeModel("models/gemini-2.5-flash")

        response = model.generate_content(
            [SUMMARY_PROMPT, f"\n\nTRANSCRIPT:\n{transcript_content}"],
            request_options={"timeout": 600}
        )

        print(f"✓ Tóm tắt hoàn thành!")
        return response.text

    except Exception as e:
        print(f"✗ Lỗi khi tóm tắt: {str(e)}")
        return None


def save_summary(summary_content, output_folder, video_name):
    """Lưu file summary"""
    summary_file = os.path.join(output_folder, f"{video_name}_SUMMARY.txt")

    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"TÓM TẮT CUỘC HỌP - {video_name}\n")
        f.write("="*70 + "\n\n")
        f.write(summary_content)

    print(f"✓ Đã lưu tóm tắt: {summary_file}")
    return summary_file


def upload_to_supabase(video_name, transcript_content, summary_content):
    """Upload transcript và summary lên Supabase"""
    print(f"\n{'='*70}")
    print(f"ĐANG UPLOAD LÊN SUPABASE")
    print(f"{'='*70}\n")

    try:
        print(f"📤 Đang upload dữ liệu lên Supabase...")

        # Tạo data để insert
        data = {
            "video_name": video_name,
            "transcript_content": transcript_content,
            "summary_content": summary_content
        }

        # Insert vào Supabase
        response = supabase.table("meeting_transcripts").insert(data).execute()

        print(f"✓ Upload thành công lên Supabase!")
        print(f"  Record ID: {response.data[0]['id'] if response.data else 'N/A'}")
        return True

    except Exception as e:
        print(f"✗ Lỗi khi upload lên Supabase: {str(e)}")
        return False


def main():
    print("=" * 70)
    print("SCRIPT CONVERT VIDEO & TỰ ĐỘNG PHÂN TÍCH VỚI GEMINI AI")
    print("=" * 70)

    # Kiểm tra ffmpeg
    print("\n[1/5] Kiểm tra ffmpeg...")
    if not check_ffmpeg():
        print("✗ Không tìm thấy ffmpeg!")
        print("\nVui lòng cài đặt ffmpeg:")
        print("1. Tải từ: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip")
        print("2. Giải nén và thêm vào PATH")
        print("3. Hoặc chạy: winget install ffmpeg")
        return

    print("✓ ffmpeg đã sẵn sàng")

    # Lấy đường dẫn video
    print("\n[2/5] Lấy đường dẫn video...")
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
    print(f"\n[3/5] Convert sang MP3...")
    mp3_path = convert_to_mp3(video_path, output_folder)

    if mp3_path is None:
        print("✗ Không thể convert")
        return

    # Cắt thành các đoạn
    print(f"\n[4/5] Cắt thành các đoạn 25 phút...")
    segment_files = split_audio(mp3_path, segment_duration=1500, output_folder=output_folder)

    if not segment_files:
        print("✗ Không có đoạn nào được tạo")
        return

    # BƯỚC 1: Gỡ băng (Transcript) các đoạn MP3
    transcripts = process_segments_with_gemini(segment_files, output_folder)

    if not transcripts:
        print("✗ Không có transcript nào được tạo")
        return

    # Lưu toàn bộ transcript vào 1 file
    full_transcript_file = save_full_transcript(transcripts, output_folder, video_name)

    # Đọc nội dung transcript để upload
    with open(full_transcript_file, 'r', encoding='utf-8') as f:
        transcript_content = f.read()

    # BƯỚC 2: Summary file transcript
    summary_content = summarize_transcript(full_transcript_file)

    if summary_content:
        save_summary(summary_content, output_folder, video_name)
    else:
        print("⚠️ Không thể tạo summary, nhưng transcript vẫn được lưu")
        summary_content = ""  # Set empty nếu không có summary

    # BƯỚC 3: Upload lên Supabase
    upload_to_supabase(video_name, transcript_content, summary_content)

    print("\n" + "=" * 70)
    print("HOÀN THÀNH!")
    print("=" * 70)
    print(f"\n📂 Tất cả file đã lưu trong: {output_folder}")
    print(f"   - File MP3 gốc")
    print(f"   - Các đoạn MP3 (trong thư mục segments/)")
    print(f"   - {video_name}_FULL_TRANSCRIPT.txt (Gỡ băng đầy đủ)")
    print(f"   - {video_name}_SUMMARY.txt (Tóm tắt & Action Plan)")
    print(f"\n☁️  Đã upload lên Supabase Database")


if __name__ == "__main__":
    main()
