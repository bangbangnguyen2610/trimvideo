import google.generativeai as genai
import sys

# Fix encoding for Vietnamese
sys.stdout.reconfigure(encoding='utf-8')

# Cấu hình API key
genai.configure(api_key="AIzaSyBg-P8MBhJllhisSRxsxPW8nEh-bQtu0w4")

print("Available models:\n")
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"✓ {model.name}")
        print(f"  Supported methods: {model.supported_generation_methods}")
        print()
