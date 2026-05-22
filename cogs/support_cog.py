import discord
from discord.ext import commands
from discord import app_commands
import json
from shared.database import get_db_session, ensure_user_and_guild
from shared.models import Guild
from sqlalchemy import select
from shared.cache import get_cache, set_cache

# الرتب التي تُعطي صلاحية تنفيذ أي أمر دون اعتراض
TRUSTED_ROLES = {"Owner", "Server Administration", "Founder", "Co Founder", "High"}

# نص القواعد (مُجمل للـ AI)
RULES_TEXT = """قواعد السيرفر:
1. يجب احترام جميع الأعضاء وعدم مضايقتهم بأي شكل من الأشكال.
2. يمنع إزعاج الأعضاء أو التنمر عليهم.
3. يجب احترام خصوصية الأعضاء وعدم مضايقتهم أو إحراجهم.
4. يمنع نشر صور مسيئة أو غير لائقة أو ما شابه.
5. يمنع الترويج لسيرفر آخر علنًا أو بشكل خاص.
6. السيرفر غير مسؤول عن المشاكل الشخصية، يرجى حلها خارج السيرفر.
7. يمنع دخول السيرفر بصورة أو اسم غير لائق.
8. لا يجوز نشر روابط أو صور مثل صور القتل أو الصور الفاضحة.
9. يمنع إرسال الرسائل المكررة (Spam) أو الإشارات العشوائية (Mentions) دون سبب واضح.
10. يجب الالتزام بموضوع كل قناة واستخدام القنوات المخصصة لكل غرض.
11. يمنع إثارة الجدل في المواضيع السياسية أو الدينية أو العنصرية.
12. يمنع استخدام برامج تغيير الصوت أو إصدار أصوات مزعجة داخل القنوات الصوتية.
13. يمنع انتحال شخصية أي عضو أو أفراد طاقم الإدارة.
14. يمنع نشر أي روابط مشبوهة أو ملفات قد تضر بأجهزة الأعضاء.
15. الإدارة لها الحق في اتخاذ القرار المناسب تجاه أي تصرف غير مذكور في القوانين.
16. نتبع قواعد الديسكورد الرسمية.
"""

class SupportCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _ensure_guild(self, guild: discord.Guild):
        async for session in get_db_session():
            await ensure_user_and_guild(session, self.bot.user.id, guild.id, guild.name)
            stmt = select(Guild).where(Guild.id == guild.id)
            result = await session.execute(stmt)
            guild_record = result.scalar_one_or_none()
            if not guild_record:
                guild_record = Guild(id=guild.id, name=guild.name)
                session.add(guild_record)
                await session.commit()

    @app_commands.command(name="support", description="مساعد كتابي للإجابة على أسئلتك حول قوانين وأنظمة السيرفر.")
    @app_commands.describe(question="سؤالك أو استفسارك")
    async def support(self, interaction: discord.Interaction, question: str):
        # تأكيد تسجيل السيرفر
        if interaction.guild:
            await self._ensure_guild(interaction.guild)
            
        await interaction.response.defer(ephemeral=False, thinking=True)
        
        # استيراد ai_client محلياً لتجنب مشاكل الاستيراد
        from shared.ai_client import ai_client
        
        prompt = f"""أنت مساعد الدعم الفني لسيرفر !808.
مهمتك هي الإجابة على استفسارات الأعضاء بوضوح واحترام بناءً على القوانين التالية:
{RULES_TEXT}

إذا سأل العضو سؤالاً لا يتعلق بالقوانين أو الدعم الفني، أجب بلباقة ووجهه للقوانين أو قل أنك مخصص للدعم فقط.
ردك يجب أن يكون قصيراً وواضحاً ومفيداً، وباللغة العربية المريحة.
"""
        user_prompt = f"المستخدم {interaction.user.display_name} يسأل: {question}"
        
        try:
            ai_response = await ai_client.chat(prompt, user_prompt)
            if not ai_response or ai_response in ("RATE_LIMIT", "SAFETY_FILTER"):
                ai_response = "عذراً، أواجه ضغطاً حالياً ولا يمكنني الرد. يرجى المحاولة لاحقاً."
                
            # إرسال الرد
            if len(ai_response) <= 2000:
                await interaction.followup.send(ai_response)
            else:
                await interaction.followup.send(ai_response[:2000])
        except Exception as e:
            await interaction.followup.send("❌ حدث خطأ أثناء معالجة طلبك.")


async def setup(bot: commands.Bot):
    await bot.add_cog(SupportCog(bot))
