import requests
import streamlit as st


def generate_caption(topic: str, tone: str) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {st.secrets['GROQ_API_KEY']}",
        "Content-Type": "application/json"
    }

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

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"Groq API error {response.status_code}: {response.text}")

    return response.json()["choices"][0]["message"]["content"].strip()


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


def upload_image_to_linkedin(access_token: str, person_urn: str, image_bytes: bytes, filename: str) -> str:
    register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    register_payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": person_urn,
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }
            ]
        }
    }

    reg_response = requests.post(register_url, headers=headers, json=register_payload)
    if reg_response.status_code != 200:
        raise Exception(f"Image registration failed ({reg_response.status_code}): {reg_response.text}")

    reg_data = reg_response.json()
    upload_url = reg_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    image_urn = reg_data["value"]["asset"]

    upload_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream"
    }
    upload_response = requests.put(upload_url, headers=upload_headers, data=image_bytes)
    if upload_response.status_code not in [200, 201]:
        raise Exception(f"Image upload failed ({upload_response.status_code}): {upload_response.text}")

    return image_urn


def post_to_linkedin_with_image(post_text: str, image_urns: list) -> dict:
    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {st.secrets['LINKEDIN_ACCESS_TOKEN']}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    media_list = [
        {
            "status": "READY",
            "description": {"text": f"Image {i+1}"},
            "media": urn,
            "title": {"text": f"Image {i+1}"}
        }
        for i, urn in enumerate(image_urns)
    ]

    payload = {
        "author": st.secrets["LINKEDIN_PERSON_URN"],
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": post_text},
                "shareMediaCategory": "IMAGE",
                "media": media_list
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    return {"status": response.status_code, "body": response.text}