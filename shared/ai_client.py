import aiohttp
import asyncio
from shared.config import settings


class AIClient:
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model
        self.openrouter_key = settings.openrouter_api_key
        self.headers = {"Content-Type": "application/json"}
        self._session = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def clean_json(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text

    async def _gemini(self, payload, session):
        url = (
            "https://generativelanguage.googleapis.com/v1beta"
            f"/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )
        async with session.post(
            url, headers=self.headers, json=payload, timeout=aiohttp.ClientTimeout(total=20)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                c = data.get("candidates", [])
                if c:
                    content = c[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    if not content:
                        if c[0].get("finishReason") in ("SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT"):
                            return "SAFETY_FILTER"
                    return content
                return ""
            print(f"[AI] Gemini {resp.status}", flush=True)
            return None

    async def _openrouter(self, system_prompt, user_prompt, session):
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openrouter_key}",
        }
        payload = {
            "model": "openrouter/auto",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        }
        async with session.post(
            url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=25)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                return ""
            text = await resp.text()
            print(f"[AI] OpenRouter {resp.status}: {text}", flush=True)
            return None

    async def chat(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        }
        if json_mode:
            payload["generationConfig"] = {"responseMimeType": "application/json"}

        session = await self.get_session()

        # Try Gemini
        try:
            res = await self._gemini(payload, session)
            if res: return self.clean_json(res) if json_mode else res
        except asyncio.TimeoutError:
            print("[AI] Gemini timeout", flush=True)
        except Exception as e:
            print(f"[AI] Gemini err: {e}", flush=True)

        # Try OpenRouter
        if self.openrouter_key:
            print("[AI] Switching to OpenRouter...", flush=True)
            try:
                res = await self._openrouter(system_prompt, user_prompt, session)
                if res: return self.clean_json(res) if json_mode else res
            except asyncio.TimeoutError:
                print("[AI] OpenRouter timeout", flush=True)
            except Exception as e:
                print(f"[AI] OpenRouter err: {e}", flush=True)

        return "RATE_LIMIT"

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

ai_client = AIClient()
