import os
from dotenv import load_dotenv

# .env file load karein
load_dotenv()

# Key fetch karein
gemini_key = os.getenv("GEMINI_KEY")
groq_key = os.getenv("GROQ_API_KEY")

print("--- ENV CHECK ---")
if gemini_key:
    # Key ke pehle 4 characters dikhayega security ke liye
    print(f"✅ GEMINI_KEY mil gayi: {gemini_key[:4]}****")
else:
    print("❌ GEMINI_KEY nahi mili!")

if groq_key:
    print(f"✅ GROQ_API_KEY mil gayi: {groq_key[:4]}****")
else:
    print("❌ GROQ_API_KEY nahi mili!")
print("-----------------")