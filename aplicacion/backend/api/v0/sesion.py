from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.orm import Session
from database import get_db
from schemas.sesion import SesionCreate, SesionUpdate, SesionOut
from crud.sesion import (
    create_sesion,
    get_sesiones,
    get_sesiones_with_relations,
    get_sesion_by_id,
    get_sesion_by_id_with_relations,
    update_sesion,
    delete_sesion,
    get_sesiones_by_profesor,
    get_sesiones_by_asignatura,
    get_sesiones_by_aula,
    validar_sesion_completa,
    serializar_conflictos,
)
from constants.enums import DiaSemanaEnum
from typing import Optional, Dict, Any
from dataclasses import asdict

router = APIRouter(prefix="/v0/sesiones", tags=["Sesiones"])

# ========== ENDPOINTS PRINCIPALES ==========

@router.get("/", 
    response_model=list[SesionOut],
    summary="Listar sesiones",
    description="Obtiene una lista de sesiones con paginación y opción de incluir relaciones"
)
def listar_sesiones(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    incluir_relaciones: bool = Query(False, description="Incluir datos de asignatura, profesor y aula"),
    db: Session = Depends(get_db)
):
    if incluir_relaciones:
        return get_sesiones_with_relations(db, skip=skip, limit=limit)
    else:
        return get_sesiones(db, skip=skip, limit=limit)

@router.get("/{sesion_id}", 
    response_model=SesionOut,
    summary="Obtener sesión por ID",
    description="Obtiene los detalles de una sesión específica",
    responses={
        200: {"description": "Sesión encontrada"},
        404: {"description": "Sesión no encontrada"}
    }
)
def obtener_sesion(
    sesion_id: int,
    incluir_relaciones: bool = Query(False, description="Incluir datos de asignatura, profesor y aula"),
    db: Session = Depends(get_db)
):
    if incluir_relaciones:
        sesion = get_sesion_by_id_with_relations(db, sesion_id)
    else:
        sesion = get_sesion_by_id(db, sesion_id)
    
    if not sesion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Sesión con ID {sesion_id} no encontrada"
        )
    return sesion

@router.post("/", 
    response_model=SesionOut, 
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva sesión",
    description="Crea una nueva sesión en el sistema",
    responses={
        201: {"description": "Sesión creada exitosamente"},
        400: {"description": "Error en los datos proporcionados"},
        409: {"description": "Conflictos detectados - sesión no creada"}
    }
)
def crear_sesion(
    sesion: SesionCreate, 
    forzar: bool = Query(False, description="Forzar creación aunque haya conflictos críticos"),
    db: Session = Depends(get_db),
    response: Response = Depends()
):
    resultado = create_sesion(db, sesion, forzar_creacion=forzar)
    
    if not resultado.exitoso:
        if resultado.conflictos_criticos:
            # Hay conflictos críticos - devolver 409
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail={
                    "mensaje": resultado.mensaje,
                    "conflictos": resultado.conflictos,
                    "conflictos_criticos": resultado.conflictos_criticos,
                    "total_conflictos": resultado.total_conflictos,
                    "sugerencia": "Use el parámetro 'forzar=true' para crear pese a los conflictos"
                }
            )
        else:
            # Error de validación o base de datos
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=resultado.mensaje)
    
    # Establecer headers personalizados correctamente
    if resultado.conflictos and resultado.total_conflictos > 0:
        response.headers["X-Conflictos-Detectados"] = str(resultado.total_conflictos)
        if resultado.forzado:
            response.headers["X-Operacion-Forzada"] = "true"
    
    return resultado.entidad

