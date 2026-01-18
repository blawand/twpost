
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

def test_model(version):
    print(f"\n🧪 Testing with API version: {version}")
    try:
        # Note: genai.configure doesn't have a version arg, 
        # but we can try to use the low-level client or check if the model name works now
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemma-3-27b")
        response = model.generate_content("Hello")
        print(f"✅ Success ({version}): {response.text}")
    except Exception as e:
        print(f"❌ Failed ({version}): {e}")

test_model("default")
