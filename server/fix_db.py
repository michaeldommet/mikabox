import asyncio
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models import Base, User, ChildProfile, Device
from app.config import settings

engine = create_async_engine(settings.database_url)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def fix():
    async with SessionLocal() as db:
        # Find user
        result = await db.execute(select(User).where(User.email == 'michaeldommet@hotmail.com'))
        user = result.scalar_one_or_none()
        if not user:
            print("User not found")
            return
            
        # Ensure child profile exists
        result = await db.execute(select(ChildProfile).where(ChildProfile.user_id == user.id))
        if not result.scalars().first():
            print("Creating child profile...")
            profile = ChildProfile(user_id=user.id, name="Kiddo", age=5, avatar="🐻")
            db.add(profile)
            
        # Ensure device mikabox-001 is paired
        result = await db.execute(select(Device).where(Device.user_id == user.id))
        if not result.scalars().first():
            print("Pairing device...")
            device = Device(user_id=user.id, device_id="mikabox-001", name="MikaBox", pairing_token=str(uuid.uuid4()))
            db.add(device)
            
        await db.commit()
        print("Done!")

asyncio.run(fix())
