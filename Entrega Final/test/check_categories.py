import asyncio
import sys
import os
from sqlalchemy import select

# Configurar path
current_dir = os.path.dirname(os.path.abspath(__file__))
api_dir = os.path.join(os.path.dirname(current_dir), 'api')
sys.path.append(api_dir)
os.chdir(api_dir)

from database import AsyncSessionLocal
from models import Categoria

async def check_categories():
    print(f"Verificando base de datos en: {os.getcwd()}")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Categoria))
        categorias = result.scalars().all()
        
        print(f"Total categorías encontradas: {len(categorias)}")
        for cat in categorias:
            print(f"ID: {cat.id}, Nombre: {cat.nombre}, Activo: {cat.activo}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_categories())
