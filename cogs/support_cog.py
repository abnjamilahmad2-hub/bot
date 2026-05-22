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

    def _is_trusted(self, member: discord.Member) -> bool:
        return any(role.name in TRUSTED_ROLES for role in member.roles)

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

    async def _apply_timeout(self, member: discord.Member, minutes: int, reason: str):
        try:
            await member.timeout(discord.utils.utcnow() + discord.timedelta(minutes=minutes), reason=reason)
        except Exception:
            pass

    @app_commands.command(name="support", description="استخدم أوامر الدعم وفق القوانين.")
    @app_commands.describe(action="الإجراء المطلوب (ban/timeout/kick/...)", target="العضو المستهدف", reason="سبب الإجراء")
    @app_commands.default_permissions(administrator=True)
    async def support(self, interaction: discord.Interaction, action: str, target: discord.Member, reason: str = "لم يتم تقديم سبب"):
        # تقييد السيرفر فقط لسيرفر !808
        if interaction.guild.id != 808:
            await interaction.response.send_message("❌ هذا الأمر مخصص لسيرفر !808 فقط.", ephemeral=True)
            return

        await self._ensure_guild(interaction.guild)
        executor = interaction.user

        # إذا كان المنفذ من الرتب الموثوقة، نفّذ مباشرة
        if self._is_trusted(executor):
            await self._execute_action(interaction, action, target, reason)
            return

        # بناء Prompt للذكاء الاصطناعي لتقييم الإجراء
        prompt = f"قواعد السيرفر هي:\n{RULES_TEXT}\n\nالمستخدم {executor.display_name} يرغب في تنفيذ {action} على {target.display_name} مع السبب: {reason}.\n\nهل هذا الإجراء مسموح وفق القواعد؟ أجب بـ JSON فقط:\n{{\"allowed\": true|false, \"action\": \"timeout_10m\"|\"timeout_30m\"|\"kick\"|\"ban\"|\"none\", \"reason\": \"شرح مختصر\"}}"
        ai_response = await ai_client.chat(prompt, json_mode=True)
        try:
            data = json.loads(ai_response)
        except Exception:
            data = {"allowed": False, "action": "none", "reason": "فشل تحليل الذكاء الاصطناعي"}

        if not data.get("allowed"):
            await interaction.response.send_message(f"❌ الإجراء غير مسموح: {data.get('reason', 'لم يحدد السبب')}", ephemeral=True)
            return

        await self._execute_action(interaction, data.get("action", action), target, data.get("reason", reason))

    async def _execute_action(self, interaction: discord.Interaction, action: str, target: discord.Member, reason: str):
        if action.startswith("timeout"):
            minutes = int(action.split("_")[1].replace("m", ""))
            await self._apply_timeout(target, minutes, reason)
            await interaction.response.send_message(f"⏱️ تم كتم {target.mention} لمدة {minutes} دقيقة.\n**السبب:** {reason}")
        elif action == "kick":
            await target.kick(reason=reason)
            await interaction.response.send_message(f"👢 تم طرد {target.mention}.\n**السبب:** {reason}")
        elif action == "ban":
            await target.ban(reason=reason)
            await interaction.response.send_message(f"🔨 تم حظر {target.mention}.\n**السبب:** {reason}")
        else:
            await interaction.response.send_message("⚠️ فعل غير مدعوم.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(SupportCog(bot))
