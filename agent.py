import requests
from groq import Groq
import streamlit as st


def generate_caption(topic: str, tone: str) -> str:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    prompt = f"""You are a LinkedIn content writer. Write an engaging LinkedIn post about the following topic.

Topic: {topic}
Tone: {tone}

Guidelines:
- Start with a strong hook (first line grabs attention)
- Use short paragraphs (2-3 lines max)
- Add 3-5 relevant hashtags at the end
- Keep it under 300 words
- Sound human, not robotic

Return ONLY the post text. No extra explanation."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


def post_to_linkedin(post_text: str) -> dict:
    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {st.secrets['LINKEDIN_ACCESS_TOKEN']}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    payload = {
        "author": st.secrets["LINKEDIN_PERSON_URN"],
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": post_text},
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    return {"status": response.status_code, "body": response.text}