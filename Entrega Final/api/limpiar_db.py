"""
Script para limpiar la base de datos
Elimina todos los datos excepto las cuentas admin y cocina
"""
import sqlite3
import os

# Ruta a la base de datos
DB_PATH = os.path.join(os.path.dirname(__file__), 'pizzeria.db')

def limpiar_base_datos():
    print("=" * 50)
    print("🧹 LIMPIEZA DE BASE DE DATOS - La Fornace")
    print("=" * 50)
    
    if not os.path.exists(DB_PATH):
        print("❌ No se encontró la base de datos en:", DB_PATH)
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Obtener IDs de admin y cocina
        cursor.execute("""
            SELECT id, email, nombre, rol FROM usuarios 
            WHERE rol IN ('admin', 'administrador', 'cocinero', 'cocina')
        """)
        usuarios_protegidos = cursor.fetchall()
        
        if not usuarios_protegidos:
            print("⚠️  No se encontraron cuentas admin o cocina.")
            print("   Buscando todos los usuarios...")
            cursor.execute("SELECT id, email, nombre, rol FROM usuarios")
            todos = cursor.fetchall()
            for u in todos:
                print(f"   - ID:{u[0]} | {u[1]} | {u[2]} | rol:{u[3]}")
            return
        
        print("\n✅ Cuentas que se CONSERVARÁN:")
        ids_protegidos = []
        for u in usuarios_protegidos:
            print(f"   - ID:{u[0]} | {u[1]} | {u[2]} | rol:{u[3]}")
            ids_protegidos.append(u[0])
        
        # Contar datos antes de limpiar
        print("\n📊 Datos ANTES de limpiar:")
        tablas_datos = [
            ('usuarios', 'Usuarios totales'),
            ('pedidos', 'Pedidos'),
            ('carritos', 'Carritos'),
            ('carrito_items', 'Items de carrito'),
            ('solicitudes_anulacion', 'Solicitudes de anulación'),
            ('reembolsos', 'Reembolsos'),
            ('cola_impresion', 'Cola de impresión'),
            ('emails_confirmacion', 'Emails de confirmación'),
            ('preferencias_promo', 'Preferencias promocionales'),
            ('campanias_segmentadas', 'Campañas'),
            ('ranking_productos', 'Rankings'),
            ('pdf_exports', 'PDFs exportados'),
        ]
        
        for tabla, nombre in tablas_datos:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                count = cursor.fetchone()[0]
                print(f"   - {nombre}: {count}")
            except:
                pass
        
        # Confirmar
        print("\n" + "=" * 50)
        respuesta = input("⚠️  ¿Desea continuar con la limpieza? (s/n): ")
        if respuesta.lower() != 's':
            print("❌ Operación cancelada.")
            return
        
        print("\n🗑️  Limpiando datos...")
        
        # Orden de eliminación (respetando foreign keys)
        # 1. Eliminar reembolsos
        cursor.execute("DELETE FROM reembolsos")
        print(f"   ✓ Reembolsos eliminados: {cursor.rowcount}")
        
        # 2. Eliminar solicitudes de anulación
        cursor.execute("DELETE FROM solicitudes_anulacion")
        print(f"   ✓ Solicitudes de anulación eliminadas: {cursor.rowcount}")
        
        # 3. Eliminar cola de impresión
        cursor.execute("DELETE FROM cola_impresion")
        print(f"   ✓ Cola de impresión eliminada: {cursor.rowcount}")
        
        # 4. Eliminar emails de confirmación
        cursor.execute("DELETE FROM emails_confirmacion")
        print(f"   ✓ Emails de confirmación eliminados: {cursor.rowcount}")
        
        # 5. Eliminar pedidos (de usuarios no protegidos)
        cursor.execute("DELETE FROM pedidos")
        print(f"   ✓ Pedidos eliminados: {cursor.rowcount}")
        
        # 6. Eliminar items de carrito (de usuarios no protegidos)
        cursor.execute("""
            DELETE FROM carrito_items WHERE carrito_id IN (
                SELECT id FROM carritos WHERE user_id NOT IN ({})
            )
        """.format(','.join('?' * len(ids_protegidos))), ids_protegidos)
        print(f"   ✓ Items de carrito eliminados: {cursor.rowcount}")
        
        # 7. Eliminar carritos (de usuarios no protegidos)
        cursor.execute("""
            DELETE FROM carritos WHERE user_id NOT IN ({})
        """.format(','.join('?' * len(ids_protegidos))), ids_protegidos)
        print(f"   ✓ Carritos eliminados: {cursor.rowcount}")
        
        # 8. Eliminar preferencias promo (de usuarios no protegidos)
        cursor.execute("""
            DELETE FROM preferencias_promo WHERE cliente_id NOT IN ({})
        """.format(','.join('?' * len(ids_protegidos))), ids_protegidos)
        print(f"   ✓ Preferencias promocionales eliminadas: {cursor.rowcount}")
        
        # 9. Eliminar campañas
        cursor.execute("DELETE FROM campanias_segmentadas")
        print(f"   ✓ Campañas eliminadas: {cursor.rowcount}")
        
        # 10. Eliminar rankings
        cursor.execute("DELETE FROM ranking_productos")
        print(f"   ✓ Rankings eliminados: {cursor.rowcount}")
        
        # 11. Eliminar PDFs exportados
        cursor.execute("DELETE FROM pdf_exports")
        print(f"   ✓ PDFs exportados eliminados: {cursor.rowcount}")
        
        # 12. Eliminar usuarios NO protegidos
        cursor.execute("""
            DELETE FROM usuarios WHERE id NOT IN ({})
        """.format(','.join('?' * len(ids_protegidos))), ids_protegidos)
        print(f"   ✓ Usuarios eliminados: {cursor.rowcount}")
        
        # Commit cambios
        conn.commit()
        
        # Vacuum para reducir tamaño del archivo
        print("\n🔧 Optimizando base de datos...")
        cursor.execute("VACUUM")
        
        # Mostrar resultado final
        print("\n📊 Datos DESPUÉS de limpiar:")
        for tabla, nombre in tablas_datos:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                count = cursor.fetchone()[0]
                print(f"   - {nombre}: {count}")
            except:
                pass
        
        print("\n" + "=" * 50)
        print("✅ ¡Limpieza completada exitosamente!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Error durante la limpieza: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    limpiar_base_datos()
