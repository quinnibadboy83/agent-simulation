import os
import httpx


def ask_brain(prompt: str) -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return "No AI key set. Add GEMINI_API_KEY in Render, then redeploy."
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.0-flash:generateContent?key=" + key
    )
    try:
        with httpx.Client(timeout=40.0) as client:
            resp = client.post(url, json={
                "contents": [{"parts": [{"text": prompt}]}],
            })
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"Brain failed: {e}"
