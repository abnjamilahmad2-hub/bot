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

    # ── Gemini (Google AI Studio) ──
    async def _gemini(self, payload, session):
        url = (
            "https://generativelanguage.googleapis.com/v1beta"
            f"/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )
        async with session.post(
            url,
            headers=self.headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30),
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
                            "SAFETY", "BLOCKLIST",
                            "PROHIBITED_CONTENT",
                        ):
                            return "SAFETY_FILTER"
                    return content
                return ""
            print(
                f"[AI] Gemini {resp.status}",
                flush=True,
            )
            return None  # None = retry / fallback

    # ── OpenRouter (Free Fallback) ──
    async def _openrouter(self, system_prompt, user_prompt, session):
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openrouter_key}",
        }
        payload = {
            "model": "google/gemini-2.0-flash-exp:free",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        async with session.post(
            url,
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get(
                        "message", {}
                    ).get("content", "")
                return ""
            text = await resp.text()
            print(
                f"[AI] OpenRouter {resp.status}: {text}",
                flush=True,
            )
            return None

    # ── Main chat method ──
    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
    ) -> str:
        # Build Gemini payload
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

        # ─ Try 1: Gemini (one shot, fast timeout) ─
        try:
            result = await self._gemini(payload, session)
            if result is not None:
                return result
        except asyncio.TimeoutError:
            print("[AI] Gemini timeout", flush=True)
        except Exception as e:
            print(f"[AI] Gemini error: {e}", flush=True)

        # ─ Try 2: OpenRouter free (immediate fallback) ─
        if self.openrouter_key:
            print(
                "[AI] Switching to OpenRouter fallback...",
                flush=True,
            )
            try:
                result = await self._openrouter(
                    system_prompt, user_prompt, session
                )
                if result is not None:
                    return result
            except asyncio.TimeoutError:
                print("[AI] OpenRouter timeout", flush=True)
            except Exception as e:
                print(f"[AI] OpenRouter error: {e}", flush=True)

        # ─ Try 3: Gemini retry (last chance) ─
        try:
            await asyncio.sleep(2)
            result = await self._gemini(payload, session)
            if result is not None:
                return result
        except Exception:
            pass

        return "RATE_LIMIT"

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


ai_client = AIClient()
