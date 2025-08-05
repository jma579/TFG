class Settings:
    DATABASE_URL: str = "sqlite:///aplicacion/base_datos/dev.db"  # SQLite por defecto (desarrollo)
    # Para PostgreSQL sería algo como: postgresql://usuario:contraseña@localhost:5432/tu_bd

settings = Settings()