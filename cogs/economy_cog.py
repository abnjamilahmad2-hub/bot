import discord
from discord.ext import commands

class EconomyCog(commands.Cog):
    """نظام الاقتصاد العالمي - مرتبط بكريديت ديسكورد الأساسي"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.app_commands.command(name="credits", description="عرض رصيدك الحالي من الكريديت العالمي")
    async def credits_command(self, interaction: discord.Interaction):
        from shared.database import get_db_session, ensure_user_and_guild
        from shared.models import User
        from sqlalchemy import select
        
        async for session in get_db_session():
            await ensure_user_and_guild(session, interaction.user.id, interaction.guild.id, interaction.guild.name)
            
            stmt_user = select(User).where(User.id == interaction.user.id)
            user_record = (await session.execute(stmt_user)).scalar_one()
            
            embed = discord.Embed(
                title="💳 الحساب البنكي",
                description=f"🌍 **رصيدك العالمي:** {user_record.global_balance} كريديت",
                color=discord.Color.gold()
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text="الكريديت العالمي مرتبط بنظام ديسكورد الأساسي")
            await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyCog(bot))
