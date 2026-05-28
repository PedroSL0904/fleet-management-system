import logging
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from .models import Vehiculo, Asignacion, Mantenimiento, Chofer

logger = logging.getLogger(__name__)


# ==========================================
# VEHICLE STATE TRANSITIONS
# ==========================================

def dar_baja_vehiculo(vehiculo: Vehiculo) -> None:
    vehiculo.estado = 'BAJA'
    vehiculo.save()


def reactivar_vehiculo(vehiculo: Vehiculo) -> None:
    if Mantenimiento.objects.filter(vehiculo=vehiculo, estado='EN_PROCESO').exists():
        vehiculo.estado = 'EN_TALLER'
    elif Asignacion.objects.filter(vehiculo=vehiculo, estado='ACTIVA').exists():
        vehiculo.estado = 'EN_RUTA'
    else:
        vehiculo.estado = 'DISPONIBLE'
    vehiculo.save()


def determinar_estado_vehiculo(vehiculo: Vehiculo) -> str:
    if Mantenimiento.objects.filter(vehiculo=vehiculo, estado='EN_PROCESO').exists():
        return 'EN_TALLER'
    if Asignacion.objects.filter(vehiculo=vehiculo, estado='ACTIVA').exists():
        return 'EN_RUTA'
    return 'DISPONIBLE'


# ==========================================
# ASSIGNMENT LIFECYCLE
# ==========================================

def activar_asignacion(asignacion: Asignacion) -> None:
    asignacion.estado = 'ACTIVA'
    asignacion.save()
    asignacion.vehiculo.estado = 'EN_RUTA'
    asignacion.vehiculo.save()


def liberar_vehiculo(vehiculo: Vehiculo, kilometraje_regreso: str | None = None) -> None:
    if kilometraje_regreso:
        try:
            vehiculo.kilometraje_actual = Decimal(kilometraje_regreso)
        except InvalidOperation:
            logger.warning(f"Invalid mileage input received: {kilometraje_regreso}")

    vehiculo.estado = 'DISPONIBLE'
    vehiculo.save()

    asignacion = Asignacion.objects.filter(vehiculo=vehiculo, estado='ACTIVA').first()
    if asignacion:
        asignacion.estado = 'FINALIZADA'
        asignacion.fecha_devolucion = timezone.now()
        asignacion.save()


# ==========================================
# MAINTENANCE LIFECYCLE
# ==========================================

def iniciar_mantenimiento(mantenimiento: Mantenimiento) -> None:
    mantenimiento.estado = 'EN_PROCESO'
    mantenimiento.save()
    mantenimiento.vehiculo.estado = 'EN_TALLER'
    mantenimiento.vehiculo.save()


def finalizar_mantenimiento(mantenimiento: Mantenimiento) -> None:
    mantenimiento.estado = 'FINALIZADO'
    mantenimiento.save()
    if mantenimiento.vehiculo.estado == 'EN_TALLER':
        mantenimiento.vehiculo.estado = 'DISPONIBLE'
        mantenimiento.vehiculo.save()


# ==========================================
# DRIVER STATE TRANSITIONS
# ==========================================

def dar_baja_chofer(chofer: Chofer) -> None:
    chofer.estado = 'BAJA'
    chofer.save()


def reactivar_chofer(chofer: Chofer) -> None:
    chofer.estado = 'ACTIVO'
    chofer.save()
