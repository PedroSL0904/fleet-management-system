import logging
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.utils import timezone

from .models import Vehiculo, Asignacion, Mantenimiento, Chofer

logger = logging.getLogger(__name__)


# ==========================================
# VEHICLE STATE TRANSITIONS
# ==========================================


def dar_baja_vehiculo(vehiculo: Vehiculo) -> None:
    """Marks a vehicle as decommissioned (BAJA). No validation required."""
    vehiculo.estado = "BAJA"
    vehiculo.save()


def reactivar_vehiculo(vehiculo: Vehiculo) -> None:
    """
    Reactivates a decommissioned vehicle by determining its correct operational state.
    Checks for active maintenance or assignments to set EN_TALLER, EN_RUTA, or DISPONIBLE.
    """
    # Single query to check both maintenance and assignment status
    has_active_maintenance = Mantenimiento.objects.filter(
        vehiculo=vehiculo, estado="EN_PROCESO"
    ).exists()
    has_active_assignment = Asignacion.objects.filter(
        vehiculo=vehiculo, estado="ACTIVA"
    ).exists()

    if has_active_maintenance:
        vehiculo.estado = "EN_TALLER"
    elif has_active_assignment:
        vehiculo.estado = "EN_RUTA"
    else:
        vehiculo.estado = "DISPONIBLE"

    vehiculo.save()


def determinar_estado_vehiculo(vehiculo: Vehiculo) -> str:
    """
    Determines the correct operational state for a vehicle without persisting changes.
    Returns: 'EN_TALLER', 'EN_RUTA', or 'DISPONIBLE'.
    """
    # Single query to check both maintenance and assignment status
    has_active_maintenance = Mantenimiento.objects.filter(
        vehiculo=vehiculo, estado="EN_PROCESO"
    ).exists()
    if has_active_maintenance:
        return "EN_TALLER"

    has_active_assignment = Asignacion.objects.filter(
        vehiculo=vehiculo, estado="ACTIVA"
    ).exists()
    if has_active_assignment:
        return "EN_RUTA"

    return "DISPONIBLE"


# ==========================================
# ASSIGNMENT LIFECYCLE
# ==========================================


def activar_asignacion(asignacion: Asignacion) -> None:
    """
    Activates a vehicle assignment and transitions the vehicle to EN_RUTA.
    Assumes vehiculo relation is already loaded (use select_related in views).
    """
    asignacion.estado = "ACTIVA"
    asignacion.save()

    # Update vehicle state to reflect active assignment
    asignacion.vehiculo.estado = "EN_RUTA"
    asignacion.vehiculo.save()


def liberar_vehiculo(
    vehiculo: Vehiculo, kilometraje_regreso: str | None = None
) -> None:
    """
    Releases a vehicle from active assignment, updating mileage and finalizing the trip.
    Logs a warning if mileage input is invalid but continues execution.
    """
    # Parse mileage input, gracefully handle invalid values
    if kilometraje_regreso:
        try:
            vehiculo.kilometraje_actual = Decimal(kilometraje_regreso)
        except InvalidOperation:
            logger.warning(f"Invalid mileage input received: {kilometraje_regreso}")

    vehiculo.estado = "DISPONIBLE"
    vehiculo.save()

    # Finalize the active assignment if one exists
    asignacion = Asignacion.objects.filter(vehiculo=vehiculo, estado="ACTIVA").first()
    if asignacion:
        asignacion.estado = "FINALIZADA"
        asignacion.fecha_devolucion = timezone.now()
        asignacion.save()


# ==========================================
# MAINTENANCE LIFECYCLE
# ==========================================


def iniciar_mantenimiento(mantenimiento: Mantenimiento) -> None:
    """
    Transitions a maintenance record to EN_PROCESO and moves the vehicle to EN_TALLER.
    Assumes vehiculo relation is already loaded (use select_related in views).
    """
    mantenimiento.estado = "EN_PROCESO"
    mantenimiento.save()

    # Update vehicle state to reflect maintenance in progress
    mantenimiento.vehiculo.estado = "EN_TALLER"
    mantenimiento.vehiculo.save()


def finalizar_mantenimiento(mantenimiento: Mantenimiento) -> None:
    """
    Marks maintenance as FINALIZADO and returns vehicle to DISPONIBLE if it was in EN_TALLER.
    Assumes vehiculo relation is already loaded (use select_related in views).
    """
    mantenimiento.estado = "FINALIZADO"
    mantenimiento.save()

    # Only transition vehicle if it's still in maintenance state
    if mantenimiento.vehiculo.estado == "EN_TALLER":
        mantenimiento.vehiculo.estado = "DISPONIBLE"
        mantenimiento.vehiculo.save()


# ==========================================
# DRIVER STATE TRANSITIONS
# ==========================================


def dar_baja_chofer(chofer: Chofer) -> None:
    """Marks a driver as inactive (BAJA). No validation required."""
    chofer.estado = "BAJA"
    chofer.save()


def reactivar_chofer(chofer: Chofer) -> None:
    """Reactivates a driver by setting status to ACTIVO. No validation required."""
    chofer.estado = "ACTIVO"
    chofer.save()
