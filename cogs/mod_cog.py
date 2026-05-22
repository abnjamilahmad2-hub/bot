import discord
from discord.ext import commands
from discord import app_commands

class ModCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ban", description="حظر عضو من السيرفر مع ذكر السبب.")
    @app_commands.describe(member="العضو المراد حظره", reason="سبب الحظر")
    @app_commands.default_permissions(ban_members=True)
    async def ban_command(self, interaction: discord.Interaction, member: discord.Member, reason: str = "بدون سبب"):
        if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("❌ لا يمكنك حظر شخص لديه رتبة أعلى منك أو مساوية لك.", ephemeral=True)
            return

        try:
            await member.ban(reason=f"By {interaction.user}: {reason}")
            embed = discord.Embed(
                title="🔨 تم الحظر",
                description=f"تم حظر {member.mention} بنجاح.\n**السبب:** {reason}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ حدث خطأ أثناء محاولة الحظر: {e}", ephemeral=True)

    async def unban_autocomplete(self, interaction: discord.Interaction, current: str):
        bans = []
        try:
            async for ban_entry in interaction.guild.bans(limit=1000):
                user = ban_entry.user
                if current.lower() in user.name.lower() or current == str(user.id):
                    bans.append(app_commands.Choice(name=f"{user.name} ({user.id})", value=str(user.id)))
                if len(bans) >= 25:
                    break
        except:
            pass
        return bans

    @app_commands.command(name="unban", description="فك الحظر عن عضو من القائمة.")
    @app_commands.describe(user_id="الشخص المراد فك الحظر عنه")
    @app_commands.autocomplete(user_id=unban_autocomplete)
    @app_commands.default_permissions(ban_members=True)
    async def unban_command(self, interaction: discord.Interaction, user_id: str):
        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user)
            embed = discord.Embed(
                title="🔓 تم فك الحظر",
                description=f"تم فك الحظر عن {user.mention} بنجاح.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        except discord.NotFound:
            await interaction.response.send_message("❌ هذا العضو غير محظور.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ الرجاء إدخال مستخدم صحيح.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ حدث خطأ أثناء محاولة فك الحظر: {e}", ephemeral=True)

    @app_commands.command(name="kick", description="طرد عضو من السيرفر.")
    @app_commands.describe(member="العضو المراد طرده", reason="سبب الطرد")
    @app_commands.default_permissions(kick_members=True)
    async def kick_command(self, interaction: discord.Interaction, member: discord.Member, reason: str = "بدون سبب"):
        if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("❌ لا يمكنك طرد شخص لديه رتبة أعلى منك أو مساوية لك.", ephemeral=True)
            return

        try:
            await member.kick(reason=f"By {interaction.user}: {reason}")
            embed = discord.Embed(
                title="👢 تم الطرد",
                description=f"تم طرد {member.mention} بنجاح.\n**السبب:** {reason}",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ حدث خطأ أثناء محاولة الطرد: {e}", ephemeral=True)

    @app_commands.command(name="timeout", description="إعطاء تايم أوت (كتم) لعضو.")
    @app_commands.describe(member="العضو", minutes="عدد الدقائق (0 لفك الكتم)", reason="السبب")
    @app_commands.default_permissions(moderate_members=True)
    async def timeout_command(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "بدون سبب"):
        if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("❌ لا يمكنك كتم شخص لديه رتبة أعلى منك أو مساوية لك.", ephemeral=True)
            return

        import datetime
        try:
            if minutes > 0:
                duration = datetime.timedelta(minutes=minutes)
                await member.timeout(duration, reason=f"By {interaction.user}: {reason}")
                embed = discord.Embed(
                    title="⏱️ تم إعطاء تايم أوت",
                    description=f"تم كتم {member.mention} لمدة {minutes} دقيقة.\n**السبب:** {reason}",
                    color=discord.Color.gold()
                )
            else:
                await member.timeout(None, reason=f"By {interaction.user}: فك الكتم")
                embed = discord.Embed(
                    title="⏱️ تم فك التايم أوت",
                    description=f"تم فك الكتم عن {member.mention}.",
                    color=discord.Color.green()
                )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ حدث خطأ أثناء محاولة التايم أوت: {e}", ephemeral=True)

    @app_commands.command(name="clear", description="مسح عدد من الرسائل من القناة الحالية.")
    @app_commands.describe(amount="عدد الرسائل المراد مسحها (1-100)")
    @app_commands.default_permissions(manage_messages=True)
    async def clear_command(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
        await interaction.response.defer(ephemeral=True)
        try:
            deleted = await interaction.channel.purge(limit=amount)
            await interaction.followup.send(f"🧹 تم مسح {len(deleted)} رسالة بنجاح.")
        except Exception as e:
            await interaction.followup.send(f"❌ حدث خطأ أثناء مسح الرسائل: {e}")

    @app_commands.command(name="warn", description="توجيه إنذار لعضو في السيرفر.")
    @app_commands.describe(member="العضو", reason="سبب الإنذار")
    @app_commands.default_permissions(moderate_members=True)
    async def warn_command(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        # في المستقبل يمكن حفظ الإنذارات في الداتا بيس، حاليا نرسلها بالخاص والشات
        embed = discord.Embed(
            title="⚠️ إنذار رسمي",
            description=f"تم إنذار {member.mention}.\n**السبب:** {reason}\n**بواسطة:** {interaction.user.mention}",
            color=discord.Color.yellow()
        )
        try:
            await member.send(f"لقد تلقيت إنذاراً في سيرفر **{interaction.guild.name}**\nالسبب: {reason}")
        except:
            pass # الخاص مغلق
            
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(ModCog(bot))
