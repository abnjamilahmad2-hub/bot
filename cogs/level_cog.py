import discord
from discord.ext import commands
from shared.database import get_db_session
from shared.models import GuildMember
from sqlalchemy import select

class LevelCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.content.startswith(self.bot.command_prefix):
            return

        if message.guild is None:
            return

        # حساب عدد الأحرف (تجاهل المسافات الفارغة)
        char_count = len(message.content.replace(" ", ""))
        
        # تجاهل الرسائل القصيرة جداً لعدم رفع المستوى بالسبام
        if char_count < 5:
            return 
            
        from shared.database import get_db_session, ensure_user_and_guild
        from shared.models import Guild, GuildMember
        from sqlalchemy import select
        from shared.cache import get_cache, set_cache
            
        async for session in get_db_session():
            # التأكد من تفعيل نظام المستويات
            await ensure_user_and_guild(session, message.author.id, message.guild.id, message.guild.name)
            
            # التحقق من الـ Cache أولاً
            active_systems = await get_cache(f"guild_systems:{message.guild.id}")
            if not active_systems:
                stmt_guild = select(Guild).where(Guild.id == message.guild.id)
                guild_record = (await session.execute(stmt_guild)).scalar_one_or_none()
                if guild_record and guild_record.active_systems:
                    active_systems = str(guild_record.active_systems)
                    await set_cache(f"guild_systems:{message.guild.id}", active_systems, expire=300)
                else:
                    active_systems = ""
                    
            if "level_ai" not in active_systems:
                return
                
            # البحث عن إحصائيات المستخدم
            stmt = select(GuildMember).where(
                GuildMember.user_id == message.author.id,
                GuildMember.guild_id == message.guild.id
            )
            result = await session.execute(stmt)
            member_record = result.scalar_one_or_none()
            
            if not member_record:
                # إنشاء سجل جديد إذا لم يكن موجوداً
                member_record = GuildMember(user_id=message.author.id, guild_id=message.guild.id)
                member_record.level = 0
                member_record.characters_typed = 0
                session.add(member_record)
                
            # إضافة الأحرف المكتوبة
            if member_record.characters_typed is None:
                member_record.characters_typed = 0
            if member_record.level is None:
                member_record.level = 0
            
            member_record.characters_typed += char_count
            
            # كل 500 حرف تعادل 1 مستوى (Level)
            new_level = member_record.characters_typed // 500
            
            # إذا وصل لمستوى جديد
            if new_level > member_record.level:
                member_record.level = new_level
                await message.channel.send(f"🎉 أسطوري يا {message.author.mention}! لقد وصلت للمستوى **{new_level}** بفضل تفاعلك وكتاباتك.")
                
            await session.commit()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # التحقق من حصول العضو على البوست (Boost)
        if not before.premium_since and after.premium_since:
            from shared.database import get_db_session, ensure_user_and_guild
            from shared.models import Guild, GuildMember
            from sqlalchemy import select
            from shared.cache import get_cache, set_cache
            
            async for session in get_db_session():
                await ensure_user_and_guild(session, after.id, after.guild.id, after.guild.name)
                
                # التحقق من الـ Cache أولاً
                active_systems = await get_cache(f"guild_systems:{after.guild.id}")
                if not active_systems:
                    stmt_guild = select(Guild).where(Guild.id == after.guild.id)
                    guild_record = (await session.execute(stmt_guild)).scalar_one_or_none()
                    if guild_record and guild_record.active_systems:
                        active_systems = str(guild_record.active_systems)
                        await set_cache(f"guild_systems:{after.guild.id}", active_systems, expire=300)
                    else:
                        active_systems = ""
                        
                if "level_ai" not in active_systems:
                    return
                    
                stmt = select(GuildMember).where(
                    GuildMember.user_id == after.id,
                    GuildMember.guild_id == after.guild.id
                )
                result = await session.execute(stmt)
                member_record = result.scalar_one_or_none()
                
                if not member_record:
                    member_record = GuildMember(user_id=after.id, guild_id=after.guild.id)
                    member_record.level = 0
                    member_record.characters_typed = 0
                    session.add(member_record)
                
                if member_record.level is None:
                    member_record.level = 0
                if member_record.characters_typed is None:
                    member_record.characters_typed = 0
                    
                # مكافأة البوست: 25 مستوى
                member_record.level += 25
                # إضافة أحرف وهمية ليتوافق المستوى مع الحسبة (25 * 500 = 12500)
                member_record.characters_typed += 12500 
                await session.commit()
                
                # إرسال رسالة شكر في القناة العامة
                channel = after.guild.system_channel
                if channel:
                    await channel.send(f"🚀 شكراً لدعمك السيرفر يا {after.mention}! لقد تم مكافأتك بـ **25 مستوى إضافي** للبوست الأسطوري.")

async def setup(bot: commands.Bot):
    await bot.add_cog(LevelCog(bot))
