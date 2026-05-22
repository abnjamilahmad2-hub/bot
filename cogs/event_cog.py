import discord
from discord.ext import commands, tasks
import datetime
from shared.ai_client import ai_client


class EventCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.event_prompt = """أنت منظم الفعاليات الذكي (Event AI) في سيرفر The Sanctuary.
مهمتك: توليد فعالية يومية (سؤال، لغز، تحدي، أو موضوع نقاش مثير) لتنشيط السيرفر.
يجب أن يكون باللغة العربية ومميز جداً وحماسي. اكتب فقط نص الفعالية بدون مقدمات."""
        self.last_event_date = {}
        # تخزين: guild_id -> {"channel_id": ..., "message_id": ..., "event_channel_id": ...}
        self.active_events = {}
        self.daily_event.start()

    def cog_unload(self):
        self.daily_event.cancel()

    class ParticipateView(discord.ui.View):
        """زر المشاركة الوحيد - يوجه المستخدم إلى قناة الفعالية المخفية"""
        def __init__(self, event_channel_id: int):
            super().__init__(timeout=None)
            self.event_channel_id = event_channel_id
            self.participants = set()

        @discord.ui.button(
            label="🎮 اضغط هنا للمشاركة في الفعالية!",
            style=discord.ButtonStyle.success,
            custom_id="event_participate_btn",
            row=0
        )
        async def participate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            # التحقق من أن المستخدم لم يشارك مسبقاً
            if interaction.user.id in self.participants:
                await interaction.response.send_message(
                    "⚠️ لقد شاركت بالفعل! توجه إلى قناة الفعالية.",
                    ephemeral=True
                )
                return

            self.participants.add(interaction.user.id)

            # إعطاء المستخدم صلاحية رؤية القناة المخفية
            event_channel = interaction.guild.get_channel(self.event_channel_id)
            if event_channel:
                await event_channel.set_permissions(
                    interaction.user,
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )
                await interaction.response.send_message(
                    f"✅ تم تسجيل مشاركتك! توجه الآن إلى قناة الفعالية: {event_channel.mention}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ حدث خطأ، لم يتم العثور على قناة الفعالية.",
                    ephemeral=True
                )

    async def _cleanup_old_event(self, guild: discord.Guild):
        """حذف القناة المخفية القديمة ورسالة الفعالية القديمة"""
        old_data = self.active_events.get(guild.id)
        if not old_data:
            return

        # حذف رسالة الفعالية القديمة
        try:
            old_msg_channel = guild.get_channel(old_data.get("message_channel_id", 0))
            if old_msg_channel:
                old_msg = await old_msg_channel.fetch_message(old_data.get("message_id", 0))
                if old_msg:
                    await old_msg.delete()
        except (discord.NotFound, discord.HTTPException):
            pass

        # حذف قناة الفعالية المخفية القديمة
        try:
            old_event_channel = guild.get_channel(old_data.get("event_channel_id", 0))
            if old_event_channel:
                await old_event_channel.delete(reason="تنظيف فعالية اليوم السابق")
        except (discord.NotFound, discord.HTTPException):
            pass

        # مسح البيانات المخزنة
        del self.active_events[guild.id]

    async def _create_hidden_channel(self, guild: discord.Guild, event_title: str) -> discord.TextChannel:
        """إنشاء قناة مخفية خاصة بالفعالية - لا يراها أحد إلا المشاركين"""
        today = datetime.date.today().strftime("%Y-%m-%d")
        channel_name = f"🎯│فعالية-{today}"

        # صلاحيات: إخفاء القناة عن الجميع
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True
            )
        }

        # البحث عن category مناسبة أو إنشاء واحدة
        category = discord.utils.get(guild.categories, name="🎉 الفعاليات")
        if not category:
            category = await guild.create_category(
                name="🎉 الفعاليات",
                overwrites=overwrites
            )

        # إنشاء القناة المخفية
        event_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"📌 فعالية اليوم: {event_title[:100]}",
            reason="قناة فعالية يومية جديدة"
        )

        # إرسال رسالة ترحيبية في القناة المخفية
        welcome_embed = discord.Embed(
            title="🎉 مرحباً بك في فعالية اليوم!",
            description=(
                f"**{event_title}**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "📝 شارك برأيك أو إجابتك هنا!\n"
                "💬 تفاعل مع باقي المشاركين\n"
                "🏆 أفضل مشاركة ستحصل على مكافأة!\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.gold()
        )
        welcome_embed.set_footer(text="⏰ هذه القناة ستُحذف تلقائياً بعد 24 ساعة")
        await event_channel.send(embed=welcome_embed)

        return event_channel

    @tasks.loop(hours=24)
    async def daily_event(self):
        from shared.database import get_db_session
        from shared.models import Guild as GuildModel
        from sqlalchemy import select
        from shared.cache import get_cache, set_cache

        today = datetime.date.today()

        for guild in self.bot.guilds:
            # التحقق من عدم إرسال فعالية مسبقاً اليوم
            if self.last_event_date.get(guild.id) == today:
                continue

            is_event_active = False
            active_systems = await get_cache(f"guild_systems:{guild.id}")
            guild_record = None
            async for session in get_db_session():
                stmt = select(GuildModel).where(GuildModel.id == guild.id)
                guild_record = (await session.execute(stmt)).scalar_one_or_none()
                if not active_systems:
                    if guild_record and guild_record.active_systems:
                        active_systems = str(guild_record.active_systems)
                        await set_cache(f"guild_systems:{guild.id}", active_systems, expire=300)
                    else:
                        active_systems = ""

            if "event_ai" not in active_systems:
                continue

            # تحديد قناة إرسال الفعالية الرئيسية
            channel = None
            if guild_record and guild_record.events_channel_id:
                channel = guild.get_channel(guild_record.events_channel_id)
            if not channel:
                channel = guild.system_channel
            if not channel:
                channel = next((c for c in guild.text_channels if c.name in ("عام", "general")), None)

            if not channel:
                continue

            try:
                # 1) حذف الفعالية القديمة (القناة + الرسالة)
                await self._cleanup_old_event(guild)

                # 2) توليد فعالية جديدة بالذكاء الاصطناعي
                topic = await ai_client.chat(self.event_prompt, "اصنع فعالية اليوم بأسلوب حماسي ومميز.")
                if not topic:
                    topic = "🎯 تحدي اليوم: شارك أفضل نصيحة تعلمتها في حياتك!"

                # 3) إنشاء القناة المخفية
                event_channel = await self._create_hidden_channel(guild, topic)

                # 4) إرسال رسالة الفعالية مع زر المشاركة
                embed = discord.Embed(
                    title="🎉 فعالية اليوم الكبرى! 🎉",
                    description=topic,
                    color=discord.Color.purple()
                )
                embed.add_field(
                    name="📋 كيف تشارك؟",
                    value="اضغط على الزر بالأسفل وستفتح لك قناة خاصة بالفعالية!",
                    inline=False
                )
                embed.set_footer(text="⏰ الفعالية تنتهي خلال 24 ساعة | شارك الآن!")
                embed.timestamp = datetime.datetime.now(datetime.timezone.utc)

                view = self.ParticipateView(event_channel.id)
                msg = await channel.send(
                    content="@everyone 📢 حان وقت الفعالية اليومية!",
                    embed=embed,
                    view=view
                )

                # 5) تخزين بيانات الفعالية الحالية للحذف لاحقاً
                self.active_events[guild.id] = {
                    "message_id": msg.id,
                    "message_channel_id": channel.id,
                    "event_channel_id": event_channel.id,
                    "created_at": today.isoformat()
                }

                self.last_event_date[guild.id] = today

            except Exception as e:
                print(f"[Event Error] Guild {guild.id}: {e}", flush=True)

    @daily_event.before_loop
    async def before_event(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(EventCog(bot))
