import sqlite3
import os

# Obtener la ruta de la base de datos
current_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_dir, 'database.db')

def inspect_database():
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Crear archivo de salida
        output_file = os.path.join(current_dir, 'esquema_db.txt')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Obtener todas las tablas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            output_line = "🔍 TABLAS ENCONTRADAS:"
            f.write(output_line + "\n")
            
            separator = "=" * 50
            f.write(separator + "\n")
            
            for table in tables:
                table_name = table[0]
                table_line = f"\n📋 Tabla: {table_name}"
                f.write(table_line + "\n")
                
                # Obtener la estructura de cada tabla
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                columns_header = "  Columnas:"
                f.write(columns_header + "\n")
                
                for col in columns:
                    col_id, name, col_type, not_null, default, pk = col
                    pk_str = " (PK)" if pk else ""
                    not_null_str = " NOT NULL" if not_null else ""
                    default_str = f" DEFAULT {default}" if default else ""
                    col_line = f"    - {name}: {col_type}{pk_str}{not_null_str}{default_str}"
                    f.write(col_line + "\n")
            
            # Obtener las claves foráneas
            fk_header = "\n🔗 CLAVES FORÁNEAS:"
            f.write(fk_header + "\n")
            
            f.write(separator + "\n")
            
            for table in tables:
                table_name = table[0]
                cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                fks = cursor.fetchall()
                
                if fks:
                    fk_table_line = f"\n📋 {table_name}:"
                    f.write(fk_table_line + "\n")
                    for fk in fks:
                        id_fk, seq, ref_table, from_col, to_col, on_update, on_delete, match = fk
                        fk_line = f"    {from_col} -> {ref_table}.{to_col}"
                        f.write(fk_line + "\n")
        
        conn.close()
        print(f"📄 Esquema guardado en: {output_file}")
        
    except Exception as e:
        print(f"❌ Error al inspeccionar la base de datos: {e}")

if __name__ == "__main__":
    inspect_database()
