import discord
from discord.ext import commands
from shared.welcome_ui import create_card

WELCOME_CHANNEL_NAME = "welcome"

class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_card(self, member, text):
        channel = discord.utils.get(member.guild.text_channels, name=WELCOME_CHANNEL_NAME)
        if not channel:
            return

        path = f"/tmp/{member.id}.png"

        create_card(
            username=member.display_name,
            subtitle=text,
            avatar_url=member.display_avatar.url,
            output_path=path
        )

        file = discord.File(path, filename="card.png")

        embed = discord.Embed(
            description=text,
            color=discord.Color.from_rgb(40,40,40)
        )

        embed.set_image(url="attachment://card.png")

        await channel.send(embed=embed, file=file)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.send_card(member, f"Welcome to !808")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.send_card(member, f"Goodbye from !808")

async def setup(bot):
    await bot.add_cog(WelcomeCog(bot))
