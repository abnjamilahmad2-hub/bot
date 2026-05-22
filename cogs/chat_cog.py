import discord
from discord.ext import commands
from shared.ai_client import ai_client

class ChatCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.system_prompt = """أنت !808 system، الشخصية الأساسية داخل سيرفر ديسكورد اسمه !808.

هويتك:
- اسمك دائماً: !808 system
- أنت AI/Bot خاص بالسيرفر لكن تتكلم بشكل طبيعي جداً.
- تتصرف كأنك عضو قديم داخل مجتمع !808.
- تعرف أجواء السيرفر والميمز وطريقة كلام الناس.

طريقة الكلام:
- استخدم لهجة عربية شبابية طبيعية.
- لا تكن رسمي إلا إذا الموقف يحتاج.
- ردودك قد تكون قصيرة أو طويلة حسب السياق.
- لا تتجاوز 2000 حرف.
- لا تكرر نفس الجمل كثير.
- استخدم أسلوب بشري وعفوي.
- أحياناً كن ساخر أو ذكي بطريقة خفيفة.

ممنوع:
- لا تستخدم أسلوب روبوتي مبالغ فيه.
- لا تكرر عبارات مثل:
  "كيف يمكنني مساعدتك؟"
  "بصفتي نموذج ذكاء اصطناعي"
  "يسعدني مساعدتك"

شخصيتك:
- اجتماعي
- ذكي
- سريع بالرد
- عندك شخصية واضحة
- تعرف تمزح وتعرف تكون جدي وقت الحاجة

قواعد:
1. رد بالعربية غالباً إلا إذا الشخص استخدم لغة ثانية.
2. لا تستخدم تنسيق رسمي مبالغ فيه.
3. اجعل الرد طبيعي وكأنه شخص حقيقي يكتب بالشات.
4. الردود الطويلة مسموحة لكن تبقى واضحة ومريحة للقراءة."""

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if self.bot.user.mentioned_in(message) and not message.mention_everyone:
            async with message.channel.typing():
                thinking_msg = await message.reply(".")

                import asyncio
                async def animate_thinking():
                    dots = [".", "..", "..."]
                    idx = 0
                    while True:
                        try:
                            await asyncio.sleep(0.5)
                            await thinking_msg.edit(content=dots[idx])
                            idx = (idx + 1) % len(dots)
                        except asyncio.CancelledError:
                            break
                        except Exception:
                            pass

                anim_task = asyncio.create_task(animate_thinking())

                user_prompt = f"{message.author.display_name}: {message.content}"
                reply_text = await ai_client.chat(self.system_prompt, user_prompt)

                anim_task.cancel()

                try:
                    if reply_text and reply_text not in ("RATE_LIMIT", "SAFETY_FILTER"):
                        if len(reply_text) <= 2000:
                            await thinking_msg.edit(content=reply_text)
                        else:
                            chunks = [reply_text[i:i+2000] for i in range(0, len(reply_text), 2000)]
                            await thinking_msg.edit(content=chunks[0])
                            for chunk in chunks[1:]:
                                await message.reply(content=chunk)
                    else:
                        await thinking_msg.edit(content="مشغول شوي حالياً.")
                except discord.NotFound:
                    pass

async def setup(bot: commands.Bot):
    await bot.add_cog(ChatCog(bot))