@router.put("/{sesion_id}", 
    response_model=SesionOut,
    summary="Actualizar sesión",
    description="Actualiza los datos de una sesión existente",
    responses={
        200: {"description": "Sesión actualizada exitosamente"},
        404: {"description": "Sesión no encontrada"},
        400: {"description": "Error en los datos proporcionados"},
        409: {"description": "Conflictos detectados - sesión no actualizada"}
    }
)
def actualizar_sesion(
    sesion_id: int, 
    datos: SesionUpdate,
    forzar: bool = Query(False, description="Forzar actualización aunque haya conflictos críticos"),
    db: Session = Depends(get_db),
    response: Response = Depends()
):
    resultado = update_sesion(db, sesion_id, datos, forzar_actualizacion=forzar)
    
    if not resultado.exitoso:
        if "no encontrada" in resultado.mensaje.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=resultado.mensaje)
        elif resultado.conflictos_criticos:
            # Hay conflictos críticos - devolver 409
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail={
                    "mensaje": resultado.mensaje,
                    "conflictos": resultado.conflictos,
                    "conflictos_criticos": resultado.conflictos_criticos,
                    "total_conflictos": resultado.total_conflictos,
                    "sugerencia": "Use el parámetro 'forzar=true' para actualizar pese a los conflictos"
                }
            )
        else:
            # Error de validación o base de datos
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=resultado.mensaje)
    
    # Establecer headers personalizados correctamente
    if resultado.conflictos and resultado.total_conflictos > 0:
        response.headers["X-Conflictos-Detectados"] = str(resultado.total_conflictos)
        if resultado.forzado:
            response.headers["X-Operacion-Forzada"] = "true"
    
    return resultado.entidad

@router.delete("/{sesion_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar sesión",
    description="Elimina una sesión del sistema",
    responses={
        204: {"description": "Sesión eliminada exitosamente"},
        404: {"description": "Sesión no encontrada"}
    }
)
def eliminar_sesion(sesion_id: int, db: Session = Depends(get_db)):
    success, error = delete_sesion(db, sesion_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=error or f"Sesión con ID {sesion_id} no encontrada"
        )

# ========== ENDPOINTS DE CONSULTA ==========

@router.get("/profesor/{profesor_id}", 
    response_model=list[SesionOut],
    summary="Obtener sesiones por profesor",
    description="Lista todas las sesiones de un profesor específico"
)
def obtener_sesiones_por_profesor(profesor_id: int, db: Session = Depends(get_db)):
    sesiones = get_sesiones_by_profesor(db, profesor_id)
    return sesiones

@router.get("/asignatura/{asignatura_id}", 
    response_model=list[SesionOut],
    summary="Obtener sesiones por asignatura",
    description="Lista todas las sesiones de una asignatura específica"
)
def obtener_sesiones_por_asignatura(asignatura_id: int, db: Session = Depends(get_db)):
    sesiones = get_sesiones_by_asignatura(db, asignatura_id)
    return sesiones

@router.get("/aula/{aula_id}", 
    response_model=list[SesionOut],
    summary="Obtener sesiones por aula",
    description="Lista todas las sesiones que se imparten en un aula específica"
)
def obtener_sesiones_por_aula(aula_id: int, db: Session = Depends(get_db)):
    sesiones = get_sesiones_by_aula(db, aula_id)
    return sesiones

# ========== ENDPOINTS DE VALIDACIÓN ==========

