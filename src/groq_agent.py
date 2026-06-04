from groq import Groq
from dotenv import load_dotenv
import os
import json

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

def analyze_news(title, content,agent_prompt):

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
    "confidence": 0-100,
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
                "role":"system",
                "content": agent_prompt
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
            
    )

    import json

    response_text = response.choices[0].message.content

    response_text = response_text.replace("```json", "")
    response_text = response_text.replace("```", "")

    print("\nRAW RESPONSE:")
    print(response_text)
    print("=" * 60)

    return json.loads(response_text)