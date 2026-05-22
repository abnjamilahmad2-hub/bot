import discord
from discord.ext import commands
import random
import asyncio

class EconomyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.app_commands.command(name="credits", description="عرض رصيدك الحالي")
    async def credits_command(self, interaction: discord.Interaction):
        from shared.database import get_db_session, ensure_user_and_guild
        from shared.models import User, GuildMember, Guild
        from sqlalchemy import select
        
        async for session in get_db_session():
            await ensure_user_and_guild(session, interaction.user.id, interaction.guild.id, interaction.guild.name)
            
            stmt_user = select(User).where(User.id == interaction.user.id)
            user_record = (await session.execute(stmt_user)).scalar_one()
            
            stmt_member = select(GuildMember).where(
                GuildMember.user_id == interaction.user.id,
                GuildMember.guild_id == interaction.guild.id
            )
            member_record = (await session.execute(stmt_member)).scalar_one()
            
            stmt_guild = select(Guild).where(Guild.id == interaction.guild.id)
            guild_record = (await session.execute(stmt_guild)).scalar_one()
            
            eco_mode = guild_record.economy_mode or "both"
            
            desc = ""
            if eco_mode in ["global", "both"]:
                desc += f"🌍 **رصيدك العالمي (الحقيقي):** {user_record.global_balance} كريديت\n"
            if eco_mode in ["local", "both"]:
                desc += f"🏠 **رصيدك المحلي (الوهمي):** {member_record.local_balance} كريديت\n"
                
            embed = discord.Embed(
                title="💳 الحساب البنكي",
                description=desc,
                color=discord.Color.gold()
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="guess_game", description="لعبة التخمين السريعة! خمن الرقم خلال 10 ثواني.")
    async def guess_command(self, interaction: discord.Interaction):
        number = random.randint(1, 10)
        await interaction.response.send_message(f"🤔 **لعبة التخمين!**\nلقد فكرت في رقم من 1 إلى 10. لديك 10 ثواني لتخمينه وكتابته في الشات يا {interaction.user.mention}!")
        
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel and m.content.isdigit()

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=10.0)
            if int(msg.content) == number:
                reward = random.randint(50, 150)
                from shared.database import get_db_session
                from shared.models import GuildMember, Guild
                from sqlalchemy import select
                
                awarded = False
                async for session in get_db_session():
                    stmt_guild = select(Guild).where(Guild.id == interaction.guild.id)
                    guild_record = (await session.execute(stmt_guild)).scalar_one()
                    
                    if guild_record.economy_mode in ["local", "both"]:
                        stmt_member = select(GuildMember).where(
                            GuildMember.user_id == interaction.user.id,
                            GuildMember.guild_id == interaction.guild.id
                        )
                        member_record = (await session.execute(stmt_member)).scalar_one()
                        member_record.local_balance = (member_record.local_balance or 0) + reward
                        await session.commit()
                        awarded = True
                        
                if awarded:
                    await interaction.channel.send(f"🎉 صحيح! الرقم هو {number}. ربحت {reward} كريديت محلي!")
                else:
                    await interaction.channel.send(f"🎉 صحيح! الرقم هو {number}. (النظام العالمي مفعل فقط لذا لا يوجد مكافآت)")
            else:
                await interaction.channel.send(f"❌ خطأ! الرقم الصحيح كان {number}.")
        except asyncio.TimeoutError:
            await interaction.channel.send(f"⏰ انتهى الوقت! الرقم الصحيح كان {number}.")

    @discord.app_commands.command(name="riddle_game", description="لعبة الألغاز السريعة! أجب خلال 10 ثواني.")
    async def riddle_command(self, interaction: discord.Interaction):
        riddles = [
            {"q": "شيء كلما زاد نقص؟", "a": ["العمر", "عمر"]},
            {"q": "شيء له أسنان ولا يعض؟", "a": ["المشط", "مشط"]},
            {"q": "ابن الماء وإذا وضع فيه مات؟", "a": ["الثلج", "الجليد", "ثلج"]},
            {"q": "شيء يكتب ولا يقرأ؟", "a": ["القلم", "قلم"]},
        ]
        riddle = random.choice(riddles)
        
        await interaction.response.send_message(f"🧠 **لغز سريع!**\n{riddle['q']}\nلديك 10 ثواني للإجابة يا {interaction.user.mention}!")
        
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=10.0)
            if any(ans in msg.content.lower() for ans in riddle["a"]):
                reward = random.randint(100, 300)
                from shared.database import get_db_session
                from shared.models import GuildMember, Guild
                from sqlalchemy import select
                
                awarded = False
                async for session in get_db_session():
                    stmt_guild = select(Guild).where(Guild.id == interaction.guild.id)
                    guild_record = (await session.execute(stmt_guild)).scalar_one()
                    
                    if guild_record.economy_mode in ["local", "both"]:
                        stmt_member = select(GuildMember).where(
                            GuildMember.user_id == interaction.user.id,
                            GuildMember.guild_id == interaction.guild.id
                        )
                        member_record = (await session.execute(stmt_member)).scalar_one()
                        member_record.local_balance = (member_record.local_balance or 0) + reward
                        await session.commit()
                        awarded = True
                        
                if awarded:
                    await interaction.channel.send(f"🎉 إجابة عبقرية! ربحت {reward} كريديت محلي!")
                else:
                    await interaction.channel.send(f"🎉 إجابة عبقرية! (النظام العالمي مفعل فقط لذا لا يوجد مكافآت)")
            else:
                await interaction.channel.send(f"❌ إجابة خاطئة! الإجابة هي {riddle['a'][0]}.")
        except asyncio.TimeoutError:
            await interaction.channel.send(f"⏰ انتهى الوقت! الإجابة هي {riddle['a'][0]}.")

async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyCog(bot))
