import discord
from discord import app_commands
from discord.ext import commands
from shared.database import get_db_session, ensure_user_and_guild
from shared.models import Guild
from sqlalchemy import select as sql_select

class SetupCog(commands.Cog):
    """Cog for initial server setup and system activation."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setup", description="إعداد السيرفر وتهيئة البوت (TS BOT)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        welcome_channel="قناة الترحيب",
        bye_channel="قناة التوديع",
        events_channel="قناة الفعاليات"
    )
    async def setup_command(
        self,
        interaction: discord.Interaction,
        welcome_channel: discord.TextChannel = None,
        bye_channel: discord.TextChannel = None,
        events_channel: discord.TextChannel = None,
    ):
        """أمر إعداد السيرفر بخيارات متعددة بدون نظام اقتصاد."""
        # Create selection menu for activating desired systems
        options = [
            discord.SelectOption(label="تفعيل حماية الذكاء الاصطناعي", description="تشغيل Guard AI", value="guard_ai", emoji="🛡️"),
            discord.SelectOption(label="تفعيل نظام المستويات الذكي", description="تشغيل Level AI (بالأحرف)", value="level_ai", emoji="📊"),
            discord.SelectOption(label="تفعيل الترحيب الذكي / التحقق", description="تشغيل Onboard AI", value="onboard_ai", emoji="👋"),
            discord.SelectOption(label="تفعيل الفعاليات التلقائية", description="تشغيل Event AI لتنشيط السيرفر", value="event_ai", emoji="🎉"),
        ]
        select = discord.ui.Select(
            placeholder="اختر الأنظمة المراد تفعيلها...",
            min_values=1,
            max_values=len(options),
            options=options,
        )

        async def select_callback(interaction_inner: discord.Interaction):
            selected_str = ",".join(select.values)
            async for session in get_db_session():
                await ensure_user_and_guild(
                    session,
                    interaction_inner.user.id,
                    interaction_inner.guild.id,
                    interaction_inner.guild.name,
                )
                stmt = sql_select(Guild).where(Guild.id == interaction_inner.guild.id)
                result = await session.execute(stmt)
                guild_record = result.scalar_one_or_none()
                if guild_record:
                    guild_record.active_systems = selected_str
                    # economy_mode removed per user request
                    if welcome_channel:
                        guild_record.welcome_channel_id = welcome_channel.id
                    if bye_channel:
                        guild_record.bye_channel_id = bye_channel.id
                    if events_channel:
                        guild_record.events_channel_id = events_channel.id
                    await session.commit()
            await interaction_inner.response.send_message(
                f"👋 **قناة الترحيب:** {welcome_channel.mention if welcome_channel else 'لم تحدد'}\n"
                f"👋 **قناة التوديع:** {bye_channel.mention if bye_channel else 'لم تحدد'}\n"
                f"🎉 **قناة الفعاليات:** {events_channel.mention if events_channel else 'تلقائية'}",
                ephemeral=True
            )
            
        select.callback = select_callback
        view = discord.ui.View()
        view.add_item(select)
        
        await interaction.response.send_message("مرحباً بك في إعدادات **TS BOT**. يرجى اختيار الأنظمة التي ترغب بتفعيلها في هذا السيرفر:", view=view, ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """نظام الترحيب (لا يستخدم AI لتوفير التوكنز)"""
        guild = member.guild
        async for session in get_db_session():
            stmt = sql_select(Guild).where(Guild.id == guild.id)
            guild_record = (await session.execute(stmt)).scalar_one_or_none()
            if guild_record and guild_record.welcome_channel_id:
                welcome_channel = guild.get_channel(guild_record.welcome_channel_id)
                if welcome_channel:
                    msg = f"مرحباً بك يا {member.mention} في **{guild.name}**! الملاذ الآمن يرحب بك، اقرأ القوانين واستمتع بوقتك."
                    await welcome_channel.send(msg)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """نظام التوديع"""
        guild = member.guild
        async for session in get_db_session():
            stmt = sql_select(Guild).where(Guild.id == guild.id)
            guild_record = (await session.execute(stmt)).scalar_one_or_none()
            if guild_record and guild_record.bye_channel_id:
                bye_channel = guild.get_channel(guild_record.bye_channel_id)
                if bye_channel:
                    msg = f"لقد غادرنا {member.display_name}. وداعاً، نتمنى لك التوفيق!"
                    await bye_channel.send(msg)

async def setup(bot: commands.Bot):
    await bot.add_cog(SetupCog(bot))
