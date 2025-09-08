"""
Dependencias comunes para FastAPI: DB, paginación, filtros, settings,
validaciones y metadatos de request.

Centraliza la lógica reutilizable para evitar duplicación en routers.
Importa estas dependencias desde aquí para desacoplar módulos.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime
from fastapi import Depends, Query, Header, Request, HTTPException, status
from sqlalchemy.orm import Session

from config.settings import get_settings, Settings
from db.session import get_db, get_db_readonly
from constants.enums import TipoPrograma, SeveridadConflicto, EstadoConflicto

# ============================
# Exports públicos
# ============================
__all__ = [
    "get_db", "get_db_readonly", "get_current_settings", 
    "pagination", "common_filters", "programa_filters", "conflict_filters",
    "validate_programa_id", "get_request_info"
]

# ============================
# Config / Settings
# ============================

def get_current_settings() -> Settings:
    """
    Inyecta la configuración actual (singleton con lru_cache).
    
    Usage:
        def endpoint(settings: Settings = Depends(get_current_settings)):
            max_size = settings.max_file_size_mb
    """
    return get_settings()

# ============================
# Paginación estándar
# ============================

def pagination(
    settings: Settings = Depends(get_current_settings),
    skip: int = Query(0, ge=0, description="Registros a omitir (offset)"),
    limit: int = Query(
        None, 
        ge=1, 
        description="Registros por página (por defecto desde settings)"
    ),
) -> Dict[str, int]:
    """
    Paginación estándar con límites configurables.
    
    Returns:
        dict: {"skip": int, "limit": int}
    """
    # Usar default del settings si no se especifica
    _limit = limit if limit is not None else settings.default_page_size
    
    # Respetar límite máximo global
    if _limit > settings.max_page_size:
        _limit = settings.max_page_size
    
    return {"skip": skip, "limit": _limit}

# ============================
# Filtros comunes
# ============================

def common_filters(
    activo: Optional[bool] = Query(
        None, 
        description="Filtrar por estado activo/inactivo"
    ),
    nombre_like: Optional[str] = Query(
        None, 
        max_length=200,
        description="Búsqueda parcial por nombre (ILIKE)"
    ),
    created_from: Optional[datetime] = Query(
        None, 
        description="Desde fecha de creación (YYYY-MM-DD)"
    ),
    created_to: Optional[datetime] = Query(
        None, 
        description="Hasta fecha de creación (YYYY-MM-DD)"
    ),
) -> Dict[str, Any]:
    """
    Filtros básicos aplicables a la mayoría de entidades.
    
    Returns:
        dict: Filtros no nulos para aplicar en queries
    """
    filters: Dict[str, Any] = {}
    
    if activo is not None:
        filters["activo"] = activo
    if nombre_like:
        filters["nombre_like"] = nombre_like.strip()
    if created_from:
        filters["created_from"] = created_from
    if created_to:
        filters["created_to"] = created_to
    
    # Validación de rango de fechas
    if created_from and created_to and created_from > created_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="created_from debe ser anterior a created_to"
        )
    
    return filters

# ============================
# Filtros específicos del dominio
# ============================

def programa_filters(
    tipo: Optional[TipoPrograma] = Query(
        None, 
        description="Tipo de programa (grado, master, doctorado)"
    ),
    common: Dict[str, Any] = Depends(common_filters)
) -> Dict[str, Any]:
    """
    Filtros específicos para programas académicos.
    Combina filtros comunes + específicos de programa.
    """
    filters = {**common}
    if tipo:
        filters["tipo"] = tipo
    return filters

def conflict_filters(
    severidad_min: Optional[SeveridadConflicto] = Query(
        None,
        description="Severidad mínima de conflictos a mostrar"
    ),
    estado: Optional[EstadoConflicto] = Query(
        None,
        description="Estado específico de conflictos"
    ),
    solo_activos: bool = Query(
        True,
        description="Solo conflictos en estados activos (abierto, en_revision)"
    )
) -> Dict[str, Any]:
    """
    Filtros específicos para el sistema de detección de conflictos.
    """
    filters: Dict[str, Any] = {}
    
    if severidad_min:
        filters["severidad_min"] = severidad_min
    if estado:
        filters["estado"] = estado
    if solo_activos:
        filters["solo_activos"] = solo_activos
    
    return filters

# ============================
# Validaciones de existencia
# ============================

def validate_programa_id(
    programa_id: int,
    db: Session = Depends(get_db),
) -> int:
    """
    Valida que el programa exista antes de procesar el endpoint.
    
    Args:
        programa_id: ID del programa a validar
        db: Sesión de base de datos
    
    Returns:
        int: El mismo programa_id si existe
    
    Raises:
        HTTPException: 404 si no existe el programa
    """
    # Import con fallback para encontrar models
    try:
        from database.models import Programa
    except ImportError:
        # Fallback usando sys.path como en session.py
        import sys
        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(project_root))
        from database.models import Programa
    
    programa = db.query(Programa).filter(Programa.id == programa_id).first()
    if not programa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Programa con ID {programa_id} no encontrado"
        )
    return programa_id

# ============================
# Información de request
# ============================

def get_request_info(
    request: Request,
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
    x_forwarded_for: Optional[str] = Header(None, alias="X-Forwarded-For"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-Id"),
) -> Dict[str, Any]:
    """
    Metadatos de la petición HTTP para logging y trazabilidad.
    
    NOTA: No usar para seguridad, solo para logging/analytics.
    
    Returns:
        dict: Información del request (IP, user-agent, etc.)
    """
    client_ip = None
    
    if x_forwarded_for:
        # Primer IP de la cadena proxy
        client_ip = x_forwarded_for.split(",")[0].strip()
    elif request.client:
        client_ip = request.client.host

    return {
        "client_ip": client_ip or "unknown",
        "user_agent": user_agent or "",
        "request_id": x_request_id or "",
        "method": request.method,
        "path": str(request.url.path),
        "timestamp": datetime.now().isoformat()
    }

# ============================
# Utilidades adicionales
# ============================

def get_sort_params(
    sort_by: Optional[str] = Query("id", description="Campo por el que ordenar"),
    sort_desc: bool = Query(False, description="Orden descendente")
) -> Dict[str, Any]:
    """
    Parámetros de ordenación estándar.
    
    Returns:
        dict: {"sort_by": str, "sort_desc": bool}
    """
    return {
        "sort_by": sort_by or "id",
        "sort_desc": sort_desc
    }
