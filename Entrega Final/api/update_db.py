import asyncio
from database import init_db

async def main():
    print("Actualizando esquema de base de datos...")
    await init_db()
    print("Base de datos actualizada correctamente.")

if __name__ == "__main__":
    asyncio.run(main())
