#!/usr/bin/env python3
"""
Gemini Auto-Tagging for Meeting Classification
"""

import os
import sys
import json
import google.generativeai as genai
from typing import Optional, Dict

# Fix encoding for Vietnamese
sys.stdout.reconfigure(encoding='utf-8')

# Gemini API Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyBg-P8MBhJllhisSRxsxPW8nEh-bQtu0w4')
genai.configure(api_key=GEMINI_API_KEY)

# Tagging Prompt
TAGGING_PROMPT = """Bạn là một AI chuyên phân loại cuộc họp. Nhiệm vụ của bạn là đọc summary của cuộc họp và gắn tags phù hợp.

**QUAN TRỌNG**: Chỉ trả về JSON format thuần túy, KHÔNG thêm markdown code blocks (```json), KHÔNG thêm giải thích.

Phân tích summary dưới đây và trả về JSON với 2 fields:

1. **meeting_type** (Loại cuộc họp):
   - "Họp dự án": Nếu cuộc họp thảo luận về một dự án cụ thể với timeline, deliverables, milestones, và có phân công công việc rõ ràng
   - "Họp định kỳ": Nếu là cuộc họp weekly/monthly check-in, status update, review tiến độ chung, không tập trung vào 1 dự án duy nhất

2. **meeting_topic** (Chủ đề chính):
   - "Loyalty": Nếu nội dung liên quan đến chương trình khách hàng thân thiết, tích điểm, ưu đãi thành viên, chăm sóc khách hàng VIP
   - "Membership": Nếu liên quan đến hệ thống thành viên, đăng ký, phân cấp thành viên, quyền lợi membership
   - "Operation": Nếu về vận hành, quy trình nội bộ, logistics, inventory, fulfillment, customer service operations
   - "Business": Nếu về kinh doanh, doanh số, chiến lược bán hàng, marketing, pricing, promotion, revenue
   - "Data": Nếu về phân tích dữ liệu, báo cáo số liệu, metrics, KPIs, analytics, BI, data infrastructure

**LƯU Ý**:
- Nếu summary đề cập nhiều chủ đề, chọn chủ đề chiếm tỷ trọng lớn nhất
- Ưu tiên dựa vào action items và quyết định chính
- Trả về format JSON chính xác như mẫu dưới đây

**Format trả về** (KHÔNG thêm markdown hoặc text khác):
{
  "meeting_type": "Họp dự án",
  "meeting_topic": "Business"
}

---

**SUMMARY CẦN PHÂN TÍCH:**

"""


def analyze_and_tag(summary_content: str) -> Optional[Dict[str, str]]:
    """
    Analyze meeting summary and generate tags using Gemini

    Args:
        summary_content: The meeting summary text

    Returns:
        dict: {
            'meeting_type': str,  # "Họp dự án" hoặc "Họp định kỳ"
            'meeting_topic': str  # "Loyalty" | "Membership" | "Operation" | "Business" | "Data"
        } if successful, None otherwise
    """
    print("🏷️ Analyzing summary for auto-tagging...")

    try:
        # Initialize model
        model = genai.GenerativeModel('models/gemini-2.0-flash-exp')

        # Combine prompt with summary
        full_prompt = TAGGING_PROMPT + summary_content

        # Generate tags
        response = model.generate_content(full_prompt)

        if not response or not response.text:
            print("✗ No response from Gemini")
            return None

        response_text = response.text.strip()

        # Remove markdown code blocks if present (just in case)
        if response_text.startswith('```json'):
            response_text = response_text.replace('```json', '').replace('```', '').strip()
        elif response_text.startswith('```'):
            response_text = response_text.replace('```', '').strip()

        # Parse JSON
        tags = json.loads(response_text)

        # Validate fields
        meeting_type = tags.get('meeting_type')
        meeting_topic = tags.get('meeting_topic')

        if not meeting_type or not meeting_topic:
            print(f"✗ Invalid tags format: {tags}")
            return None

        # Validate values
        valid_types = ["Họp dự án", "Họp định kỳ"]
        valid_topics = ["Loyalty", "Membership", "Operation", "Business", "Data"]

        if meeting_type not in valid_types:
            print(f"⚠️ Invalid meeting_type: {meeting_type}, defaulting to 'Họp định kỳ'")
            meeting_type = "Họp định kỳ"

        if meeting_topic not in valid_topics:
            print(f"⚠️ Invalid meeting_topic: {meeting_topic}, defaulting to 'Business'")
            meeting_topic = "Business"

        print(f"✓ Tags generated:")
        print(f"  Meeting Type: {meeting_type}")
        print(f"  Meeting Topic: {meeting_topic}")

        return {
            'meeting_type': meeting_type,
            'meeting_topic': meeting_topic
        }

    except json.JSONDecodeError as e:
        print(f"✗ Failed to parse JSON response: {str(e)}")
        print(f"  Raw response: {response_text[:200]}...")
        return None

    except Exception as e:
        print(f"✗ Error during tagging: {str(e)}")
        return None


