import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

with open("test_result.txt", "w", encoding="utf-8") as f:
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content("Say hello in one word.")
        f.write(f"SUCCESS: gemini-2.5-flash responded: {response.text}\n")
    except Exception as e:
        f.write(f"FAILED gemini-2.5-flash: {str(e)[:200]}\n")
        # Try fallback
        try:
            model = genai.GenerativeModel('gemini-2.0-flash-lite')
            response = model.generate_content("Say hello in one word.")
            f.write(f"SUCCESS: gemini-2.0-flash-lite responded: {response.text}\n")
        except Exception as e2:
            f.write(f"FAILED gemini-2.0-flash-lite: {str(e2)[:200]}\n")

print("Done. Check test_result.txt")
