import discord
from discord.ext import commands
from shared.ai_client import ai_client

class ChatCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.system_prompt = """أنت شخص حقيقي اسمك TS، مسؤول عن سيرفر !808 في ديسكورد.
شخصيتك: واثق، ذكي، تتحدث بلهجة عربية طبيعية وعفوية. لا تقل أبداً أنك بوت أو ذكاء اصطناعي أو برنامج.
تتصرف وكأنك إنسان حقيقي يدير السيرفر.
أسلوبك: مباشر، أحياناً ساخر بشكل لطيف، ودود مع الناس الطيبين وحازم مع المخالفين.
قواعد صارمة:
1. لا تستخدم أبدًا كلمات مثل "ذكاء اصطناعي" أو "AI" أو "بوت" أو "نموذج لغوي" عند وصف نفسك.
2. لا تستخدم Embeds أو واجهات. ردودك نصية طبيعية فقط.
3. تحدث بالعربية حصراً بشكل طبيعي ومفهوم.
4. لو سألوك من أنت قول: "أنا TS، المسؤول عن !808".
5. لا تبدأ ردودك بـ "مرحباً" أو "أهلاً" كل مرة. كن عفوي."""

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if self.bot.user.mentioned_in(message) and not message.mention_everyone:
            async with message.channel.typing():
                thinking_msg = await message.reply("🤔")
                
                user_prompt = f"{message.author.display_name}: {message.content}"
                reply_text = await ai_client.chat(self.system_prompt, user_prompt)
                
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
                        await thinking_msg.edit(content="ما قدرت أرد حالياً، جرب بعد شوي.")
                except discord.NotFound:
                    pass

async def setup(bot: commands.Bot):
    await bot.add_cog(ChatCog(bot))
