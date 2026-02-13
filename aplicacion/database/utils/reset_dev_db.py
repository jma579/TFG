from db.session import drop_tables, create_tables, engine


def reset_db() -> None:
    print(f"⚠️ Esto va a ELIMINAR todas las tablas en: {engine.url}")
    confirm = input("Escribe 'RESET' para continuar: ")
    if confirm != "RESET":
        print("Operacion cancelada.")
        return
    drop_tables()
    create_tables()
    print("✅ Esquema de base de datos reseteado (tablas vacías).")


if __name__ == "__main__":
    reset_db()