def analyze_and_tag_with_retry(summary_content: str, max_retries: int = 3) -> Optional[Dict[str, str]]:
    """
    Analyze with retry logic

    Args:
        summary_content: The meeting summary text
        max_retries: Maximum number of retry attempts

    Returns:
        dict: Tags if successful, None otherwise
    """
    for attempt in range(max_retries):
        if attempt > 0:
            print(f"🔄 Retry attempt {attempt}/{max_retries}...")

        result = analyze_and_tag(summary_content)

        if result:
            return result

        if attempt < max_retries - 1:
            print(f"⚠️ Tagging failed, retrying in 2 seconds...")
            import time
            time.sleep(2)

    print(f"✗ All retry attempts failed")
    return None


# Test function
def main():
    """Test the auto-tagging with sample summary"""

    # Sample summary for testing
    sample_summary = """
🗣️ Chủ đề cuộc họp: Weekly Review - Doanh số và KPIs tuần

📌 Các vấn đề chính được thảo luận:

1. Doanh số tuần qua giảm 5% so với tuần trước
2. Tỷ lệ conversion từ website xuống thấp
3. Cần tăng cường hoạt động marketing cho Q2
4. Review hiệu quả các sàn TMĐT

✅ Các quyết định & thống nhất:

1. Tăng ngân sách Google Ads thêm 20% cho tuần sau
2. Chạy flash sale vào cuối tuần để boost doanh số
3. Tập trung vào ngành hàng Laptop và PC

⚠️ Các rủi ro / Trở ngại được nêu:

1. Đối thủ cạnh tranh đang chạy promotion mạnh
2. Nguồn hàng Màn hình có thể bị thiếu

❓ Các vấn đề còn tồn đọng / Cần làm rõ:

1. Xác nhận budget chính xác cho campaign
2. Kiểm tra inventory các sản phẩm hot

📋 Kế Hoạch Hành Động (Todo):

Hạng mục (Task) | Người phụ trách (Owner) | Deadline (Hạn chót)
Setup Google Ads campaign | Anh Thiện | 15/12/2025
Chuẩn bị flash sale content | Phương Anh | 14/12/2025
Check inventory | Anh Đạt | 13/12/2025
"""

    print("Testing Gemini Auto-Tagging")
    print("=" * 70)
    print("\nSample Summary:")
    print(sample_summary[:300] + "...\n")
    print("=" * 70)

    tags = analyze_and_tag_with_retry(sample_summary)

    if tags:
        print("\n✓ TAGGING SUCCESSFUL")
        print(f"Meeting Type: {tags['meeting_type']}")
        print(f"Meeting Topic: {tags['meeting_topic']}")
    else:
        print("\n✗ TAGGING FAILED")


if __name__ == "__main__":
    main()
