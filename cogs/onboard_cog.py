import discord
from discord.ext import commands
import json
from shared.ai_client import ai_client
from shared.database import get_db_session
from shared.models import Guild
from sqlalchemy import select

class OnboardCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.pending_users = {}
        self.onboard_prompt = """أنت محقق الترحيب الذكي (Onboard AI) في The Sanctuary.
مهمتك: توليد سؤال بسيط جداً ومضحك للتحقق من أن العضو الجديد إنسان وليس روبوتاً.
السؤال يجب أن يكون باللغة العربية. مثال: "كم عدد أرجل القطة؟" أو "هل السمك يطير؟"
رد بالسؤال فقط دون أي إضافات أخرى."""
        self.verify_prompt = """أنت محقق التحقق من الهوية.
بناءً على السؤال المطروح وإجابة المستخدم، حدد ما إذا كانت الإجابة صحيحة ومنطقية تدل على أنه إنسان وليس روبوت غبي.
يجب أن ترد بصيغة JSON فقط، بدون أي نصوص خارجية:
{"is_human": true|false, "reason": "سبب الموافقة أو الرفض باختصار"}"""

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        async for session in get_db_session():
            stmt_guild = select(Guild).where(Guild.id == member.guild.id)
            guild_record = (await session.execute(stmt_guild)).scalar_one_or_none()
            if not guild_record or "onboard_ai" not in str(guild_record.active_systems):
                return
            welcome_channel_id = guild_record.welcome_channel_id
                
        try:
            # Not using JSON mode here because it expects plain text
            question = await ai_client.chat(self.onboard_prompt, "أعطني سؤال تحقق لهذا العضو الجديد.", json_mode=False)
            if question:
                self.pending_users[member.id] = {"question": question, "guild_id": member.guild.id}
                
                guild = member.guild
                channel = guild.get_channel(welcome_channel_id) if welcome_channel_id else guild.system_channel
                if not channel:
                    channel = next((c for c in guild.text_channels if c.name == "عام" or c.name == "general"), None)
                
                if channel:
                    await channel.send(f"مرحباً {member.mention} في الملاذ! للتحقق من هويتك كإنسان، أجب على هذا السؤال هنا:\n**{question}**\n\n(اكتب إجابتك مباشرة في هذه القناة)")
        except Exception as e:
            print(f"[Onboard AI Error] {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.author.id not in self.pending_users:
            return
            
        user_data = self.pending_users[message.author.id]
        if message.guild and message.guild.id != user_data["guild_id"]:
            return
            
        question = user_data["question"]
        guild_id = user_data["guild_id"]
        user_prompt = f"السؤال كان: {question}\nإجابة المستخدم: {message.content}"
        
        try:
            # We don't use json_mode=True to prevent 400 errors
            response = await ai_client.chat(self.verify_prompt, user_prompt, json_mode=False)
            if not response: return
            
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.startswith("```"):
                clean_response = clean_response[3:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()
            
            data = json.loads(clean_response)
            if data.get("is_human"):
                del self.pending_users[message.author.id]
                await message.reply(f"✅ تحقق ناجح! {data.get('reason')}\nلقد تم إثبات أنك إنسان وتم السماح لك بالدخول بشكل كامل.")
                
                guild = self.bot.get_guild(guild_id)
                if guild:
                    member = guild.get_member(message.author.id)
                    if member:
                        role = discord.utils.get(guild.roles, name="Verified")
                        if role:
                            await member.add_roles(role)
            else:
                await message.reply(f"❌ إجابة خاطئة! {data.get('reason')}\nحاول مرة أخرى.")
        except Exception as e:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(OnboardCog(bot))
