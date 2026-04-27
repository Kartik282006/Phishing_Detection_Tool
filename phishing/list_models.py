import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

with open("available_models.txt", "w", encoding="utf-8") as f:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            f.write(f"{m.name}\n")

print("Done. Check available_models.txt")
