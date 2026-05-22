import aiohttp
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
        session = await self.get_session()
        url = f"{self.base_url}?key={self.api_key}"
        
        for attempt in range(3):
            try:
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
                        print(f"[AI Error] Attempt {attempt+1} - {resp.status}: {text}", flush=True)
                        if resp.status == 429:
                            await asyncio.sleep(2)
                            continue
                        elif resp.status == 503:
                            await asyncio.sleep(3)
                            continue
                        return ""
            except asyncio.TimeoutError:
                print(f"[AI Error] Timeout attempt {attempt+1}")
                await asyncio.sleep(2)
                continue
            except Exception as e:
                print(f"[AI Error] Exception: {e}")
                return ""
                
        return "RATE_LIMIT"

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

ai_client = AIClient()
