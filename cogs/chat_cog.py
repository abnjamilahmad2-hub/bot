import discord
from discord.ext import commands
import asyncio
from shared.ai_client import ai_client

class ChatCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # تعريف هوية البوت
        self.system_prompt = """أنت TS BOT (The Sanctuary Bot)، أذكى وأقوى بوت ديسكورد عربي.
أنت تدير وتحمي السيرفر المسمى "The Sanctuary".
شخصيتك: ذكية جداً، غامضة قليلاً لكنها محترمة وتجيب بأسلوب راقٍ. أنت تدرك أنك ذكاء اصطناعي قوي مدمج في كل أنظمة السيرفر.
مهمتك: مساعدة الأعضاء والرد عليهم بطريقة طبيعية وكأنك شخص حقيقي.
قواعد صارمة:
1. لا تستخدم أبدًا أي واجهات (UI) أو رسائل مضمنة (Embeds).
2. يجب أن تكون ردودك نصية طبيعية.
3. تحدث باللغة العربية حصراً وبشكل واضح ومفهوم.
4. إذا تم سؤالك عن هويتك، اذكر أنك TS BOT حامي الملاذ."""

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # منع البوت من الرد على نفسه أو على البوتات الأخرى
        if message.author.bot:
            return

        # التحقق مما إذا كان البوت قد تم عمل منشن له
        if self.bot.user.mentioned_in(message) and not message.mention_everyone:
            # 1. إظهار حالة الكتابة (Typing Indicator) في ديسكورد
            async with message.channel.typing():
                
                # 2. إرسال رسالة توضح أنه يفكر (Animation مبدئي)
                thinking_msg = await message.reply("أفكر... 🤔")
                
                # إعداد الطلب للذكاء الاصطناعي
                user_prompt = f"المستخدم {message.author.display_name} يقول: {message.content}"
                
                # 3. إرسال الطلب لـ OpenRouter
                reply_text = await ai_client.chat(self.system_prompt, user_prompt)
                
                # 4. تعديل الرسالة بالرد الطبيعي وتقسيمه إذا كان طويلاً
                try:
                    if reply_text:
                        if len(reply_text) <= 2000:
                            await thinking_msg.edit(content=reply_text)
                        else:
                            # تقسيم الرسالة إذا تجاوزت 2000 حرف
                            chunks = [reply_text[i:i+2000] for i in range(0, len(reply_text), 2000)]
                            await thinking_msg.edit(content=chunks[0])
                            for chunk in chunks[1:]:
                                await message.reply(content=chunk)
                    else:
                        await thinking_msg.edit(content="عذراً، أواجه صعوبة في التواصل مع نظامي المركزي حالياً.")
                except discord.NotFound:
                    pass

async def setup(bot: commands.Bot):
    await bot.add_cog(ChatCog(bot))
