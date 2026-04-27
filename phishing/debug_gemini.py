import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

# Force loading .env file
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
print(f"API Key found: {api_key[:5]}...{api_key[-4:] if api_key else 'None'}")

if not api_key:
    print("ERROR: No API Key found.")
    sys.exit(1)

try:
    print("Attempting to connect to Google Gemini...")
    genai.configure(api_key=api_key)
    
    print("Listing available models...")
    with open("error_log.txt", "w", encoding="utf-8") as f:
        f.write("AVAILABLE MODELS:\n")
        fo_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                fo_models.append(m.name)
                f.write(f"Model: {m.name}\n")
        f.write("-" * 20 + "\n")
        
        if not fo_models:
            f.write("NO MODELS FOUND WITH generateContent SUPPORT!\n")

    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Test connection. Answer with 'Success'.")
    with open("error_log.txt", "a", encoding="utf-8") as f:
         f.write(f"SUCCESS! Response: {response.text}\n")

except Exception as e:
    with open("error_log.txt", "a", encoding="utf-8") as f:
        f.write("\nFAILED TO CONNECT:\n")
        f.write(f"Error Type: {type(e).__name__}\n")
        f.write("-" * 50 + "\n")
        f.write(f"Error Message: {e}\n")
        f.write("-" * 50 + "\n")
        
        if "403" in str(e):
            f.write("\nDIAGNOSIS: 403 Forbidden\n")
            f.write("This almost always means the 'Generative Language API' is NOT enabled for your project.\n")
            f.write("URL to enable: https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com\n")
        if "400" in str(e):
            f.write("\nDIAGNOSIS: 400 Bad Request\n")
            f.write("Required argument might be missing or invalid model.\n")
    print("Error logged to error_log.txt")
