import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

class GrayEmbed(discord.Embed):
    def __init__(self, **kwargs):
        super().__init__(color=discord.Color.from_rgb(40, 40, 40), **kwargs)

class AVRServerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="avr_server", description="عرض معلومات سيرفر !808")
    async def avr_server(self, interaction: discord.Interaction):
        guild = interaction.guild

        total_members = guild.member_count
        online_members = len([
            m for m in guild.members
            if m.status != discord.Status.offline
        ])

        created = int(guild.created_at.timestamp())

        embed = GrayEmbed(
            title=f"⚙️ {guild.name}",
            description="واجهة معلومات سيرفر !808"
        )

        embed.add_field(
            name="📌 اسم السيرفر",
            value=guild.name,
            inline=True
        )

        embed.add_field(
            name="👥 الأعضاء",
            value=f"{total_members}",
            inline=True
        )

        embed.add_field(
            name="🟢 المتصلين",
            value=f"{online_members}",
            inline=True
        )

        embed.add_field(
            name="📅 عمر السيرفر",
            value=f"<t:{created}:R>",
            inline=False
        )

        embed.add_field(
            name="👑 المالك",
            value=str(guild.owner),
            inline=True
        )

        embed.add_field(
            name="🧩 الرومات",
            value=f"{len(guild.channels)}",
            inline=True
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.set_footer(text="!808 system • Advanced UI")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(AVRServerCog(bot))
