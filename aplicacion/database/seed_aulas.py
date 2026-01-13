"""
Script de sembrado (seeder) para poblar la tabla de Aulas.

Formas de ejecución:
1. Desde la raíz del proyecto (D:\\TFG):
   python aplicacion/database/seed_aulas.py

2. Desde el directorio aplicacion/database:
   python seed_aulas.py

El script detecta automáticamente si las aulas ya existen y evita duplicados.
"""
import sys
import os

# Configurar el Path para que Python encuentre los módulos necesarios
# Añadir el directorio backend al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend'))
# Añadir el directorio aplicacion al path para acceder a database
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import Session
from backend.db.session import SessionLocal
from database.models import Aula
from backend.constants.enums import TipoAula

# Definición de datos extraídos de las imágenes
# Formato: (Nombre, Código, Tipo, Capacidad)
AULAS_DATA = [
    # --- AULAS DE TEORÍA (Imagen de lista azul) ---
    ("AULA 1", "A1", TipoAula.TEORICA, 132),
    ("AULA 2", "A2", TipoAula.TEORICA, 126),
    ("AULA 3", "A3", TipoAula.TEORICA, 30),
    ("AULA 4", "A4", TipoAula.TEORICA, 80),
    ("AULA 5", "A5", TipoAula.TEORICA, 32),
    ("AULA 6", "A6", TipoAula.TEORICA, 40),
    ("AULA 7", "A7", TipoAula.TEORICA, 60),
    ("AULA 8", "A8", TipoAula.TEORICA, 58),
    ("AULA 9", "A9", TipoAula.TEORICA, 40),
    ("AULA 10", "A10", TipoAula.TEORICA, 24),
    ("AULA 11", "A11", TipoAula.TEORICA, 32),
    ("AULA 12", "A12", TipoAula.TEORICA, 32),
    ("AULA 13", "A13", TipoAula.TEORICA, 60),
    ("AULA 14", "A14", TipoAula.TEORICA, 92),
    ("AULA 15", "A15", TipoAula.TEORICA, 16),
    ("AULA L4", "AL4", TipoAula.TEORICA, 51),
    
    # --- AULA MAGNA ---
    ("Aula Magna", "MAGNA", TipoAula.TEORICA, 297),

    # --- LABORATORIOS (Simulación, ATC, Tiempo Real) ---
    ("Laboratorio de Simulación 1", "LAB_SIM1", TipoAula.LABORATORIO, 42),
    ("Laboratorio de Simulación 2", "LAB_SIM2", TipoAula.LABORATORIO, 25),
    ("Laboratorio de Simulación 3", "LAB_SIM3", TipoAula.LABORATORIO, 42),
    ("Laboratorio ATC", "LAB_ATC", TipoAula.LABORATORIO, 24),
    ("Laboratorio en Tiempo Real", "LAB_TR", TipoAula.LABORATORIO, 20), # Capacidad estimada

    # --- LABORATORIOS (Física, Electrónica, Mecánica) ---
    ("Laboratorio de Física Experimental", "LAB_FIS", TipoAula.LABORATORIO, 38),
    ("Laboratorio de Electrónica Básica", "LAB_ELEC", TipoAula.LABORATORIO, 20),
    ("Laboratorio de Mecánica", "LAB_MEC", TipoAula.LABORATORIO, 16), # 8 puestos dobles estimados

    # --- SEMINARIOS (Mapeados desde Sala de Grados) ---
    # Nota: Usamos capacidad 42 (Sala de Grados) para estos 3 según instrucciones.
    ("Seminario de Informática", "SEM_INF", TipoAula.SEMINARIO, 42), 
    ("Seminario de Física", "SEM_FIS", TipoAula.SEMINARIO, 42),
    ("Seminario de Matemáticas", "SEM_MAT", TipoAula.SEMINARIO, 42),
]

def seed_aulas():
    db: Session = SessionLocal()
    try:
        print("🌱 Iniciando sembrado de Aulas...")
        count_new = 0
        count_existing = 0

        for nombre, codigo, tipo, capacidad in AULAS_DATA:
            # Verificar si existe por código (clave única lógica)
            aula_existente = db.query(Aula).filter(Aula.codigo == codigo).first()

            if aula_existente:
                print(f"   ℹ️  Saltando {nombre} ({codigo}): Ya existe.")
                count_existing += 1
            else:
                # Crear nueva aula
                nueva_aula = Aula(
                    nombre=nombre,
                    codigo=codigo,
                    tipo=tipo,
                    capacidad=capacidad,
                    activo=True
                )
                db.add(nueva_aula)
                print(f"   ✅ Creando {nombre} ({codigo}) - Cap: {capacidad}")
                count_new += 1

        db.commit()
        print("\n" + "="*50)
        print(f"🎉 Proceso finalizado.")
        print(f"   Nuevas aulas: {count_new}")
        print(f"   Aulas existentes: {count_existing}")
        print("="*50)

    except Exception as e:
        print(f"❌ Error durante el sembrado: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_aulas()