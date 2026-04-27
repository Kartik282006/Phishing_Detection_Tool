import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

# Models to test based on previous availability list
candidates = [
    'gemini-1.5-flash-latest',
    'gemini-1.5-pro-latest',
    'gemini-1.0-pro',
    'gemini-pro',
    'models/gemini-1.5-flash-001',
    'models/gemini-1.5-pro-001'
]

print("Testing models for quota/availability...")
working_model = None

with open("model_test_log.txt", "w") as log:
    for model_name in candidates:
        print(f"Testing: {model_name}...")
        log.write(f"Testing: {model_name}...\n")
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content("Hello", request_options={"timeout": 10})
            print(f"SUCCESS! {model_name} responded.")
            log.write(f"SUCCESS! {model_name}\n")
            working_model = model_name
            break
        except Exception as e:
            print(f"FAILED: {e}")
            log.write(f"FAILED: {model_name} - {str(e)[:100]}...\n")

if working_model:
    print(f"\nRECOMMENDATION: Use '{working_model}'")
    with open("working_model.txt", "w") as f:
        f.write(working_model)
else:
    print("\nNO WORKING MODELS FOUND.")
