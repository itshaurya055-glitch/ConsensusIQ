from groq import Groq
from dotenv import load_dotenv
import os
import json

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

def analyze_news(title, content):

    prompt = f"""
You are a financial analyst.

Analyze the news and return ONLY valid JSON.

Title:
{title}

Content:
{content}

Return format:

{{
    "direction": "BUY/HOLD/SELL",
    "confidence": 0,
    "sector": "",
    "event_type": "",
    "impact": "LOW/MEDIUM/HIGH"
}}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content