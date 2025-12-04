import asyncio
import sys
import os

# Agregar directorio actual al path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import init_db, AsyncSessionLocal
from models import Categoria, Producto, Tamanio, Extra, CarritoItem, RankingProducto
from sqlalchemy import delete, text

async def reset_menu():
    print("Iniciando limpieza y reinicio del menú...")
    
    async with AsyncSessionLocal() as db:
        try:
            # 1. Limpiar tablas relacionadas con productos
            print("Eliminando datos existentes...")
            
            # Eliminar items de carrito primero (por FK)
            await db.execute(delete(CarritoItem))
            
            # Eliminar rankings
            await db.execute(delete(RankingProducto))
            
            # Eliminar productos
            await db.execute(delete(Producto))
            
            # Eliminar categorías, tamaños y extras
            await db.execute(delete(Categoria))
            await db.execute(delete(Tamanio))
            await db.execute(delete(Extra))
            
            # Reiniciar secuencias de IDs (opcional pero recomendado para limpieza total)
            # Nota: Esto es específico de PostgreSQL
            try:
                await db.execute(text("ALTER SEQUENCE productos_id_seq RESTART WITH 1"))
                await db.execute(text("ALTER SEQUENCE categorias_id_seq RESTART WITH 1"))
                await db.execute(text("ALTER SEQUENCE tamanios_id_seq RESTART WITH 1"))
                await db.execute(text("ALTER SEQUENCE extras_id_seq RESTART WITH 1"))
            except Exception as e:
                print(f"Nota: No se pudieron reiniciar secuencias (posiblemente no es PostgreSQL o permisos insuficientes): {e}")

            print("Datos eliminados correctamente.")
            
            # 2. Crear Categorías Básicas
            print("Creando categorías...")
            cat_pizzas = Categoria(nombre="Pizzas", descripcion="Nuestras deliciosas pizzas artesanales", activo=True)
            cat_bebestibles = Categoria(nombre="Bebestibles", descripcion="Bebidas y jugos refrescantes", activo=True)
            
            db.add(cat_pizzas)
            db.add(cat_bebestibles)
            
            # 3. Crear Tamaños Estándar
            print("Creando tamaños...")
            t_personal = Tamanio(nombre="Personal", precio_adicional=0, activo=True)
            t_mediana = Tamanio(nombre="Mediana", precio_adicional=2000, activo=True)
            t_familiar = Tamanio(nombre="Familiar", precio_adicional=4000, activo=True)
            
            db.add(t_personal)
            db.add(t_mediana)
            db.add(t_familiar)
            
            # 4. Crear Extras Básicos (para que no quede vacío)
            print("Creando extras básicos...")
            e_queso = Extra(nombre="Queso Extra", precio=1000, disponible=True, activo=True)
            e_peperoni = Extra(nombre="Peperoni", precio=1000, disponible=True, activo=True)
            e_champi = Extra(nombre="Champiñones", precio=800, disponible=True, activo=True)
            
            db.add(e_queso)
            db.add(e_peperoni)
            db.add(e_champi)
            
            await db.commit()
            print("¡Menú reiniciado exitosamente!")
            print("- Categorías: Pizzas, Bebestibles")
            print("- Tamaños: Personal, Mediana, Familiar")
            print("- Extras: Queso, Peperoni, Champiñones")
            print("- Productos: 0 (Listo para agregar desde Admin)")
            
        except Exception as e:
            await db.rollback()
            print(f"Error al reiniciar menú: {e}")
            raise e

if __name__ == "__main__":
    asyncio.run(reset_menu())
