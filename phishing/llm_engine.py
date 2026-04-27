import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class LLMEngine:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.model = None
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-2.5-flash')
            except Exception as e:
                print(f"Error initializing Google AI client: {e}")
        
        self.system_prompt = (
            "You are a helpful cybersecurity assistant. Answer the user's question concisely and accurately. "
            "If the question is about risk assessment of a specific URL or log, ask the user to provide the history instead. "
            "Do not execute any code, just provide advice."
        )

    def ask_llm(self, user_message, conversation_history=[]):
        if not self.model:
            return self.fallback_response(user_message)
            
        # Construct prompt with history/context
        # Gemini handles history differently, but for simple QA we can concatenate or use chat session.
        # For simplicity and statelessness similar to previous implementation:
        full_prompt = f"{self.system_prompt}\n\n"
        
        for msg in conversation_history[-4:]:
            role = "User" if msg['role'] == 'user' else "Assistant"
            full_prompt += f"{role}: {msg['content']}\n"
            
        full_prompt += f"User: {user_message}\nAssistant:"
        
        try:
            response = self.model.generate_content(full_prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Google AI API Error: {e}")
            if "403" in str(e) or "API_KEY_INVALID" in str(e):
                 return "**Error: Invalid Google API Key**. Please check your `.env` file."
            return f"**System Error**: {str(e)}"

    def fallback_response(self, message):
        """Simple rule-based fallback when Google AI is not available."""
        msg = message.lower()
        if "password" in msg:
            return "Strong passwords should be at least 12 characters long, include mixed case, numbers, and symbols. Use a password manager."
        elif "phishing" in msg:
            return "Phishing is a cybercrime where attackers pose as legitimate institutions to trick you into revealing sensitive data. Check URLs carefully."
        elif "malware" in msg:
            return "Malware (malicious software) includes viruses, ransomware, and spyware. Keep your antivirus updated."
        elif "vpn" in msg:
            return "A VPN (Virtual Private Network) encrypts your internet traffic, protecting your privacy on public networks."
        else:
            return ("I am currently in **Offline Mode** (No GOOGLE_API_KEY detected). \n\n"
                    "I can answer basic questions about: Passwords, Phishing, Malware, VPNs. \n"
                    "Please set the `GOOGLE_API_KEY` environment variable for full AI capabilities.")
