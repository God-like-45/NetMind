import asyncio
import os
from netmind.db.session import init_db, get_session_factory
from netmind.models.base import User
from netmind.core.security import get_password_hash

async def seed_users():
    await init_db()
    factory = get_session_factory()
    async with factory() as session:
        # Check if admin exists
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.email == "admin@netmind.local"))
        admin = result.scalars().first()
        
        if not admin:
            print("Creating default admin user...")
            admin = User(
                email="admin@netmind.local",
                full_name="System Admin",
                hashed_password=get_password_hash("admin123"),
                role="ADMIN",
                is_active=True
            )
            session.add(admin)
            
            operator = User(
                email="operator@netmind.local",
                full_name="NOC Operator",
                hashed_password=get_password_hash("operator123"),
                role="OPERATOR",
                is_active=True
            )
            session.add(operator)
            
            await session.commit()
            print("Users created successfully.")
        else:
            print("Users already exist.")

if __name__ == "__main__":
    asyncio.run(seed_users())
