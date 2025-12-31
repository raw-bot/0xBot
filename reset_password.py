import asyncio
import os
import sys

# Add backend/src to path so we can import modules
sys.path.append(os.path.join(os.getcwd(), "backend"))

from sqlalchemy import select

from backend.src.core.database import AsyncSessionLocal
from backend.src.models.user import User
from backend.src.routes.auth import hash_password


async def reset_password():
    email = "demo@nof1.com"
    new_password = "Demo1234!"

    print(f"Resetting password for {email} to {new_password}...")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            print(f"User {email} not found! Creating...")
            user = User(email=email, password_hash=hash_password(new_password))
            db.add(user)
            await db.commit()
            print("User created successfully.")
            return

        print(f"User found: {user.id}")
        user.password_hash = hash_password(new_password)
        await db.commit()
        print("Password updated successfully.")


if __name__ == "__main__":
    asyncio.run(reset_password())
