import aiohttp
import asyncio
from shared.config import settings


FALLBACK_MODELS = [
    settings.gemini_model,
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class AIClient:
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.models = FALLBACK_MODELS
        self.headers = {"Content-Type": "application/json"}
        self._session = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _request(self, model, payload, session):
        """Send a single request to a specific model."""
        url = (
            f"{BASE_URL}/{model}:generateContent"
            f"?key={self.api_key}"
        )
        async with session.post(
            url,
            headers=self.headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            return resp.status, await resp.text(), await resp.json() if resp.status == 200 else None

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
    ) -> str:
        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
        }

        if json_mode:
            payload["generationConfig"] = {
                "responseMimeType": "application/json"
            }

        session = await self.get_session()

        for model in self.models:
            for attempt in range(2):
                try:
                    url = (
                        f"{BASE_URL}/{model}:generateContent"
                        f"?key={self.api_key}"
                    )
                    async with session.post(
                        url,
                        headers=self.headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=60),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get(
                                    "content", {}
                                ).get("parts", [{}])
                                content = parts[0].get("text", "")
                                if not content:
                                    reason = candidates[0].get(
                                        "finishReason", "unknown"
                                    )
                                    if reason in (
                                        "SAFETY",
                                        "BLOCKLIST",
                                        "PROHIBITED_CONTENT",
                                    ):
                                        return "SAFETY_FILTER"
                                return content
                            return ""

                        text = await resp.text()
                        print(
                            f"[AI] {model} attempt {attempt+1}"
                            f" -> {resp.status}",
                            flush=True,
                        )

                        if resp.status in (429, 503):
                            await asyncio.sleep(3)
                            continue
                        return ""

                except asyncio.TimeoutError:
                    print(
                        f"[AI] {model} timeout attempt {attempt+1}",
                        flush=True,
                    )
                    await asyncio.sleep(2)
                    continue
                except Exception as e:
                    print(f"[AI] Exception: {e}", flush=True)
                    return ""

            print(
                f"[AI] {model} exhausted, trying next model...",
                flush=True,
            )

        return "RATE_LIMIT"

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


ai_client = AIClient()
