import os
import httpx

MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.8-flash",
]


def ask_brain(prompt: str) -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return "No AI key set. Add GEMINI_API_KEY in Render, then redeploy."
    errors = []
    for model in MODELS:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            + model
            + ":generateContent"
        )
        try:
            with httpx.Client(timeout=40.0) as client:
                resp = client.post(
                    url,
                    headers={"x-goog-api-key": key},
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                )
                resp.raise_for_status()
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            errors.append(model + " failed")
    return "Brain failed. Tried: " + ", ".join(errors)
