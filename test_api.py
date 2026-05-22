import os
import json
import urllib.request
import urllib.error

# ── احصل على المفتاح من متغيّر بيئي ──────────────────────
#   اضبطه في نظامك:  set OPENROUTER_API_KEY=sk-xxxx (Windows PowerShell)
#   أو ضع القيمة مباشرةً داخل المتغيّر التالي (ليس مُستحباً).
api_key = os.getenv("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")
if not api_key:
    raise RuntimeError("خطأ: يرجى تعيين متغيّر البيئة OPENROUTER_API_KEY بقيمة مفتاح API الخاص بك.")

models = [
    "openrouter/free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "qwen/qwen3-coder:free",
]

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}

def post(payload: dict):
    """إرسال طلب POST وإرجاع نص الاستجابة."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            # إذا كان الرمز 2xx سيتجه إلى هنا
            body = resp.read().decode("utf-8")
            return body
    except urllib.error.HTTPError as e:
        # إرجاع نص الخطأ لتسهيل الفحص
        err_body = e.read().decode("utf-8")
        raise RuntimeError(f"HTTP {e.code}: {err_body}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"فشل الاتصال: {e.reason}") from None


for model in models:
    print(f"\n--- اختبار النموذج: {model} ---")

    # 1️⃣ اختبار طلب عادي (بدون JSON)
    try:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Reply with 'hi'"}],
        }
        resp_text = post(payload)
        print("NO JSON: Success!")
        print("← الرد:", resp_text[:200], "...")   # عرض جزء من النتيجة
    except Exception as exc:
        print("NO JSON: فشل →", exc)

    # 2️⃣ اختبار طلب مع response_format = json_object
    try:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": 'Reply with JSON {"a": 1}'}],
            "response_format": {"type": "json_object"},
        }
        resp_text = post(payload)
        print("JSON: Success!")
        # التأكد من أن المحتوى فعلاً JSON صالح
        try:
            parsed = json.loads(resp_text)
            print("← JSON مُفسَّر:", parsed)
        except json.JSONDecodeError:
            print("← التحذير: الرد غير صالح كـ JSON")
    except Exception as exc:
        print("JSON: فشل →", exc)