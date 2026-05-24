import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import io
import os
import logging

logger = logging.getLogger("TS_BOT")

# مسار صورة الخلفية
BG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "welcome_bg.png"
)

# مسار الخط (سيتم تحميله تلقائياً إذا لم يكن موجوداً)
FONT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets"
)
FONT_PATH = os.path.join(FONT_DIR, "cairo_bold.ttf")
FONT_URL = (
    "https://github.com/google/fonts/raw/main/"
    "ofl/cairo/static/Cairo-Bold.ttf"
)


async def _ensure_font():
    """تحميل الخط العربي الفخم مرة واحدة فقط."""
    if os.path.exists(FONT_PATH):
        return
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(FONT_URL, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status == 200:
                    data = await r.read()
                    os.makedirs(FONT_DIR, exist_ok=True)
                    with open(FONT_PATH, "wb") as f:
                        f.write(data)
                    logger.info("Downloaded Cairo-Bold font.")
    except Exception as e:
        logger.warning(f"Could not download font: {e}")


def _make_circle_avatar(avatar_bytes: bytes, size: int) -> Image.Image:
    """قص صورة البروفايل على شكل دائرة مثالية."""
    av = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    av = av.resize((size, size), Image.LANCZOS)

    # إنشاء قناع دائري
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)

    # تطبيق القناع
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(av, (0, 0), mask)
    return result


def _build_welcome_image(
    bg_path: str,
    avatar_bytes: bytes,
    nickname: str,
) -> io.BytesIO:
    """
    بناء صورة الترحيب النهائية:
    1. فتح الخلفية (1024×571)
    2. وضع الصورة الدائرية في مركز الدائرة السوداء (808)
    3. كتابة الاسم في المستطيل السفلي الرمادي
    """
    bg = Image.open(bg_path).convert("RGBA")
    w, h = bg.size  # 1024 x 571

    # ---- إحداثيات الدائرة (محسوبة بالبكسل) ----
    # الدائرة السوداء تقع: أفقياً x=455..570, عمودياً y=231..342
    circle_cx = 512          # مركز أفقي
    circle_cy = 287          # مركز عمودي
    circle_diameter = 110    # قطر الدائرة (أصغر بـ 5px للتأطير)

    avatar_circle = _make_circle_avatar(avatar_bytes, circle_diameter)

    # وضع الصورة الدائرية
    paste_x = circle_cx - circle_diameter // 2
    paste_y = circle_cy - circle_diameter // 2
    bg.paste(avatar_circle, (paste_x, paste_y), avatar_circle)

    # ---- كتابة الاسم في المستطيل السفلي ----
    # المستطيل الرمادي: y=423..510, مركزه y≈467
    draw = ImageDraw.Draw(bg)

    font_size = 28
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except Exception:
        font = ImageFont.load_default()

    # توسيط النص في المستطيل السفلي
    text_y = 453
    bbox = draw.textbbox((0, 0), nickname, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (w - text_w) // 2
    # تعديل عمودي ليتوسط داخل المستطيل
    text_y = 467 - text_h // 2

    # ظل خفيف للوضوح
    draw.text(
        (text_x + 1, text_y + 1), nickname,
        fill=(30, 30, 30, 200), font=font
    )
    # النص الرئيسي (أبيض)
    draw.text(
        (text_x, text_y), nickname,
        fill=(255, 255, 255, 255), font=font
    )

    # تحويل إلى BytesIO
    buf = io.BytesIO()
    bg.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf


class WelcomeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.loop.create_task(_ensure_font())

    @app_commands.command(
        name="welcome_channel",
        description="تحديد روم الترحيب (لتفعيل صورة الترحيب والمنشن)"
    )
    @app_commands.describe(
        channel="الروم الذي تريد إرسال صور الترحيب فيه"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_welcome_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ):
        from shared.database import get_db_session
        from shared.models import Guild
        from sqlalchemy import select, update

        async for session in get_db_session():
            # تأكد أن السيرفر موجود
            stmt = select(Guild).where(Guild.id == interaction.guild.id)
            res = await session.execute(stmt)
            guild_rec = res.scalar_one_or_none()

            if guild_rec:
                await session.execute(
                    update(Guild)
                    .where(Guild.id == interaction.guild.id)
                    .values(welcome_channel_id=channel.id)
                )
            else:
                session.add(Guild(
                    id=interaction.guild.id,
                    name=interaction.guild.name,
                    welcome_channel_id=channel.id,
                ))
            await session.commit()

        # حذف الكاش القديم
        from shared.cache import delete_cache
        await delete_cache(f"welcome_ch:{interaction.guild.id}")

        embed = discord.Embed(
            title="✅ تم تفعيل نظام الترحيب",
            description=(
                f"سيتم إرسال صور الترحيب مع المنشن "
                f"في {channel.mention} عند دخول أي عضو جديد."
            ),
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)

    async def _get_welcome_channel(
        self, guild: discord.Guild
    ) -> discord.TextChannel | None:
        """إحضار روم الترحيب من الكاش أو قاعدة البيانات."""
        from shared.cache import get_cache, set_cache
        from shared.database import get_db_session
        from shared.models import Guild
        from sqlalchemy import select

        cached = await get_cache(f"welcome_ch:{guild.id}")
        if cached:
            ch = guild.get_channel(int(cached))
            return ch

        async for session in get_db_session():
            stmt = select(Guild).where(Guild.id == guild.id)
            res = await session.execute(stmt)
            rec = res.scalar_one_or_none()
            if rec and rec.welcome_channel_id:
                await set_cache(
                    f"welcome_ch:{guild.id}",
                    str(rec.welcome_channel_id),
                    expire=600,
                )
                return guild.get_channel(rec.welcome_channel_id)
        return None

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        channel = await self._get_welcome_channel(member.guild)
        if not channel:
            return

        try:
            # تحميل صورة البروفايل بأعلى جودة
            avatar_url = member.display_avatar.with_size(512).url
            async with aiohttp.ClientSession() as s:
                async with s.get(avatar_url) as r:
                    avatar_bytes = await r.read()

            nickname = member.display_name

            # بناء الصورة
            img_buf = _build_welcome_image(
                BG_PATH, avatar_bytes, nickname
            )

            file = discord.File(img_buf, filename="welcome.png")
            await channel.send(
                content=f"{member.mention}",
                file=file,
            )
        except Exception as e:
            logger.error(f"[Welcome] Error: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
