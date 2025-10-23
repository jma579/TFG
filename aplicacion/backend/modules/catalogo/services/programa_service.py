"""
Service para la lógica de negocio de la entidad Programa.

Responsabilidades:
- Implementar casos de uso (operaciones de negocio)
- Validar reglas de dominio
- Orquestar llamadas a repositorios
- Manejar excepciones y errores HTTP
- Transformar entre Models (SQLAlchemy) y Schemas (Pydantic)
"""

from sqlalchemy.orm import Session
from typing import Optional
from fastapi import HTTPException, status

from backend.modules.catalogo.repositories.programa_repo import programa_repository
from backend.modules.catalogo.schemas.programa import (
    ProgramaCreate, 
    ProgramaUpdate, 
    ProgramaOut, 
    ProgramaList
)
from backend.constants.enums import TipoPrograma


class ProgramaService:
    """
    Service para gestionar la lógica de negocio de Programas.
    
    Patrón: Repository → Service → Router
    - Repository: acceso a datos (queries SQL)
    - Service: lógica de negocio (validaciones, orquestación)
    - Router: endpoints REST (validación entrada, serialización)
    """
    
    def __init__(self):
        """
        Inicializar service con dependencia del repository.
        
        El repository se inyecta aquí (Dependency Injection manual).
        """
        self.repo = programa_repository
    
    
    # ============================================================
    #  CASO DE USO: Obtener programa por ID
    # ============================================================
    
    def get_programa(self, db: Session, programa_id: int) -> ProgramaOut:
        """
        Obtener un programa por su ID.
        
        Validaciones:
        - El programa debe existir (404 si no existe)
        
        Args:
            db: Sesión de base de datos
            programa_id: ID del programa a buscar
            
        Returns:
            ProgramaOut: Schema con datos del programa
            
        Raises:
            HTTPException 404: Si el programa no existe
            
        Flujo:
            1. Consultar repository
            2. Si no existe → lanzar 404
            3. Transformar Model → Schema
            4. Devolver schema
            
        Uso:
            programa = service.get_programa(db, 1)
            print(programa.nombre)  # "Grado en Matemáticas"
        """
        # 1. Buscar en repositorio
        programa = self.repo.get_by_id(db, programa_id)
        
        # 2. Validar existencia
        if not programa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Programa con ID {programa_id} no encontrado"
            )
        
        # 3. Transformar Model (SQLAlchemy) → Schema (Pydantic)
        return ProgramaOut.model_validate(programa)
    
    
    # ============================================================
    #  CASO DE USO: Listar programas con filtros
    # ============================================================
    
    def get_programas(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        activo: Optional[bool] = None,
        tipo: Optional[TipoPrograma] = None
    ) -> ProgramaList:
        """
        Listar programas con filtros opcionales y paginación.
        
        Validaciones:
        - No se requieren validaciones especiales (lista vacía es válida)
        
        Args:
            db: Sesión de base de datos
            skip: Número de registros a saltar (offset)
            limit: Número máximo de registros a devolver
            activo: Filtro opcional por estado
            tipo: Filtro opcional por tipo de programa
            
        Returns:
            ProgramaList: Schema con lista paginada y metadatos
            
        Flujo:
            1. Consultar repository con filtros
            2. Transformar cada Model → Schema
            3. Construir ProgramaList con metadatos de paginación
            4. Devolver schema de lista
            
        Uso:
            # Obtener página 2 (items 10-19) de programas activos
            lista = service.get_programas(db, skip=10, limit=10, activo=True)
            print(f"Total: {lista.total}")  # 25
            print(f"Página {lista.page}")    # 2
            for prog in lista.items:
                print(prog.nombre)
        """
        # 1. Consultar repository (devuelve items y total)
        items, total = self.repo.get_multi(db, skip, limit, activo, tipo)
        
        # 2. Transformar lista de Models → lista de Schemas
        items_out = [ProgramaOut.model_validate(prog) for prog in items]
        
        # 3. Construir schema de lista con metadatos
        return ProgramaList(
            total=total,
            items=items_out,
            page=(skip // limit) + 1,  # Calcular número de página
            size=limit
        )
    
    
    # ============================================================
    #  CASO DE USO: Crear nuevo programa
    # ============================================================
    
    def create_programa(
        self, 
        db: Session, 
        programa_in: ProgramaCreate
    ) -> ProgramaOut:
        """
        Crear un nuevo programa con validaciones de negocio.
        
        Validaciones:
        - El par (nombre, tipo) debe ser único (409 si existe)
        
        Args:
            db: Sesión de base de datos
            programa_in: Schema con datos del programa a crear
            
        Returns:
            ProgramaOut: Schema con el programa creado (incluye ID generado)
            
        Raises:
            HTTPException 409: Si ya existe un programa con ese (nombre, tipo)
            
        Flujo:
            1. Validar unicidad (nombre, tipo)
            2. Si existe → lanzar 409 Conflict
            3. Llamar repository.create()
            4. Transformar Model → Schema
            5. Devolver schema
            
        Uso:
            programa_data = ProgramaCreate(
                nombre="Grado en Física",
                tipo=TipoPrograma.GRADO
            )
            programa = service.create_programa(db, programa_data)
            print(programa.id)  # 1 (generado por DB)
        """
        # 1. VALIDACIÓN DE NEGOCIO: Unicidad (nombre, tipo)
        if self.repo.exists_by_nombre_tipo(db, programa_in.nombre, programa_in.tipo):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Ya existe un programa con nombre '{programa_in.nombre}' "
                    f"y tipo '{programa_in.tipo.value}'"
                )
            )
        
        # 2. Crear en repository
        # Convertir schema Pydantic → dict para SQLAlchemy
        programa_data = programa_in.model_dump()
        programa = self.repo.create(db, programa_data)
        
        # 3. Transformar y devolver
        return ProgramaOut.model_validate(programa)
    
    
    # ============================================================
    #  CASO DE USO: Actualizar programa existente
    # ============================================================
    
    def update_programa(
        self, 
        db: Session, 
        programa_id: int, 
        programa_in: ProgramaUpdate
    ) -> ProgramaOut:
        """
        Actualizar un programa existente con validaciones.
        
        Validaciones:
        - El programa debe existir (404 si no existe)
        - Si se actualiza nombre o tipo, el nuevo par debe ser único (409)
        
        Args:
            db: Sesión de base de datos
            programa_id: ID del programa a actualizar
            programa_in: Schema con campos a actualizar (parcial)
            
        Returns:
            ProgramaOut: Schema con el programa actualizado
            
        Raises:
            HTTPException 404: Si el programa no existe
            HTTPException 409: Si el nuevo (nombre, tipo) ya existe en OTRO programa
            
        Flujo:
            1. Verificar que el programa existe
            2. Extraer solo campos enviados (exclude_unset=True)
            3. Si se actualiza nombre o tipo, validar unicidad
            4. Llamar repository.update()
            5. Transformar y devolver
            
        Uso:
            # Actualizar solo el nombre
            update_data = ProgramaUpdate(nombre="Nuevo nombre")
            programa = service.update_programa(db, 1, update_data)
            
            # Actualizar múltiples campos
            update_data = ProgramaUpdate(
                nombre="Otro nombre",
                activo=False
            )
            programa = service.update_programa(db, 1, update_data)
        """
        # 1. Verificar existencia del programa
        programa = self.repo.get_by_id(db, programa_id)
        if not programa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Programa con ID {programa_id} no encontrado"
            )
        
        # 2. Extraer solo campos enviados (excluir campos None/no enviados)
        update_data = programa_in.model_dump(exclude_unset=True)
        
        # 3. VALIDACIÓN DE NEGOCIO: Unicidad si se actualiza nombre o tipo
        if "nombre" in update_data or "tipo" in update_data:
            # Construir valores finales (mezclar actuales + nuevos)
            nuevo_nombre = update_data.get("nombre", programa.nombre)
            nuevo_tipo = update_data.get("tipo", programa.tipo)
            
            # Verificar unicidad (excluyendo el programa actual)
            if self.repo.exists_by_nombre_tipo(
                db, 
                nuevo_nombre, 
                nuevo_tipo, 
                exclude_id=programa_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Ya existe otro programa con nombre '{nuevo_nombre}' "
                        f"y tipo '{nuevo_tipo.value}'"
                    )
                )
        
        # 4. Actualizar en repository
        programa = self.repo.update(db, programa, update_data)
        
        # 5. Transformar y devolver
        return ProgramaOut.model_validate(programa)
    
    
    # ============================================================
    #  CASO DE USO: Eliminar (desactivar) programa
    # ============================================================
    
    def delete_programa(self, db: Session, programa_id: int) -> dict:
        """
        Realizar soft delete de un programa (marcar como inactivo).
        
        Validaciones:
        - El programa debe existir (404 si no existe)
        
        Args:
            db: Sesión de base de datos
            programa_id: ID del programa a desactivar
            
        Returns:
            dict: Mensaje de confirmación
            
        Raises:
            HTTPException 404: Si el programa no existe
            
        Flujo:
            1. Intentar soft delete en repository
            2. Si no existe (devuelve False) → lanzar 404
            3. Devolver mensaje de éxito
            
        Uso:
            resultado = service.delete_programa(db, 1)
            print(resultado)  # {"message": "Programa desactivado correctamente"}
        """
        # 1. Intentar soft delete
        success = self.repo.delete(db, programa_id)
        
        # 2. Validar si existía
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Programa con ID {programa_id} no encontrado"
            )
        
        # 3. Devolver confirmación
        return {"message": "Programa desactivado correctamente"}


# ============================================================
#  SINGLETON: Instancia única del service
# ============================================================

programa_service = ProgramaService()
"""
Instancia singleton del service.

Se usa así en routers:
    from backend.modules.catalogo.services.programa_service import programa_service
    
    resultado = programa_service.create_programa(db, programa_data)
"""