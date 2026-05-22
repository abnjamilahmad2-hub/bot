import discord
from discord.ext import commands
import json
import datetime
from shared.ai_client import ai_client

# الرتب الموثوقة في نظام الحماية (High ليست موثوقة)
TRUSTED_ROLES = {"Owner", "Server Administration", "Founder", "Co Founder"}

class GuardCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.spam_tracker = {}  # user_id -> [timestamps]
        self.guard_prompt = """أنت نظام الحماية الذكي لسيرفر !808. مهمتك تحليل الرسائل بدقة.
قوانين السيرفر:
1. يجب احترام جميع الأعضاء وعدم مضايقتهم.
2. يمنع إزعاج الأعضاء أو التنمر عليهم.
3. يمنع نشر صور مسيئة أو غير لائقة.
4. يمنع الترويج لسيرفر آخر علناً أو بشكل خاص.
5. يمنع نشر روابط أو صور مثل صور القتل أو الصور الفاضحة.
6. يمنع الرسائل المكررة (Spam) أو الإشارات العشوائية.
7. يمنع إثارة الجدل في المواضيع السياسية أو الدينية أو العنصرية.
8. يمنع انتحال شخصية أي عضو أو أفراد طاقم الإدارة.
9. يمنع نشر أي روابط مشبوهة أو ملفات ضارة.
10. يمنع دخول السيرفر بصورة أو اسم غير لائق.

رد بـ JSON فقط:
{"status": "safe"} إذا الرسالة سليمة
{"status": "violation", "severity": "low|medium|high|critical", "reason": "سبب المخالفة", "action": "timeout_10m|timeout_30m|remove_user|block_user"}

درجات العقوبة:
- low (سب خفيف/إزعاج) = timeout_10m
- medium (محتوى غير لائق/سبام) = timeout_30m  
- high (ترويج سيرفر/روابط مشبوهة) = remove_user
- critical (انتحال شخصية/محتوى خطير) = block_user"""

        self.name_check_prompt = """أنت نظام فحص أسماء المستخدمين لسيرفر !808.
حلل هذا الاسم وحدد هل هو لائق أم لا. الأسماء غير اللائقة تشمل: ألفاظ بذيئة، إيحاءات جنسية، أسماء عنصرية، انتحال شخصية إدارة.
رد بـ JSON فقط:
{"is_appropriate": true} أو {"is_appropriate": false, "reason": "السبب"}"""

    def _has_trusted_role(self, member: discord.Member) -> bool:
        """التحقق من أن العضو يحمل رتبة موثوقة (High ليست موثوقة في الحماية)"""
        return any(role.name in TRUSTED_ROLES for role in member.roles)

    def _is_spam(self, user_id: int) -> bool:
        """كشف السبام: 5 رسائل أو أكثر خلال 5 ثواني"""
        now = datetime.datetime.now()
        if user_id not in self.spam_tracker:
            self.spam_tracker[user_id] = []
        
        # تنظيف الرسائل القديمة (أكثر من 5 ثواني)
        self.spam_tracker[user_id] = [
            t for t in self.spam_tracker[user_id] 
            if (now - t).total_seconds() < 5
        ]
        self.spam_tracker[user_id].append(now)
        
        return len(self.spam_tracker[user_id]) >= 5

    @discord.app_commands.command(name="tell", description="يردد البوت ما تقوله ويحذف رسالتك.")
    @discord.app_commands.describe(text="النص الذي تريد من البوت قوله")
    async def tell_command(self, interaction: discord.Interaction, text: str):
        await interaction.channel.send(text)
        await interaction.response.send_message("تم", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        if message.content.startswith(self.bot.command_prefix):
            return

        # تجاهل الرتب الموثوقة
        if self._has_trusted_role(message.author):
            return

        from shared.database import get_db_session, ensure_user_and_guild
        from shared.models import Guild
        from sqlalchemy import select
        from shared.cache import get_cache, set_cache
        
        async for session in get_db_session():
            await ensure_user_and_guild(session, message.author.id, message.guild.id, message.guild.name)
            
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
                return

        # فحص السبام أولاً (بدون AI)
        if self._is_spam(message.author.id):
            try:
                await message.delete()
                duration = datetime.timedelta(minutes=15)
                await message.author.timeout(duration, reason="سبام - رسائل متكررة بسرعة")
                warning = await message.channel.send(f"⚠️ {message.author.mention} تم كتمك 15 دقيقة بسبب السبام.")
                await warning.delete(delay=7)
            except (discord.Forbidden, discord.NotFound):
                pass
            return

        # تحليل الرسالة بالذكاء الاصطناعي
        user_prompt = f"الكاتب: {message.author.name}\nالنص: {message.content}"
        self.bot.loop.create_task(self._analyze_message(message, user_prompt))

    async def _analyze_message(self, message: discord.Message, user_prompt: str):
        try:
            response = await ai_client.chat(self.guard_prompt, user_prompt, json_mode=True)
            if not response or response in ("RATE_LIMIT", "SAFETY_FILTER"):
                return
            
            data = json.loads(response)
            if data.get("status") == "violation":
                reason = data.get("reason", "مخالفة القوانين")
                action = data.get("action", "timeout_10m")
                
                # حذف الرسالة المخالفة
                try:
                    await message.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass

                # تنفيذ العقوبة
                try:
                    if action == "timeout_10m":
                        duration = datetime.timedelta(minutes=10)
                        await message.author.timeout(duration, reason=reason)
                        warning = await message.channel.send(f"⚠️ {message.author.mention} تم كتمك 10 دقائق.\n**السبب:** {reason}")
                    elif action == "timeout_30m":
                        duration = datetime.timedelta(minutes=30)
                        await message.author.timeout(duration, reason=reason)
                        warning = await message.channel.send(f"⚠️ {message.author.mention} تم كتمك 30 دقيقة.\n**السبب:** {reason}")
                    elif action == "remove_user":
                        await message.author.kick(reason=reason)
                        warning = await message.channel.send(f"👢 تم طرد {message.author.display_name}.\n**السبب:** {reason}")
                    elif action == "block_user":
                        await message.author.ban(reason=reason)
                        warning = await message.channel.send(f"🔨 تم حظر {message.author.display_name}.\n**السبب:** {reason}")
                    else:
                        warning = await message.channel.send(f"⚠️ {message.author.mention} تم حذف رسالتك.\n**السبب:** {reason}")
                    
                    await warning.delete(delay=10)
                except (discord.Forbidden, discord.NotFound):
                    pass
                    
        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"[Guard AI Error] {e}", flush=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """فحص الحسابات الجديدة المشبوهة"""
        if member.bot:
            return

        account_age = (datetime.datetime.now(datetime.timezone.utc) - member.created_at).days
        
        # حساب عمره أقل من 7 أيام = مشبوه
        if account_age < 7:
            # فحص الاسم
            await self._check_member_name(member)
            
            # إرسال تنبيه للإدارة
            for channel in member.guild.text_channels:
                if channel.permissions_for(member.guild.me).send_messages:
                    try:
                        await channel.send(
                            f"🔍 **تنبيه أمني:** {member.mention} حساب جديد (عمره {account_age} يوم). "
                            f"تحت المراقبة.",
                            delete_after=60
                        )
                    except discord.Forbidden:
                        continue
                    break

    async def _check_member_name(self, member: discord.Member):
        """فحص اسم العضو"""
        try:
            response = await ai_client.chat(
                self.name_check_prompt, 
                f"الاسم: {member.display_name}", 
                json_mode=True
            )
            if not response or response in ("RATE_LIMIT", "SAFETY_FILTER"):
                return
                
            data = json.loads(response)
            if not data.get("is_appropriate", True):
                reason = data.get("reason", "اسم غير لائق")
                try:
                    duration = datetime.timedelta(minutes=10)
                    await member.timeout(duration, reason=f"اسم غير لائق: {reason}")
                except discord.Forbidden:
                    pass
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """مراقبة تغيير الرتب - حماية من إعطاء رتب مشبوهة"""
        if before.bot or after.bot:
            return

        # الرتب الجديدة التي أُضيفت
        added_roles = set(after.roles) - set(before.roles)
        if not added_roles:
            return

        # البحث عن من أعطى الرتبة في سجلات التدقيق
        try:
            async for entry in after.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update):
                if entry.target and entry.target.id == after.id:
                    executor = entry.user
                    if executor.bot:
                        return
                    
                    # لو المعطي عنده رتبة موثوقة (ليس High) → مسموح
                    if self._has_trusted_role(executor):
                        return
                    
                    # لو المعطي ما عنده رتبة موثوقة → مشبوه
                    # timeout 5 دقائق للمعطي وإزالة الرتبة
                    try:
                        for role in added_roles:
                            await after.remove_roles(role, reason="إعطاء رتبة مشبوه - تم الإلغاء تلقائياً")
                        
                        duration = datetime.timedelta(minutes=5)
                        await executor.timeout(duration, reason="محاولة إعطاء رتبة بدون صلاحية موثوقة")
                        
                        # تنبيه
                        for ch in after.guild.text_channels:
                            if ch.permissions_for(after.guild.me).send_messages:
                                await ch.send(
                                    f"🛡️ **حماية الرتب:** {executor.mention} حاول إعطاء رتبة لـ {after.mention}. "
                                    f"تم إلغاء الرتبة وكتم المسؤول 5 دقائق.",
                                    delete_after=30
                                )
                                break
                    except discord.Forbidden:
                        pass
                    break
        except discord.Forbidden:
            pass

    @commands.Cog.listener() 
    async def on_member_update_name(self, before: discord.Member, after: discord.Member):
        """فحص تغيير الأسماء"""
        if before.display_name != after.display_name:
            await self._check_member_name(after)

async def setup(bot: commands.Bot):
    await bot.add_cog(GuardCog(bot))
