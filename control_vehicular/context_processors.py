import logging
from datetime import date, timedelta
from typing import Dict, Any

from django.http import HttpRequest
from .models import Mantenimiento, PolizaSeguro

# ==========================================
# CONFIGURATION CONSTANTS
# ==========================================
ALERT_THRESHOLD_DAYS = 15
logger = logging.getLogger(__name__)


def alertas_globales(request: HttpRequest) -> Dict[str, Any]:
    """
    Global Context Processor for FleetPro.
    Calculates and injects real-time operational alerts into the global context.
    """
    if not request.user.is_authenticated:
        return {}

    try:
        today = date.today()
        limit_date = today + timedelta(days=ALERT_THRESHOLD_DAYS)

        # 3. Pending Maintenance Query (Ignorando BAJAS y sumando los EN_PROCESO)
        alertas_mant = (
            Mantenimiento.objects.select_related("vehiculo")
            .filter(
                estado__in=["PENDIENTE", "EN_PROCESO"], fecha_servicio__lte=limit_date
            )
            .exclude(vehiculo__estado="BAJA")
            .order_by("fecha_servicio")
        )

        # 4. Expiring Insurance Policies Query (Ignorando BAJAS)
        alertas_pol = (
            PolizaSeguro.objects.select_related("vehiculo")
            .filter(fecha_vencimiento__lte=limit_date)
            .exclude(vehiculo__estado="BAJA")
            .order_by("fecha_vencimiento")
        )

        # 5. Context Compilation (Agregamos sufijo _global para no confundir)
        return {
            "alertas_mantenimientos_global": alertas_mant,
            "alertas_polizas_global": alertas_pol,
            "total_alertas": alertas_mant.count() + alertas_pol.count(),
        }

    except Exception as e:
        logger.error(f"Error processing global alerts context: {str(e)}")
        return {}
