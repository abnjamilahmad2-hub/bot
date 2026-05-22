import aiohttp
import json
import asyncio
from shared.config import settings

class AIClient:
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        self.headers = {
            "Content-Type": "application/json"
        }
        self._session = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def chat(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ]
        }
        
        if json_mode:
            payload["generationConfig"] = {"responseMimeType": "application/json"}
            
        session = await self.get_session()
        try:
            url = f"{self.base_url}?key={self.api_key}"
            async with session.post(url, headers=self.headers, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    candidates = data.get('candidates', [])
                    if candidates:
                        content = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                        if not content:
                            reason = candidates[0].get('finishReason', 'unknown')
                            print(f"[AI Info] Empty content. Reason: {reason}. Raw data: {data}", flush=True)
                            if reason in ["SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT"]:
                                return "SAFETY_FILTER"
                        return content
                    return ""
                else:
                    text = await resp.text()
                    print(f"[AI Error] {resp.status}: {text}", flush=True)
                    if resp.status == 429:
                        return "RATE_LIMIT"
                    return ""
        except asyncio.TimeoutError:
            print("[AI Error] Timeout")
            return ""
        except Exception as e:
            print(f"[AI Error] Exception: {e}")
            return ""

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

ai_client = AIClient()
