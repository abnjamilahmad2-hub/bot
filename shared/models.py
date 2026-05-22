from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from shared.database import Base

class Guild(Base):
    __tablename__ = "guilds"
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(255))
    welcome_message = Column(Text, nullable=True, default="مرحباً بك في السيرفر!")
    bye_message = Column(Text, nullable=True, default="وداعاً، نتمنى لك التوفيق!")
    active_systems = Column(Text, nullable=True, default="guard_ai,level_ai,onboard_ai,event_ai,support_ai")
    welcome_channel_id = Column(BigInteger, nullable=True)
    bye_channel_id = Column(BigInteger, nullable=True)
    events_channel_id = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, index=True)
    global_balance = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class GuildMember(Base):
    __tablename__ = "guild_members"
    user_id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    guild_id = Column(BigInteger, ForeignKey("guilds.id"), primary_key=True)
    level = Column(Integer, default=0)
    characters_typed = Column(Integer, default=0)
    
    user = relationship("User", backref="guild_memberships")
    guild = relationship("Guild", backref="members")

class ModAction(Base):
    __tablename__ = "mod_actions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, ForeignKey("guilds.id"), index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    mod_id = Column(BigInteger)
    action_type = Column(String(50))
    reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
