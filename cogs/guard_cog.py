import discord
from discord.ext import commands
import json
import datetime
from shared.ai_client import ai_client

TRUSTED_ROLES = {"Owner", "Server Administration", "Founder", "Co Founder"}

class GuardCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # Micro-prompt لتقليل استهلاك الـ Tokens والحصول على استجابة فورية
        self.security_prompt = """أنت مشرف أمني (Anti-Nuke) لـ !808.
تصلك حركة إدارية. حلل إن كانت "تخريب/Nuke" أم "طبيعية".
التخريب: حظر/طرد بدون سبب مقنع، مسح قنوات/رتب، إضافة بوتات غريبة.
رد بـ JSON فقط: {"is_nuke": true|false}"""

        self.spam_tracker = {}

    def _has_trusted_role(self, member: discord.Member) -> bool:
        return any(role.name in TRUSTED_ROLES for role in member.roles)

    async def _check_security_action(self, guild: discord.Guild, executor: discord.Member, action_desc: str):
        """يرسل الحدث للذكاء الاصطناعي، إذا كان نيوك يعاقب الفاعل"""
        # إذا كان الفاعل هو السيرفر أونر، لا يتم عقابه
        if executor.id == guild.owner_id:
            return False
            
        executor_age = (datetime.datetime.now(datetime.timezone.utc) - executor.joined_at).days if executor.joined_at else 100
        
        prompt = f"الإداري: {executor.name} (بالسيرفر منذ {executor_age} يوم)\nالفعل: {action_desc}"
        
        try:
            response = await ai_client.chat(self.security_prompt, prompt, json_mode=True)
            if not response or response in ("RATE_LIMIT", "SAFETY_FILTER"):
                return False
                
            data = json.loads(response)
            is_nuke = data.get("is_nuke", False)
            
            if is_nuke:
                # طرد المخرب
                try:
                    await executor.kick(reason=f"نظام الحماية: تم طرد المخرب بسبب: {action_desc}")
                except discord.Forbidden:
                    pass
                
                # تنبيه
                for ch in guild.text_channels:
                    if ch.permissions_for(guild.me).send_messages:
                        embed = discord.Embed(
                            title="🛡️ نظام الحماية (Anti-Nuke)",
                            description=f"تم رصد محاولة تخريب من {executor.mention}.\n**الفعل:** {action_desc}\n\n✅ **القرار:** تم طرد المشتبه به.",
                            color=discord.Color.red()
                        )
                        await ch.send(embed=embed)
                        break
                return True
        except Exception:
            pass
        return False

    async def _get_audit_log_executor(self, guild: discord.Guild, action: discord.AuditLogAction, target_id: int):
        try:
            async for entry in guild.audit_logs(limit=5, action=action):
                if entry.target and entry.target.id == target_id:
                    return entry.user
        except discord.Forbidden:
            pass
        return None

    # 1. Banning
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        executor = await self._get_audit_log_executor(guild, discord.AuditLogAction.ban, user.id)
        if executor and not executor.bot:
            is_nuke = await self._check_security_action(guild, executor, f"قام بحظر العضو {user.name}")
            if is_nuke:
                try:
                    await guild.unban(user, reason="Anti-Nuke: Reverting Ban")
                except discord.Forbidden:
                    pass

    # 2. Kicking
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        executor = await self._get_audit_log_executor(member.guild, discord.AuditLogAction.kick, member.id)
        if executor and not executor.bot:
            await self._check_security_action(member.guild, executor, f"قام بطرد العضو {member.name}")

    # 3. Channel Delete
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        executor = await self._get_audit_log_executor(channel.guild, discord.AuditLogAction.channel_delete, channel.id)
        if executor and not executor.bot:
            is_nuke = await self._check_security_action(channel.guild, executor, f"قام بمسح القناة {channel.name}")
            if is_nuke:
                try:
                    await channel.clone(reason="Anti-Nuke: Reverting Channel Deletion")
                except discord.Forbidden:
                    pass

    # 4. Channel Create
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        executor = await self._get_audit_log_executor(channel.guild, discord.AuditLogAction.channel_create, channel.id)
        if executor and not executor.bot:
            is_nuke = await self._check_security_action(channel.guild, executor, f"قام بإنشاء القناة {channel.name}")
            if is_nuke:
                try:
                    await channel.delete(reason="Anti-Nuke: Deleting spam channel")
                except discord.Forbidden:
                    pass

    # 5. Role Delete
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        executor = await self._get_audit_log_executor(role.guild, discord.AuditLogAction.role_delete, role.id)
        if executor and not executor.bot:
            await self._check_security_action(role.guild, executor, f"قام بمسح الرتبة {role.name}")

    # 6. Role Create
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        executor = await self._get_audit_log_executor(role.guild, discord.AuditLogAction.role_create, role.id)
        if executor and not executor.bot:
            is_nuke = await self._check_security_action(role.guild, executor, f"قام بإنشاء الرتبة {role.name}")
            if is_nuke:
                try:
                    await role.delete(reason="Anti-Nuke: Deleting spam role")
                except discord.Forbidden:
                    pass

    # 7. Bot Add
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            executor = await self._get_audit_log_executor(member.guild, discord.AuditLogAction.bot_add, member.id)
            if executor and not executor.bot:
                is_nuke = await self._check_security_action(member.guild, executor, f"قام بإضافة البوت {member.name}")
                if is_nuke:
                    try:
                        await member.kick(reason="Anti-Nuke: Removing unauthorized bot")
                    except discord.Forbidden:
                        pass

    @discord.app_commands.command(name="tell", description="يردد البوت ما تقوله ويحذف رسالتك.")
    @discord.app_commands.describe(text="النص الذي تريد من البوت قوله")
    async def tell_command(self, interaction: discord.Interaction, text: str):
        await interaction.channel.send(text)
        await interaction.response.send_message("تم", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(GuardCog(bot))