@router.post("/validar", 
    summary="Validar sesión sin crearla",
    description="Valida una sesión propuesta contra todas las reglas de negocio sin persistirla en la base de datos",
    responses={
        200: {"description": "Validación completada - revisar detalles en la respuesta"},
        400: {"description": "Error en los datos proporcionados"}
    }
)
def validar_nueva_sesion(
    sesion: SesionCreate,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Endpoint para validar una sesión propuesta sin crearla.
    
    Retorna información detallada sobre:
    - Si la sesión es válida según las reglas de negocio
    - Todos los conflictos detectados categorizados
    - Conflictos críticos que impedirían la creación
    - Conflictos no críticos que generarían advertencias
    """
    try:
        resultado = validar_sesion_completa(db, sesion)
        
        # Serializar conflictos para asegurar compatibilidad JSON
        conflictos_serializados = serializar_conflictos(resultado.conflictos) if resultado.conflictos else {}
        conflictos_criticos_serializados = [asdict(c) for c in resultado.conflictos_criticos] if resultado.conflictos_criticos else []
        
        return {
            "valida": resultado.es_valido,
            "mensaje": resultado.mensaje,
            "puede_crearse": resultado.es_valido,
            "puede_forzarse": not resultado.es_valido and len(resultado.conflictos_criticos) > 0,
            "conflictos": {
                "total": resultado.total_conflictos,
                "criticos": len(resultado.conflictos_criticos) if resultado.conflictos_criticos else 0,
                "no_criticos": resultado.total_conflictos - (len(resultado.conflictos_criticos) if resultado.conflictos_criticos else 0),
                "detalle": conflictos_serializados,
                "lista_criticos": conflictos_criticos_serializados
            },
            "recomendaciones": {
                "crear_directamente": resultado.es_valido and resultado.total_conflictos == 0,
                "crear_con_advertencias": resultado.es_valido and resultado.total_conflictos > 0,
                "forzar_creacion": not resultado.es_valido and len(resultado.conflictos_criticos) > 0,
                "revisar_datos": not resultado.es_valido and len(resultado.conflictos_criticos) == 0
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Error al validar sesión: {str(e)}"
        )

@router.post("/validar/{sesion_id}", 
    summary="Validar actualización de sesión",
    description="Valida una actualización propuesta de sesión existente sin aplicar los cambios",
    responses={
        200: {"description": "Validación completada - revisar detalles en la respuesta"},
        404: {"description": "Sesión no encontrada"},
        400: {"description": "Error en los datos proporcionados"}
    }
)
def validar_actualizacion_sesion(
    sesion_id: int,
    datos: SesionUpdate,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Endpoint para validar una actualización propuesta sin aplicarla.
    
    Retorna información detallada sobre los conflictos que resultarían
    de aplicar los cambios propuestos a la sesión existente.
    """
    try:
        # Verificar que la sesión existe
        sesion_actual = get_sesion_by_id(db, sesion_id)
        if not sesion_actual:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sesión con ID {sesion_id} no encontrada"
            )
        
        # Preparar datos para validación (actual + cambios)
        update_data = datos.model_dump(exclude_unset=True, exclude_none=True)
        if not update_data:
            return {
                "valida": True,
                "mensaje": "No hay cambios para validar",
                "puede_actualizarse": True,
                "conflictos": {"total": 0, "criticos": 0, "no_criticos": 0, "detalle": {}, "lista_criticos": []},
                "recomendaciones": {"actualizar_directamente": True}
            }
        
        datos_combinados = {
            "asignatura_id": sesion_actual.asignatura_id,
            "profesor_id": sesion_actual.profesor_id,
            "aula_id": sesion_actual.aula_id,
            "dia_semana": sesion_actual.dia_semana,
            "inicio": sesion_actual.inicio,
            "fin": sesion_actual.fin,
            "tipo_clase": sesion_actual.tipo_clase
        }
        datos_combinados.update(update_data)
        sesion_validacion = SesionCreate(**datos_combinados)
        
        # Validar ignorando la sesión actual
        resultado = validar_sesion_completa(db, sesion_validacion, sesion_id_ignorar=sesion_id)
        
        # Serializar conflictos para asegurar compatibilidad JSON
        conflictos_serializados = serializar_conflictos(resultado.conflictos) if resultado.conflictos else {}
        conflictos_criticos_serializados = [asdict(c) for c in resultado.conflictos_criticos] if resultado.conflictos_criticos else []
        
        return {
            "valida": resultado.es_valido,
            "mensaje": resultado.mensaje,
            "puede_actualizarse": resultado.es_valido,
            "puede_forzarse": not resultado.es_valido and len(resultado.conflictos_criticos) > 0,
            "cambios_propuestos": list(update_data.keys()),
            "conflictos": {
                "total": resultado.total_conflictos,
                "criticos": len(resultado.conflictos_criticos) if resultado.conflictos_criticos else 0,
                "no_criticos": resultado.total_conflictos - (len(resultado.conflictos_criticos) if resultado.conflictos_criticos else 0),
                "detalle": conflictos_serializados,
                "lista_criticos": conflictos_criticos_serializados
            },
            "recomendaciones": {
                "actualizar_directamente": resultado.es_valido and resultado.total_conflictos == 0,
                "actualizar_con_advertencias": resultado.es_valido and resultado.total_conflictos > 0,
                "forzar_actualizacion": not resultado.es_valido and len(resultado.conflictos_criticos) > 0,
                "revisar_cambios": not resultado.es_valido and len(resultado.conflictos_criticos) == 0
            }
        }
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Error al validar actualización: {str(e)}"
        )
