import discord
from discord.ext import commands
import json
from shared.ai_client import ai_client

class GuardCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guard_prompt = """أنت نظام الحماية الذكي (Guard AI) لـ TS BOT في سيرفر The Sanctuary.
مهمتك: تحليل هذه الرسالة وتحديد ما إذا كانت تحتوي على مخالفة (سب، شتائم مبطنة، روابط خبيثة، سبام، إزعاج).
يجب أن ترد بصيغة JSON فقط.
إذا كانت الرسالة سليمة، رد بـ: {"status": "successful", "reason": "safe"}
إذا كانت مخالفة، رد بـ: {"status": "rejected", "action": "delete", "reason": "سبب المخالفة باللغة العربية"}"""

    @discord.app_commands.command(name="tell", description="يردد البوت ما تقوله ويحذف رسالتك.")
    @discord.app_commands.describe(text="النص الذي تريد من البوت قوله")
    async def tell_command(self, interaction: discord.Interaction, text: str):
        # إرسال الرسالة كما طلب المستخدم
        await interaction.channel.send(text)
        await interaction.response.send_message("تم التنفيذ", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # تجاهل رسائل البوتات والأوامر
        if message.author.bot or message.content.startswith(self.bot.command_prefix):
            return

        # منع الانهيار في رسائل الخاص
        if message.guild is None:
            return

        # التحقق مما إذا كان النظام مفعلاً في السيرفر
        from shared.database import get_db_session, ensure_user_and_guild
        from shared.models import Guild
        from sqlalchemy import select
        from shared.cache import get_cache, set_cache
        
        async for session in get_db_session():
            await ensure_user_and_guild(session, message.author.id, message.guild.id, message.guild.name)
            
            # التحقق من الـ Cache أولاً
            active_systems = await get_cache(f"guild_systems:{message.guild.id}")
            if not active_systems:
                stmt = select(Guild).where(Guild.id == message.guild.id)
                result = await session.execute(stmt)
                guild_record = result.scalar_one_or_none()
                if guild_record and guild_record.active_systems:
                    active_systems = str(guild_record.active_systems)
                    await set_cache(f"guild_systems:{message.guild.id}", active_systems, expire=300)
                else:
                    active_systems = ""
                    
            if "guard_ai" not in active_systems:
                return # النظام غير مفعل في هذا السيرفر
                
        # طبقة الحماية الذكية (AI Middleware)
        # إنشاء سياق للمنظومة الذكية
        user_prompt = f"الكاتب: {message.author.name}\nالنص: {message.content}"
        
        # تشغيل التحليل في الخلفية لعدم تجميد البوت
        self.bot.loop.create_task(self.analyze_message(message, user_prompt))

    async def analyze_message(self, message: discord.Message, user_prompt: str):
        try:
            # طلب التحليل من OpenRouter بصيغة JSON
            response = await ai_client.chat(self.guard_prompt, user_prompt, json_mode=True)
            if not response: 
                return
            
            data = json.loads(response)
            if data.get("status") == "rejected":
                reason = data.get("reason", "محتوى غير لائق")
                
                # حذف الرسالة المخالفة
                try:
                    await message.delete()
                    warning_msg = await message.channel.send(f"⚠️ {message.author.mention} تم حذف رسالتك بواسطة الحماية الذكية.\n**السبب:** {reason}")
                    # حذف رسالة التحذير بعد 7 ثواني للحفاظ على نظافة الشات
                    await warning_msg.delete(delay=7)
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    pass
                    
        except json.JSONDecodeError:
            # في حال لم يقم الذكاء الاصطناعي بإرجاع JSON صحيح
            pass
        except Exception as e:
            print(f"[Guard AI Error] {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(GuardCog(bot))
