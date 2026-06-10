from groq import Groq
from dotenv import load_dotenv
import os
import json

load_dotenv(override=True)


def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set")

    return Groq(api_key=api_key)


def analyze_news(title, content, agent_prompt):
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

    client = get_groq_client()

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": agent_prompt
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    response_text = response.choices[0].message.content

    response_text = response_text.replace("```json", "")
    response_text = response_text.replace("```", "")

    print("\nRAW RESPONSE:")
    print(response_text)
    print("=" * 60)

    return json.loads(response_text)


def analyze_news_multi_agent(title, content):
    """
    Call Groq once to simulate all 4 agents (conservative, momentum, value, risk_averse).
    Returns a dict mapping agent name to their individual analysis.
    """
    client = get_groq_client()
    
    prompt = f"""
Analyze the following financial news article from the perspective of four different AI investment agents:

1. "conservative": Low risk tolerance, prioritizes capital preservation and stable large-cap news.
2. "momentum": Focuses on high-growth, breakouts, trend-following, and positive catalyst news.
3. "value": Looks for undervalued stocks, margins of safety, long-term fundamentals, and market overreactions.
4. "risk_averse": Extremely sensitive to macro risks, debt levels, regulatory changes, and geopolitical uncertainty.

Title: {title}
Content: {content}

You must return a valid JSON object matching the following structure:
{{
    "conservative": {{
        "direction": "BUY/HOLD/SELL",
        "confidence": 0-100,
        "sector": "FINANCIALS/TECHNOLOGY/ENERGY/HEALTHCARE/CONSUMER/UNKNOWN",
        "event_type": "EARNINGS/POLICY/MACRO/M&A/REGULATORY/UNKNOWN",
        "impact": "LOW/MEDIUM/HIGH"
    }},
    "momentum": {{
        "direction": "BUY/HOLD/SELL",
        "confidence": 0-100,
        "sector": "FINANCIALS/TECHNOLOGY/ENERGY/HEALTHCARE/CONSUMER/UNKNOWN",
        "event_type": "EARNINGS/POLICY/MACRO/M&A/REGULATORY/UNKNOWN",
        "impact": "LOW/MEDIUM/HIGH"
    }},
    "value": {{
        "direction": "BUY/HOLD/SELL",
        "confidence": 0-100,
        "sector": "FINANCIALS/TECHNOLOGY/ENERGY/HEALTHCARE/CONSUMER/UNKNOWN",
        "event_type": "EARNINGS/POLICY/MACRO/M&A/REGULATORY/UNKNOWN",
        "impact": "LOW/MEDIUM/HIGH"
    }},
    "risk_averse": {{
        "direction": "BUY/HOLD/SELL",
        "confidence": 0-100,
        "sector": "FINANCIALS/TECHNOLOGY/ENERGY/HEALTHCARE/CONSUMER/UNKNOWN",
        "event_type": "EARNINGS/POLICY/MACRO/M&A/REGULATORY/UNKNOWN",
        "impact": "LOW/MEDIUM/HIGH"
    }}
}}
"""

    completion = client.chat.completions.create(
        model="llama3-8b-8192",  # Fast & high limits
        messages=[
            {"role": "system", "content": "You are an expert multi-agent financial analyst coordinator. Return JSON only."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )
    
    response_text = completion.choices[0].message.content
    response_text = response_text.replace("```json", "").replace("```", "")
    
    return json.loads(response_text)