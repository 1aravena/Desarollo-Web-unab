import asyncio
import sys
import os
from sqlalchemy import delete, text

# 1. Configurar rutas
# Obtener el directorio donde está este script (Entrega Final/test)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Obtener el directorio de la API (Entrega Final/api)
api_dir = os.path.join(os.path.dirname(current_dir), 'api')

# Agregar el directorio de la API al path de Python para poder importar módulos
sys.path.append(api_dir)

# CAMBIAR el directorio de trabajo a la carpeta de la API
# Esto es CRÍTICO para que la base de datos (./pizzeria.db) se encuentre en el lugar correcto
os.chdir(api_dir)
print(f"Directorio de trabajo establecido en: {os.getcwd()}")

# Ahora sí podemos importar los módulos de la API
try:
    from database import init_db, AsyncSessionLocal
    from models import Categoria, Producto, Tamanio, Extra, CarritoItem, RankingProducto
except ImportError as e:
    print(f"Error al importar módulos: {e}")
    print(f"Sys path: {sys.path}")
    sys.exit(1)

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
            # Nota: Esto es específico de PostgreSQL, pero lo dejamos por si acaso se cambia de motor
            # En SQLite no falla, pero tampoco hace nada con esta sintaxis específica usualmente.
            # Para SQLite, el autoincrement se resetea si borras la tabla sqlite_sequence, pero delete() no lo hace.
            try:
                await db.execute(text("DELETE FROM sqlite_sequence WHERE name='productos'"))
                await db.execute(text("DELETE FROM sqlite_sequence WHERE name='categorias'"))
                await db.execute(text("DELETE FROM sqlite_sequence WHERE name='tamanios'"))
                await db.execute(text("DELETE FROM sqlite_sequence WHERE name='extras'"))
            except Exception as e:
                print(f"Nota: No se pudieron reiniciar secuencias (posiblemente no es SQLite): {e}")

            print("Datos eliminados correctamente.")
            
            # 2. Crear Categorías Básicas
            print("Creando categorías...")
            cat_pizzas = Categoria(nombre="Pizzas", descripcion="Nuestras deliciosas pizzas artesanales", activo=True)
            cat_liquidos = Categoria(nombre="Líquidos", descripcion="Bebidas, jugos y refrescos", activo=True)
            
            db.add(cat_pizzas)
            db.add(cat_liquidos)
            
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
            print("- Categorías: Pizzas, Líquidos")
            print("- Tamaños: Personal, Mediana, Familiar")
            print("- Extras: Queso, Peperoni, Champiñones")
            print("- Productos: 0 (Listo para agregar desde Admin)")
            
        except Exception as e:
            await db.rollback()
            print(f"Error al reiniciar menú: {e}")
            raise e

if __name__ == "__main__":
    # En Windows, a veces es necesario configurar el policy del event loop
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(reset_menu())
