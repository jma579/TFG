"""
Repository para acceso a datos de la entidad Programa.

Responsabilidades:
- Ejecutar queries SQL mediante SQLAlchemy ORM
- Proporcionar métodos CRUD básicos
- Implementar queries especializadas (filtros, búsquedas)
- NO lanza excepciones HTTP (devuelve None, [], etc.)
- NO contiene lógica de negocio (eso va en Service)
"""

from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import Optional

from database.models import Programa
from backend.constants.enums import TipoPrograma


class ProgramaRepository:
    """
    Repository para operaciones de base de datos sobre Programa.
    
    Patrón Singleton: se crea una única instancia al final del archivo.
    """
    
    # ============================================================
    #  GET BY ID
    # ============================================================
    
    def get_by_id(self, db: Session, programa_id: int) -> Optional[Programa]:
        """
        Obtener programa por ID.
        
        Args:
            db: Sesión de SQLAlchemy
            programa_id: ID del programa a buscar
            
        Returns:
            Objeto Programa si existe, None si no se encuentra
            
        Ejemplo:
            programa = repo.get_by_id(db, 1)
            if programa:
                print(programa.nombre)
            else:
                print("No encontrado")
        """
        return db.query(Programa).filter(Programa.id == programa_id).first()
    

    # ============================================================
    #  QUERY ESPECIALIZADA: Buscar por nombre
    # ============================================================
    
    def get_by_nombre(self, db: Session, nombre: str) -> Optional[Programa]:
        """
        Buscar programa por nombre exacto.
        
        Args:
            db: Sesión de SQLAlchemy
            nombre: Nombre del programa (case-insensitive)
            
        Returns:
            Objeto Programa si existe, None si no se encuentra
            
        Note:
            Si existen múltiples programas con el mismo nombre pero distinto tipo,
            retorna el primero encontrado. Para buscar por nombre+tipo usar
            get_by_nombre_tipo().
            
        SQL generado:
            SELECT * FROM programas 
            WHERE LOWER(nombre) = LOWER('grado en matemáticas')
            LIMIT 1;
            
        Ejemplo:
            programa = repo.get_by_nombre(db, "Grado en Matemáticas")
            if programa:
                print(f"Encontrado: {programa.id}")
        """
        return db.query(Programa).filter(
            Programa.nombre.ilike(nombre)  # Case-insensitive
        ).first()
    

    # ============================================================
    #  QUERY ESPECIALIZADA: Buscar por nombre y tipo
    # ============================================================
    def get_by_nombre_tipo(
        self,
        db: Session,
        nombre: str,
        tipo: TipoPrograma,
    ) -> Optional[Programa]:
        """
        Buscar programa por nombre y tipo.

        Combina ambos campos (nombre, tipo), que son únicos en la tabla
        gracias a la constraint uq_programa_nombre_tipo.

        Args:
            db: Sesión de SQLAlchemy
            nombre: Nombre del programa (case-insensitive)
            tipo: Tipo de programa (GRADO, MASTER, DOBLE_GRADO, etc.)

        Returns:
            Objeto Programa si existe, None si no se encuentra.

        SQL aproximado:
            SELECT * FROM programas
            WHERE LOWER(nombre) = LOWER(:nombre)
              AND tipo = :tipo
            LIMIT 1;
        """
        return (
            db.query(Programa)
            .filter(
                Programa.nombre.ilike(nombre),  # Case-insensitive
                Programa.tipo == tipo,
            )
            .first()
        )
    
    
    # ============================================================
    #  GET MULTI (con filtros y paginación)
    # ============================================================
    
    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        activo: Optional[bool] = None,
        tipo: Optional[TipoPrograma] = None
    ) -> tuple[list[Programa], int]:
        """
        Obtener lista de programas con filtros opcionales y paginación.
        
        Args:
            db: Sesión de SQLAlchemy
            skip: Offset para paginación (número de registros a saltar)
            limit: Límite de registros a devolver
            activo: Filtro opcional por estado activo
            tipo: Filtro opcional por tipo de programa
            
        Returns:
            Tupla (items, total):
                - items: Lista de programas de la página actual
                - total: Número total de registros (sin paginar)
                
        Ejemplo SQL generado (con filtros):
            SELECT * FROM programas 
            WHERE activo = TRUE AND tipo = 'GRADO'
            OFFSET 10 LIMIT 5;
            
        Uso:
            # Obtener página 2 (10 items por página) de programas activos
            items, total = repo.get_multi(db, skip=10, limit=10, activo=True)
            print(f"Mostrando 10 de {total} programas")
        """
        # 1. Construir query base
        query = db.query(Programa)
        
        # 2. Aplicar filtros dinámicos
        if activo is not None:
            query = query.filter(Programa.activo == activo)
        if tipo is not None:
            query = query.filter(Programa.tipo == tipo)

        # 3. Orden predecible
        query = query.order_by(
            Programa.nombre.asc(),
            Programa.tipo.asc()
        )
        
        # 4. Contar total ANTES de paginar (para metadatos de paginación)
        total = query.count()

        # 5. Aplicar paginación y ejecutar
        items = query.offset(skip).limit(limit).all()
        
        return items, total
    
    
    # ============================================================
    #  CREATE
    # ============================================================
    
    def create(self, db: Session, programa_data: dict) -> Programa:
        """
        Crear nuevo programa en la base de datos.
        
        Args:
            db: Sesión de SQLAlchemy
            programa_data: Diccionario con los datos del programa
                          Ejemplo: {"nombre": "Grado Mat", "tipo": TipoPrograma.GRADO}
            
        Returns:
            Objeto Programa creado (con ID generado por la DB)
            
        Flujo:
            1. Crear objeto ORM desde dict
            2. Añadir a la sesión (db.add)
            3. Commit (INSERT SQL)
            4. Refresh (SELECT para obtener ID autogenerado)
            5. Devolver objeto completo
            
        SQL generado:
            INSERT INTO programas (nombre, tipo, activo) 
            VALUES ('Grado Mat', 'GRADO', TRUE);
            
        Uso:
            data = {"nombre": "Test", "tipo": TipoPrograma.GRADO, "activo": True}
            programa = repo.create(db, data)
            print(programa.id)  # 1 (generado por DB)
        """
        # 1. Crear objeto SQLAlchemy desde diccionario
        db_programa = Programa(**programa_data)
        
        # 2. Añadir a la sesión (no persiste aún)
        db.add(db_programa)
        
        # 3. Commit: ejecuta INSERT SQL
        db.commit()
        
        # 4. Refresh: recarga el objeto desde DB para obtener ID y defaults
        db.refresh(db_programa)
        
        return db_programa
    
    
    # ============================================================
    #  UPDATE
    # ============================================================
    
    def update(
        self, 
        db: Session, 
        programa: Programa, 
        update_data: dict
    ) -> Programa:
        """
        Actualizar programa existente.
        
        Args:
            db: Sesión de SQLAlchemy
            programa: Objeto Programa a actualizar (ya cargado desde DB)
            update_data: Diccionario con campos a actualizar
                        Solo se actualizan campos presentes (no-None)
            
        Returns:
            Objeto Programa actualizado
            
        Flujo:
            1. Iterar sobre update_data
            2. Actualizar atributos del objeto ORM
            3. Commit (UPDATE SQL)
            4. Refresh (recargar desde DB)
            
        SQL generado (ejemplo):
            UPDATE programas 
            SET nombre = 'Nuevo nombre', activo = FALSE
            WHERE id = 1;
            
        Uso:
            programa = repo.get_by_id(db, 1)
            update_data = {"nombre": "Nuevo nombre", "activo": False}
            programa = repo.update(db, programa, update_data)
        """
        # 1. Actualizar solo campos presentes en update_data
        for key, value in update_data.items():
            if value is not None:  # Solo actualizar si no es None
                setattr(programa, key, value)
        
        # 2. Commit: ejecuta UPDATE SQL
        db.commit()
        
        # 3. Refresh: recargar desde DB
        db.refresh(programa)
        
        return programa
    
    
    # ============================================================
    #  DELETE (SOFT)
    # ============================================================
    
    def delete(self, db: Session, programa_id: int) -> bool:
        """
        Soft delete: marcar programa como inactivo.
        
        No borra físicamente el registro (para mantener trazabilidad).
        Solo actualiza el campo 'activo' a False.
        
        Args:
            db: Sesión de SQLAlchemy
            programa_id: ID del programa a desactivar
            
        Returns:
            True si se desactivó correctamente
            False si el programa no existe
            
        SQL generado:
            UPDATE programas 
            SET activo = FALSE 
            WHERE id = 1;
            
        Uso:
            success = repo.delete(db, 1)
            if success:
                print("Programa desactivado")
            else:
                print("Programa no encontrado")
        """
        # 1. Buscar programa
        programa = self.get_by_id(db, programa_id)
        
        # 2. Si no existe, devolver False
        if not programa:
            return False
        
        # 3. Marcar como inactivo
        programa.activo = False
        
        # 4. Commit
        db.commit()
        
        return True
    
    
    # ============================================================
    #  QUERY ESPECIALIZADA: Verificar unicidad
    # ============================================================
    
    def exists_by_nombre_tipo(
        self, 
        db: Session, 
        nombre: str, 
        tipo: TipoPrograma,
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        Verificar si existe un programa con el mismo nombre y tipo.
        
        Se usa para validar el constraint único (nombre, tipo) antes de crear/actualizar.
        
        Args:
            db: Sesión de SQLAlchemy
            nombre: Nombre del programa a verificar
            tipo: Tipo del programa a verificar
            exclude_id: (Opcional) ID a excluir de la búsqueda
                       Útil en UPDATE para no contar el registro actual
            
        Returns:
            True si existe otro programa con ese (nombre, tipo)
            False si no existe
            
        SQL generado:
            -- Sin exclude_id:
            SELECT 1 FROM programas 
            WHERE nombre = 'Grado Mat' AND tipo = 'GRADO'
            LIMIT 1;
            
            -- Con exclude_id=5:
            SELECT 1 FROM programas 
            WHERE nombre = 'Grado Mat' AND tipo = 'GRADO' AND id != 5
            LIMIT 1;
            
        Uso:
            # En CREATE: verificar si existe
            if repo.exists_by_nombre_tipo(db, "Grado Mat", TipoPrograma.GRADO):
                raise Exception("Ya existe")
            
            # En UPDATE: verificar si existe OTRO con ese nombre
            if repo.exists_by_nombre_tipo(db, "Grado Mat", TipoPrograma.GRADO, exclude_id=1):
                raise Exception("Ya existe otro programa con ese nombre")
        """
        # 1. Construir query con condiciones AND
        query = db.query(Programa).filter(
            and_(
                Programa.nombre == nombre,
                Programa.tipo == tipo
            )
        )
        
        # 2. Si es UPDATE, excluir el registro actual
        if exclude_id is not None:
            query = query.filter(Programa.id != exclude_id)
        
        # 3. Verificar si existe algún resultado
        # .first() devuelve el objeto o None
        # is not None convierte a bool
        return query.first() is not None


# ============================================================
#  SINGLETON: Instancia única del repositorio
# ============================================================

programa_repository = ProgramaRepository()
"""
Instancia singleton del repositorio.

Se usa así en services:
    from backend.modules.catalogo.repositories.programa_repo import programa_repository
    
    programa = programa_repository.get_by_id(db, 1)
"""