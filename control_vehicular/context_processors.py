import logging
from datetime import date, timedelta
from typing import Dict, Any

from django.http import HttpRequest
from .models import Mantenimiento, PolizaSeguro

ALERT_THRESHOLD_DAYS = 15
logger = logging.getLogger(__name__)


def alertas_globales(request: HttpRequest) -> Dict[str, Any]:
    """Injects pending maintenance and expiring insurance alerts into global template context."""
    if not request.user.is_authenticated:
        return {}

    try:
        today = date.today()
        limit_date = today + timedelta(days=ALERT_THRESHOLD_DAYS)

        # Query pending maintenance (excluding decommissioned vehicles)
        alertas_mant = (
            Mantenimiento.objects.select_related("vehiculo")
            .filter(
                estado__in=["PENDIENTE", "EN_PROCESO"], fecha_servicio__lte=limit_date
            )
            .exclude(vehiculo__estado="BAJA")
            .order_by("fecha_servicio")
        )

        # Query expiring insurance policies (excluding decommissioned vehicles)
        alertas_pol = (
            PolizaSeguro.objects.select_related("vehiculo")
            .filter(fecha_vencimiento__lte=limit_date)
            .exclude(vehiculo__estado="BAJA")
            .order_by("fecha_vencimiento")
        )

        # Inject alerts with _global suffix to avoid naming conflicts
        return {
            "alertas_mantenimientos_global": alertas_mant,
            "alertas_polizas_global": alertas_pol,
            "total_alertas": alertas_mant.count() + alertas_pol.count(),
        }

    except Exception as e:
        logger.error(f"Error processing global alerts context: {str(e)}")
        return {}
