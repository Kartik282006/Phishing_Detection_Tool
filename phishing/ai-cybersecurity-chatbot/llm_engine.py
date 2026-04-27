import os
import openai

class LLMEngine:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            openai.api_key = self.api_key
        
        self.system_prompt = (
            "You are CyberGuard, an AI voice security assistant for Phish Carnage. "
            "Your main role is to help users understand cybersecurity threats like phishing and malware. "
            "Keep your responses conversational, concise, and easy to understand when spoken aloud. "
            "Do not use complex markdown or code blocks. "
            "If the question is about risk assessment of a specific URL, tell the user to say 'scan' followed by the URL."
        )

    def ask_llm(self, user_message, conversation_history=[]):
        if not self.api_key:
            return self.fallback_response(user_message)
            
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add context (limit to last 4 messages to save tokens)
        for msg in conversation_history[-4:]:
            messages.append(msg)
            
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=250,
                temperature=0.7
            )
            return response.choices[0].message['content'].strip()
        except Exception as e:
            print(f"OpenAI API Error: {e}")
            return "I'm having trouble connecting to my AI brain right now. Please try again later."

    def fallback_response(self, message):
        """Simple rule-based fallback when OpenAI is not available."""
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
            return ("I am currently in **Offline Mode** (No OpenAI API Key detected). \n\n"
                    "I can answer basic questions about: Passwords, Phishing, Malware, VPNs. \n"
                    "Please set the `OPENAI_API_KEY` environment variable for full AI capabilities.")
