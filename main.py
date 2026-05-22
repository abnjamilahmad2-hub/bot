import discord
from discord.ext import commands
import logging
from shared.config import settings
from shared.database import init_db

# إعداد السجلات (Logging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger("TS_BOT")

class TSBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True # مطلوب لنظام الترحيب والتوديع
        intents.guilds = True  # مطلوب لمزامنة الأوامر بشكل سليم
        super().__init__(command_prefix="$", intents=intents)

    async def setup_hook(self):
        logger.info("Initializing database...")
        await init_db()
        
        # تحميل الفروع (Cogs)
        cogs = [
            "cogs.chat_cog",
            "cogs.guard_cog",
            "cogs.support_cog",
            "cogs.mod_cog"
        ]
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded extension: {cog}")
            except Exception as e:
                logger.error(f"Failed to load extension {cog}: {e}")
                
        # مزامنة أوامر الـ Slash
        await self.tree.sync()
        logger.info("Slash commands synced.")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info("TS BOT is ready to protect The Sanctuary!")

    async def on_guild_join(self, guild: discord.Guild):
        from shared.database import get_db_session
        from shared.models import Guild
        from sqlalchemy import insert
        
        async for session in get_db_session():
            # إدخال السيرفر مع تفعيل الأنظمة الافتراضية
            guild_stmt = insert(Guild).values(
                id=guild.id, 
                name=guild.name
            ).prefix_with("OR IGNORE")
            await session.execute(guild_stmt)
            await session.commit()
            
        system_channel = guild.system_channel
        if system_channel:
            try:
                await system_channel.send("👋 مرحباً! أنا TS BOT.\nتم تفعيل نظام الحماية الذكية (Guard AI) والأنظمة الأساسية.\nاستخدم الأوامر للتفاعل معي.")
            except Exception as e:
                logger.error(f"Failed to send welcome message to {guild.name}: {e}")

if __name__ == "__main__":
    bot = TSBot()
    bot.run(settings.discord_token)
