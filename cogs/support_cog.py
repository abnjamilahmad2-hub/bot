import discord
from discord.ext import commands
from discord import app_commands
import json
import datetime

RULES_TEXT = """قواعد السيرفر:
1. يجب احترام جميع الأعضاء وعدم مضايقتهم.
2. يمنع إزعاج الأعضاء أو التنمر عليهم.
3. يمنع نشر صور مسيئة أو غير لائقة.
4. يمنع الترويج لسيرفر آخر.
5. يمنع نشر روابط خطيرة أو صور الفاضحة.
6. يمنع إرسال الرسائل المكررة (Spam).
7. يمنع إثارة الجدل في المواضيع السياسية أو الدينية.
8. يمنع انتحال شخصية الإدارة.
"""

class SupportCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.support_prompt = f"""أنت المساعد الذكي لسيرفر !808 ولديك صلاحيات إدارية كاملة لحل المشاكل.
القوانين:
{RULES_TEXT}

يتم تزويدك بسؤال المستخدم، وربما شخص مستهدف (Target) وسبب (Reason).
الخيارات:
1. إذا كان استفساراً عادياً: أجب عليه بلباقة.
2. إذا طلب معاقبة شخص وكان هناك سبب ومخالفة صريحة للقوانين: قرر العقاب.
3. إذا كانت المشكلة خارجة عن إرادتك أو تحتاج تدخلاً بشرياً من الإدارة: قم بفتح تذكرة.

رد بـ JSON فقط بالصيغة التالية:
{{
  "type": "answer" | "action" | "ticket",
  "message": "ردك الذي سيظهر للمستخدم (سواء كإجابة أو كرسالة توضيح لفتح التذكرة أو العقوبة)",
  "action": "timeout_10m" | "kick" | "ban" | "none",
  "ticket_reason": "سبب فتح التذكرة إذا كان type هو ticket (شرح للإدارة)"
}}
حاول دائماً حل المشكلة بأفضل شكل ممكن.
"""

    @app_commands.command(name="support", description="مساعد الإدارة الذكي (لطلب دعم، معاقبة، أو فتح تذكرة)")
    @app_commands.describe(question="ماذا تحتاج؟", member="عضو مستهدف (اختياري)", reason="السبب (اختياري)")
    async def support(self, interaction: discord.Interaction, question: str, member: discord.Member = None, reason: str = None):
        await interaction.response.defer(ephemeral=False, thinking=True)
        
        from shared.ai_client import ai_client
        user_prompt = f"المستخدم: {interaction.user.display_name}\nالطلب: {question}"
        if member:
            user_prompt += f"\nالمستهدف: {member.display_name}"
        if reason:
            user_prompt += f"\nالسبب: {reason}"
            
        try:
            ai_response = await ai_client.chat(self.support_prompt, user_prompt, json_mode=True)
            if not ai_response or ai_response in ("RATE_LIMIT", "SAFETY_FILTER"):
                embed = discord.Embed(
                    description="عذراً، النظام مشغول حالياً. يرجى المحاولة لاحقاً.",
                    color=discord.Color.red()
                )
                return await interaction.followup.send(embed=embed)
                
            data = json.loads(ai_response)
            response_type = data.get("type", "answer")
            msg = data.get("message", "تم استلام الطلب.")
            action = data.get("action", "none")
            ticket_reason = data.get("ticket_reason", "طلب دعم إضافي من المستخدم.")
            
            embed = discord.Embed(description=msg, color=discord.Color.red())
            
            if response_type == "action" and member:
                if member.top_role >= interaction.guild.me.top_role:
                    embed.description += "\n\n❌ لا أملك صلاحية لمعاقبة هذا الشخص."
                else:
                    try:
                        if action == "timeout_10m":
                            await member.timeout(datetime.timedelta(minutes=10), reason="بواسطة الذكاء الاصطناعي")
                        elif action == "kick":
                            await member.kick(reason="بواسطة الذكاء الاصطناعي")
                        elif action == "ban":
                            await member.ban(reason="بواسطة الذكاء الاصطناعي")
                    except discord.Forbidden:
                        embed.description += "\n\n❌ لم أتمكن من تنفيذ العقوبة لعدم وجود صلاحيات."
            
            elif response_type == "ticket":
                # Create a ticket channel
                overwrites = {
                    interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
                
                # إعطاء الصلاحية للرتب الموثوقة (الإدارة)
                for role_name in ["Owner", "Server Administration", "Founder", "Co Founder"]:
                    r = discord.utils.get(interaction.guild.roles, name=role_name)
                    if r:
                        overwrites[r] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                
                ticket_channel = await interaction.guild.create_text_channel(
                    name=f"ticket-{interaction.user.name}",
                    overwrites=overwrites,
                    reason="تم إنشاء التذكرة بواسطة المساعد الذكي"
                )
                
                embed.description += f"\n\n🎫 تم فتح تذكرة لك هنا: {ticket_channel.mention}"
                
                ticket_embed = discord.Embed(
                    title="تذكرة دعم فني",
                    description=f"**السبب الموجه للإدارة:**\n{ticket_reason}",
                    color=discord.Color.red()
                )
                await ticket_channel.send(content=f"{interaction.user.mention}", embed=ticket_embed)
            
            await interaction.followup.send(embed=embed)
            
        except json.JSONDecodeError:
            await interaction.followup.send("❌ حدث خطأ في معالجة قرار الذكاء الاصطناعي.")
        except Exception as e:
            await interaction.followup.send(f"❌ حدث خطأ: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(SupportCog(bot))
