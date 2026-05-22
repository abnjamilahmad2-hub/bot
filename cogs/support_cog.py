import discord
from discord.ext import commands
import json
import asyncio
from shared.ai_client import ai_client

class SupportCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.support_prompt = """أنت المساعد الفني والإداري الذكي (Support AI) لسيرفر The Sanctuary. لديك صلاحيات مطلقة!
مهمتك: قراءة مشكلة المستخدم ومحاولة حلها فوراً بناءً على خبرتك. إذا لزم الأمر، يمكنك تنفيذ إجراءات نظامية.
يجب أن ترد بصيغة JSON فقط، بدون أي نصوص إضافية خارج الـ JSON:
{
  "resolved": true|false, 
  "reply": "الرد الموجه للمستخدم", 
  "action": "none|remove_user|block_user|mute_user|delete_messages",
  "target_user_id": "رقم الأيدي إذا كان الإجراء يستهدف مستخدم",
  "amount": "رقم إذا كان الإجراء delete_messages"
}
اختر resolved: true إذا كان حلك كافياً، و false إذا كانت المشكلة تتطلب تدخل بشري لا يمكنك فعله."""

    @discord.app_commands.command(name="support", description="افتح تذكرة دعم فني وسيحاول الذكاء الاصطناعي مساعدتك أو حلها فوراً")
    @discord.app_commands.describe(issue="وصف المشكلة التي تواجهها", target_user="مستخدم متعلق بالمشكلة (اختياري)")
    async def support_command(self, interaction: discord.Interaction, issue: str, target_user: discord.Member = None):
        await interaction.response.send_message("يتم الآن تحليل مشكلتك وتنفيذ الإجراءات اللازمة...", ephemeral=True)
        
        target_info = f"المستخدم المستهدف: {target_user.name} (ID: {target_user.id})" if target_user else "لا يوجد مستخدم مستهدف."
        user_prompt = f"صاحب المشكلة: {interaction.user.name}\nالمشكلة: {issue}\n{target_info}"
        
        try:
            # إغلاق الـ json_mode لحل مشكلة الموديلات المجانية التي ترفض الطلب
            response = await ai_client.chat(self.support_prompt, user_prompt, json_mode=False)
            if response == "RATE_LIMIT":
                await interaction.edit_original_response(content="⚠️ لقد تجاوزت الحد المسموح للاستخدام المجاني للذكاء الاصطناعي (Rate Limit) حالياً بسبب ضغط الطلبات. الرجاء المحاولة بعد بضع دقائق.")
                return
            if not response or response == "SAFETY_FILTER":
                # إذا حدث بلوك من الموديل، سنتجاهل الفلتر ونصنع رد افتراضي يحولها للإدارة لكي لا يرى المستخدم أي طبقة حماية
                response = '{"resolved": false, "reply": "استلمت طلبك وسأقوم بتحويله للإدارة فوراً للتعامل معه.", "action": "none"}'
                
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.startswith("```"):
                clean_response = clean_response[3:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()
                
            try:
                data = json.loads(clean_response)
            except json.JSONDecodeError:
                await interaction.edit_original_response(content="حدث خطأ في استيعاب الرد الذكي. الرجاء التواصل مع الإدارة.")
                return
                
            resolved = data.get("resolved")
            reply = data.get("reply", "تم اتخاذ الإجراء.")
            action = data.get("action", "none")
            
            # تنفيذ الإجراءات
            action_result = ""
            if action != "none":
                try:
                    if action == "remove_user" and target_user:
                        await target_user.kick(reason="بواسطة Support AI")
                        action_result = "تم طرد المستخدم بنجاح."
                    elif action == "block_user" and target_user:
                        await target_user.ban(reason="بواسطة Support AI")
                        action_result = "تم حظر المستخدم بنجاح."
                    elif action == "mute_user" and target_user:
                        import datetime
                        await target_user.timeout(datetime.timedelta(minutes=10), reason="بواسطة Support AI")
                        action_result = "تم كتم المستخدم لمدة 10 دقائق."
                    elif action == "delete_messages":
                        amount = int(data.get("amount", 5))
                        await interaction.channel.purge(limit=amount)
                        action_result = f"تم مسح {amount} رسائل."
                except discord.Forbidden:
                    action_result = "ليس لدي صلاحيات كافية لتنفيذ هذا الإجراء."
                except Exception as e:
                    action_result = f"حدث خطأ أثناء التنفيذ: {e}"
            
            if resolved:
                msg = f"💡 **الرد الذكي السريع:**\n{reply}\n\n*نتيجة التنفيذ:* {action_result}\n\n*إذا لم يحل هذا مشكلتك، يمكنك طلب التحدث مع الإدارة.*"
                await interaction.edit_original_response(content=msg)
            else:
                msg = f"🤖 **الرد الذكي:**\n{reply}\n\n*نتيجة التنفيذ:* {action_result}\n\n⚠️ **جاري تحويل تذكرتك لفريق الإدارة ليتم التدخل البشري.**"
                await interaction.edit_original_response(content=msg)
                
                if isinstance(interaction.channel, discord.TextChannel):
                    thread = await interaction.channel.create_thread(
                        name=f"تذكرة دعم: {interaction.user.name}",
                        type=discord.ChannelType.public_thread,
                        reason="دعم فني"
                    )
                    await thread.send(f"إشعار للإدارة: {interaction.user.mention} بحاجة للمساعدة!\n**المشكلة:** {issue}\n**رد الذكاء الاصطناعي:** {reply}\n**تنفيذ النظام:** {action_result}")
                
        except Exception as e:
            await interaction.edit_original_response(content=f"حدث خطأ أثناء الاتصال بالدعم الذكي: {e}")

    @support_command.error
    async def support_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        if isinstance(error, discord.app_commands.errors.TransformerError):
            await interaction.response.send_message("❌ الرجاء منشنة المستخدم بشكل صحيح أو عدم كتابة أي شيء إذا لم يكن هناك مستخدم مستهدف.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ حدث خطأ: {error}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(SupportCog(bot))
