import discord
from discord.ext import commands
from discord import app_commands
import json
import datetime

class ModCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.report_prompt = """أنت نظام مراجعة البلاغات (Report System) لسيرفر !808.
يتم إرسال بلاغ ضد عضو معين مع السبب. مهمتك قراءة البلاغ وتقييم المخالفة بناءً على قوانين السيرفر.
بناءً على التقييم، قرر العقوبة المناسبة.
العقوبات الممكنة:
- timeout_10m (مخالفة خفيفة، إزعاج خفيف)
- timeout_30m (مخالفة متوسطة، سبام)
- timeout_1h (مخالفة قوية، إساءة واضحة)
- kick (مخالفة كبيرة تستدعي الطرد)
- ban (مخالفة حرجة، نشر روابط خطيرة، انتحال إدارة)
- none (إذا كان البلاغ غير منطقي أو كيدي)

رد فقط بصيغة JSON:
{"action": "العقوبة", "reason_for_action": "تفسيرك لسبب العقوبة لكي يظهر للمستخدم"}"""

    @app_commands.command(name="clear", description="مسح رسائل من القناة")
    @app_commands.describe(amount="عدد الرسائل")
    @app_commands.default_permissions(manage_messages=True)
    async def clear_command(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
        await interaction.response.defer(ephemeral=True)
        try:
            deleted = await interaction.channel.purge(limit=amount)
            embed = discord.Embed(
                title="🧹 مسح الرسائل",
                description=f"تم مسح {len(deleted)} رسالة بنجاح.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ خطأ: {e}")

    @app_commands.command(name="report", description="تقديم بلاغ ضد عضو ليتم معاقبته تلقائياً بواسطة الذكاء الاصطناعي")
    @app_commands.describe(member="العضو المخالف", reason="سبب البلاغ التفصيلي")
    async def report_command(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        await interaction.response.defer(ephemeral=False, thinking=True)
        
        if member.bot:
            return await interaction.followup.send("❌ لا يمكنك الإبلاغ عن بوت.")
            
        if member.top_role >= interaction.guild.me.top_role:
            return await interaction.followup.send("❌ لا يمكنني معاقبة هذا الشخص لأن رتبته أعلى مني.")

        from shared.ai_client import ai_client
        user_prompt = f"المشتكي: {interaction.user.display_name}\nالمُبلغ عنه: {member.display_name}\nالسبب: {reason}"
        
        try:
            ai_response = await ai_client.chat(self.report_prompt, user_prompt, json_mode=True)
            if not ai_response or ai_response in ("RATE_LIMIT", "SAFETY_FILTER"):
                return await interaction.followup.send("عذراً، النظام مشغول حالياً. يرجى المحاولة لاحقاً.")
                
            data = json.loads(ai_response)
            action = data.get("action", "none")
            ai_reason = data.get("reason_for_action", "بناءً على البلاغ")
            
            embed = discord.Embed(
                title="🚨 تقرير البلاغ الذكي",
                color=discord.Color.red()
            )
            embed.add_field(name="المُبلغ عنه", value=member.mention, inline=False)
            embed.add_field(name="القرار", value=ai_reason, inline=False)
            
            if action == "none":
                embed.description = "لم يتم اتخاذ أي عقوبة (البلاغ غير كافٍ)."
                await interaction.followup.send(embed=embed)
                return
                
            # تنفيذ العقوبة
            try:
                if action == "timeout_10m":
                    await member.timeout(datetime.timedelta(minutes=10), reason=ai_reason)
                    embed.description = "تم إعطاء العضو كتم لمدة 10 دقائق."
                elif action == "timeout_30m":
                    await member.timeout(datetime.timedelta(minutes=30), reason=ai_reason)
                    embed.description = "تم إعطاء العضو كتم لمدة 30 دقيقة."
                elif action == "timeout_1h":
                    await member.timeout(datetime.timedelta(hours=1), reason=ai_reason)
                    embed.description = "تم إعطاء العضو كتم لمدة ساعة."
                elif action == "kick":
                    await member.kick(reason=ai_reason)
                    embed.description = "تم طرد العضو من السيرفر."
                elif action == "ban":
                    await member.ban(reason=ai_reason)
                    embed.description = "تم حظر العضو من السيرفر."
                else:
                    embed.description = "عقوبة غير معروفة."
            except discord.Forbidden:
                embed.description = "❌ ليس لدي صلاحية كافية لتنفيذ هذه العقوبة."
                
            await interaction.followup.send(embed=embed)
            
        except json.JSONDecodeError:
            await interaction.followup.send("❌ حدث خطأ في تحليل قرار الذكاء الاصطناعي.")
        except Exception as e:
            await interaction.followup.send(f"❌ حدث خطأ غير متوقع: {e}")

async def setup(bot):
    await bot.add_cog(ModCog(bot))
