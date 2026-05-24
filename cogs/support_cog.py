import discord
from discord.ext import commands
from discord import app_commands
import json
import datetime
from shared.ai_client import ai_client

RULES_TEXT = "احترام الأعضاء, ممنوع التنمر/الصور المسيئة/الترويج/الروابط الخطيرة/السبام/السياسة/انتحال الإدارة."

# رتب الإدارة التي سيتم الإشارة إليها في التذاكر
ADMIN_ROLES = ["Owner", "Server Administration", "Founder", "Co Founder"]

class SupportCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.support_prompt = f"""أنت مساعد !808 الإداري.
القوانين: {RULES_TEXT}
لديك سؤال وربما (مستهدف/Target) و(سبب/Reason).
الخيارات:
1. سؤال عادي: أجب.
2. مخالفة واضحة ومكتملة الأدلة: قرر عقاب.
3. قصة غير واضحة أو تحتاج تفاصيل أكثر أو تدخل إدارة: افتح تذكرة (ticket).
رد بـ JSON فقط:
{{"type": "answer" | "action" | "ticket", "message": "ردك", "action": "timeout_10m" | "timeout_30m" | "timeout_1h" | "kick" | "ban" | "none", "ticket_reason": "السبب"}}"""

        self.ticket_chat_prompt = f"""أنت مساعد !808 الإداري وتتحدث الآن داخل "تذكرة دعم فني" مع مستخدم.
القوانين: {RULES_TEXT}
المهمة:
- تحدث معه بلباقة وحاول فهم المشكلة بالكامل.
- اسأله عن التفاصيل الدقيقة (ماذا حدث؟ من أخطأ؟).
- إذا اقتنعت بأن هناك مخالفة واضحة وتستدعي عقاباً، اتخذ قراراً بمعاقبة المخطئ وإغلاق التذكرة.
- إذا كانت المشكلة قد حُلت، أغلق التذكرة.
- إذا احتجت أن يتدخل إداري بشري، اطلب منه الانتظار.

رد بـ JSON فقط بالصيغة التالية:
{{
  "reply": "كلامك الذي سيرد على المستخدم",
  "action": "none" | "timeout_10m" | "timeout_30m" | "kick" | "ban" | "close_ticket",
  "target_user_id": "إذا كان هناك عقاب، ضع آيدي الشخص المعاقب هنا (إذا عرفته من السياق)، وإلا اتركه فارغاً",
  "reason": "سبب العقاب أو سبب إغلاق التذكرة"
}}"""

    async def _create_ticket(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        mentions = []
        for role_name in ADMIN_ROLES:
            r = discord.utils.get(interaction.guild.roles, name=role_name)
            if r:
                overwrites[r] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                mentions.append(r.mention)
        
        mentions_str = " ".join(mentions)
        
        ticket_channel = await interaction.guild.create_text_channel(
            name=f"ticket-{user.name}",
            overwrites=overwrites,
            reason="تم إنشاء التذكرة بواسطة المساعد الذكي"
        )
        
        embed = discord.Embed(
            title="🎫 تذكرة دعم فني",
            description=f"مرحباً {user.mention}، يرجى شرح قصتك بالكامل والمشكلة التي تواجهها لكي نتمكن من مساعدتك.\n\n**السبب المبدئي:** {reason}",
            color=discord.Color.red()
        )
        await ticket_channel.send(content=f"{mentions_str} | {user.mention}", embed=embed)
        return ticket_channel

    @app_commands.command(name="support", description="مساعد الإدارة الذكي (لطلب دعم، معاقبة، أو فتح تذكرة)")
    @app_commands.describe(question="ماذا تحتاج؟", member="عضو مستهدف (اختياري)", reason="السبب (اختياري)")
    async def support(self, interaction: discord.Interaction, question: str, member: discord.Member = None, reason: str = None):
        await interaction.response.defer(ephemeral=False, thinking=True)
        
        user_prompt = f"المستخدم: {interaction.user.display_name}\nالطلب: {question}"
        if member:
            user_prompt += f"\nالمستهدف: {member.display_name} (ID: {member.id})"
        if reason:
            user_prompt += f"\nالسبب: {reason}"
            
        try:
            ai_response = await ai_client.chat(self.support_prompt, user_prompt, json_mode=True)
            if not ai_response or ai_response in ("RATE_LIMIT", "SAFETY_FILTER"):
                embed = discord.Embed(description="عذراً، النظام مشغول حالياً. يرجى المحاولة لاحقاً.", color=discord.Color.red())
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
                            await member.timeout(datetime.timedelta(minutes=10), reason="الذكاء الاصطناعي")
                        elif action == "timeout_30m":
                            await member.timeout(datetime.timedelta(minutes=30), reason="الذكاء الاصطناعي")
                        elif action == "timeout_1h":
                            await member.timeout(datetime.timedelta(hours=1), reason="الذكاء الاصطناعي")
                        elif action == "kick":
                            await member.kick(reason="الذكاء الاصطناعي")
                        elif action == "ban":
                            await member.ban(reason="الذكاء الاصطناعي")
                    except discord.Forbidden:
                        embed.description += "\n\n❌ لم أتمكن من تنفيذ العقوبة لعدم وجود صلاحيات."
            
            elif response_type == "ticket":
                ticket_channel = await self._create_ticket(interaction, interaction.user, ticket_reason)
                embed.description += f"\n\n🎫 تم فتح تذكرة لك لنتناقش أكثر: {ticket_channel.mention}"
            
            await interaction.followup.send(embed=embed)
            
        except json.JSONDecodeError:
            await interaction.followup.send("❌ حدث خطأ في معالجة قرار الذكاء الاصطناعي.")
        except Exception as e:
            await interaction.followup.send(f"❌ حدث خطأ: {e}")

    @app_commands.command(name="ticket_report", description="فتح تذكرة مباشرة مع الذكاء الاصطناعي للشكوى")
    @app_commands.describe(reason="شرح مبدئي للشكوى أو المشكلة")
    async def ticket_report(self, interaction: discord.Interaction, reason: str):
        await interaction.response.defer(ephemeral=False, thinking=True)
        try:
            ticket_channel = await self._create_ticket(interaction, interaction.user, reason)
            embed = discord.Embed(description=f"🎫 تم فتح تذكرتك هنا: {ticket_channel.mention}", color=discord.Color.red())
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ حدث خطأ: {e}")

    @app_commands.command(name="close", description="إغلاق التذكرة الحالية (فقط داخل قنوات التذاكر)")
    @app_commands.describe(reason="سبب الإغلاق وهل تم الحل؟")
    async def close_ticket(self, interaction: discord.Interaction, reason: str):
        if not interaction.channel.name.startswith("ticket-"):
            embed = discord.Embed(description="❌ هذا الأمر يعمل فقط داخل قنوات التذاكر.", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)
            
        await interaction.response.defer(thinking=True)
        await self._close_ticket_action(interaction.channel, interaction.user, reason)

    async def _close_ticket_action(self, channel: discord.TextChannel, closer: discord.Member, reason: str):
        # البحث عن صاحب التذكرة لإرسال DM
        ticket_owner = None
        for member in channel.members:
            if not member.bot and channel.name == f"ticket-{member.name.lower()}":
                ticket_owner = member
                break
        
        # إذا لم نجده عبر الاسم، نأخذ أول شخص غير بوت لا يحمل رتب الإدارة
        if not ticket_owner:
            for member in channel.members:
                if not member.bot and not any(r.name in ADMIN_ROLES for r in member.roles):
                    ticket_owner = member
                    break

        if ticket_owner:
            dm_embed = discord.Embed(
                title="🔒 تم إغلاق تذكرتك",
                description=f"مرحباً {ticket_owner.mention}، لقد تم إغلاق تذكرتك في سيرفر **{channel.guild.name}**.\n\n"
                            f"**ملخص المشكلة / سبب الإغلاق:**\n{reason}",
                color=discord.Color.red()
            )
            dm_embed.set_footer(text="شكراً لتواصلك معنا.")
            try:
                await ticket_owner.send(embed=dm_embed)
            except discord.Forbidden:
                pass # لا يمكن إرسال خاص
                
        await channel.delete(reason=f"أغلقها {closer.display_name}: {reason}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        
        # التفاعل فقط داخل قنوات التذاكر
        if not message.channel.name.startswith("ticket-"):
            return
            
        # إذا كانت الرسالة من إداري، الذكاء الاصطناعي لا يتدخل لتجنب التداخل
        if any(r.name in ADMIN_ROLES for r in message.author.roles):
            return

        import asyncio
        async with message.channel.typing():
            thinking_msg = await message.reply(".")
            
            async def animate_thinking():
                dots = [".", "..", "..."]
                idx = 0
                while True:
                    try:
                        await asyncio.sleep(0.5)
                        await thinking_msg.edit(content=dots[idx])
                        idx = (idx + 1) % len(dots)
                    except asyncio.CancelledError:
                        break
                    except Exception:
                        pass
                        
            anim_task = asyncio.create_task(animate_thinking())
            
            # إرسال سياق آخر 5 رسائل لفهم القصة
            history = []
            async for msg in message.channel.history(limit=6, before=message):
                if msg.author.id == self.bot.user.id and msg.embeds:
                    history.append(f"الذكاء الاصطناعي: {msg.embeds[0].description}")
                elif msg.author.id == self.bot.user.id:
                    history.append(f"الذكاء الاصطناعي: {msg.content}")
                else:
                    history.append(f"{msg.author.display_name}: {msg.content}")
            
            history.reverse()
            history.append(f"{message.author.display_name}: {message.content}")
            chat_context = "\n".join(history)
            
            reply_text = await ai_client.chat(self.ticket_chat_prompt, chat_context, json_mode=True)
            anim_task.cancel()
            
            try:
                if not reply_text or reply_text in ("RATE_LIMIT", "SAFETY_FILTER"):
                    embed = discord.Embed(description="أنا أواجه ضغطاً في التفكير، سأرد عليك فوراً.", color=discord.Color.red())
                    await thinking_msg.edit(content=None, embed=embed)
                    return

                data = json.loads(reply_text)
                ai_reply = data.get("reply", "أرجو توضيح المزيد.")
                action = data.get("action", "none")
                target_id_str = data.get("target_user_id", "")
                reason = data.get("reason", "الذكاء الاصطناعي")

                embed = discord.Embed(description=ai_reply, color=discord.Color.red())
                await thinking_msg.edit(content=None, embed=embed)
                
                # تنفيذ قرار العقوبة لو قرر البوت
                if action != "none" and action != "close_ticket" and target_id_str:
                    try:
                        target_id = int(target_id_str)
                        member = message.guild.get_member(target_id)
                        if member and member.top_role < message.guild.me.top_role:
                            if action == "timeout_10m":
                                await member.timeout(datetime.timedelta(minutes=10), reason=reason)
                            elif action == "timeout_30m":
                                await member.timeout(datetime.timedelta(minutes=30), reason=reason)
                            elif action == "kick":
                                await member.kick(reason=reason)
                            elif action == "ban":
                                await member.ban(reason=reason)
                            
                            act_embed = discord.Embed(description=f"✅ تم تنفيذ العقوبة المطلوبة على {member.mention}. السبب: {reason}", color=discord.Color.red())
                            await message.channel.send(embed=act_embed)
                    except ValueError:
                        pass
                    except discord.Forbidden:
                        pass
                        
                # إغلاق التذكرة لو قرر البوت
                if action == "close_ticket":
                    await asyncio.sleep(3) # يعطي فرصة للمستخدم لقراءة الرد الأخير
                    await self._close_ticket_action(message.channel, message.guild.me, reason)
                    
            except json.JSONDecodeError:
                embed = discord.Embed(description="حصل خطأ في التفكير، حاول إرسال رسالة أخرى.", color=discord.Color.red())
                await thinking_msg.edit(content=None, embed=embed)
            except discord.NotFound:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(SupportCog(bot))
