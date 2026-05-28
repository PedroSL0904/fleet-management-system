import logging
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Sum
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import get_template
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from xhtml2pdf import pisa  # type: ignore

from . import services
from .decorators import AdminRequiredMixin, StaffRequiredMixin
from .forms import (
    AsignacionForm,
    ChoferForm,
    MantenimientoForm,
    PolizaSeguroForm,
    VehiculoForm,
)
from .models import Asignacion, Chofer, Mantenimiento, PolizaSeguro, Vehiculo

logger = logging.getLogger(__name__)

FORM_TEMPLATE = "control_vehicular/crear_vehiculo.html"


class FleetFormMixin:
    """Injects common context variables for form templates."""

    template_name = FORM_TEMPLATE
    titulo: str = ""
    url_regreso_name: str = ""
    texto_regreso: str = "Volver"
    pk_url_kwarg = "id"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        # Injects titulo, url_regreso, and texto_regreso into template context
        context = super().get_context_data(**kwargs)
        context["titulo"] = self.titulo
        context["url_regreso"] = reverse(self.url_regreso_name)
        context["texto_regreso"] = self.texto_regreso
        return context


# ==========================================
# DASHBOARD & REPORTING
# ==========================================


class DashboardView(LoginRequiredMixin, TemplateView):
    """Renders dashboard.html with fleet KPIs. Requires authenticated user."""

    template_name = "control_vehicular/dashboard.html"
    login_url = "/login/"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        # Aggregates fleet statistics: vehicle states, maintenance costs, assignments
        context = super().get_context_data(**kwargs)
        hoy = timezone.now().date()
        limite_30 = hoy + timedelta(days=30)
        limite_7 = hoy + timedelta(days=7)

        vehiculos_activos = Vehiculo.objects.exclude(estado="BAJA")
        total_v = vehiculos_activos.count()
        disponibles = vehiculos_activos.filter(estado="DISPONIBLE").count()
        en_ruta = vehiculos_activos.filter(estado="EN_RUTA").count()
        en_taller = vehiculos_activos.filter(estado="EN_TALLER").count()

        tasa_disponibilidad = (
            round((disponibles / total_v * 100), 1) if total_v > 0 else 0
        )

        gasto_total = Mantenimiento.objects.filter(estado="FINALIZADO").aggregate(
            total=Sum("costo")
        )["total"] or Decimal("0.00")

        costo_promedio = Mantenimiento.objects.filter(estado="FINALIZADO").aggregate(
            avg=Avg("costo")
        )["avg"] or Decimal("0.00")

        mant_preventivo = Mantenimiento.objects.filter(tipo="PREVENTIVO").count()
        mant_correctivo = Mantenimiento.objects.filter(tipo="CORRECTIVO").count()
        mant_estetico = Mantenimiento.objects.filter(tipo="ESTETICO").count()

        total_viajes = Asignacion.objects.count()
        viajes_este_mes = Asignacion.objects.filter(
            fecha_salida__month=hoy.month, fecha_salida__year=hoy.year
        ).count()

        polizas_criticas = (
            PolizaSeguro.objects.select_related("vehiculo")
            .filter(fecha_vencimiento__lte=limite_7, fecha_vencimiento__gte=hoy)
            .exclude(vehiculo__estado="BAJA")
        )

        polizas_proximas = (
            PolizaSeguro.objects.select_related("vehiculo")
            .filter(fecha_vencimiento__lte=limite_30, fecha_vencimiento__gte=hoy)
            .exclude(vehiculo__estado="BAJA")
        )

        licencias_proximas = Chofer.objects.filter(
            estado="ACTIVO",
            vencimiento_licencia__lte=limite_30,
            vencimiento_licencia__gte=hoy,
        )

        mant_activos = (
            Mantenimiento.objects.select_related("vehiculo")
            .filter(estado__in=["PENDIENTE", "EN_PROCESO"])
            .exclude(vehiculo__estado="BAJA")
        )

        asignaciones_activas = Asignacion.objects.select_related(
            "vehiculo", "chofer"
        ).filter(estado="ACTIVA")

        mantenimientos_recientes = (
            Mantenimiento.objects.exclude(vehiculo__estado="BAJA")
            .select_related("vehiculo")
            .order_by("-fecha_servicio")[:5]
        )

        vehiculo_mas_km = vehiculos_activos.order_by("-kilometraje_actual").first()

        km_promedio = vehiculos_activos.aggregate(avg=Avg("kilometraje_actual"))[
            "avg"
        ] or Decimal("0.00")

        context.update(
            {
                "total_vehiculos": total_v,
                "disponibles": disponibles,
                "en_ruta": en_ruta,
                "en_taller": en_taller,
                "tasa_disponibilidad": tasa_disponibilidad,
                "total_choferes": Chofer.objects.filter(estado="ACTIVO").count(),
                "gasto_total": gasto_total,
                "costo_promedio": round(costo_promedio, 2),
                "total_viajes": total_viajes,
                "viajes_este_mes": viajes_este_mes,
                "asignaciones_activas": asignaciones_activas,
                "mant_preventivo": mant_preventivo,
                "mant_correctivo": mant_correctivo,
                "mant_estetico": mant_estetico,
                "mant_activos": mant_activos,
                "mantenimientos_recientes": mantenimientos_recientes,
                "vehiculo_mas_km": vehiculo_mas_km,
                "km_promedio": round(km_promedio, 0),
                "polizas_criticas": polizas_criticas,
                "polizas_proximas": polizas_proximas,
                "licencias_proximas": licencias_proximas,
                "total_alertas_criticas": polizas_criticas.count()
                + mant_activos.count(),
                "hoy": hoy,
            }
        )
        return context


class FlotillaView(LoginRequiredMixin, ListView):
    """Renders flotilla.html with active vehicle list. Requires authenticated user."""

    template_name = "control_vehicular/flotilla.html"
    context_object_name = "vehiculos"
    login_url = "/login/"

    def get_queryset(self):
        return Vehiculo.objects.exclude(estado="BAJA")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        # Adds vehicle state counts to context
        context = super().get_context_data(**kwargs)
        vehiculos = context["vehiculos"]
        context["total_vehiculos"] = vehiculos.count()
        context["disponibles"] = vehiculos.filter(estado="DISPONIBLE").count()
        context["en_taller"] = vehiculos.filter(estado="EN_TALLER").count()
        context["en_ruta"] = vehiculos.filter(estado="EN_RUTA").count()
        return context


class ExportarPDFView(LoginRequiredMixin, View):
    """Generates fleet report as PDF. Requires authenticated user."""

    login_url = "/login/"

    def get(self, request: HttpRequest) -> HttpResponse:
        # Builds PDF context with KPIs, vehicles, assignments, and alerts
        hoy = timezone.now().date()
        limite_alerta = hoy + timedelta(days=30)
        vehiculos = Vehiculo.objects.exclude(estado="BAJA")
        gasto_total = Mantenimiento.objects.filter(estado="FINALIZADO").aggregate(
            total=Sum("costo")
        )["total"] or Decimal("0.00")

        context: dict[str, Any] = {
            "fecha_generacion": timezone.now(),
            "generado_por": getattr(
                request.user, "get_full_name", lambda: request.user.username
            )(),
            "kpis": {
                "total": vehiculos.count(),
                "disponibles": vehiculos.filter(estado="DISPONIBLE").count(),
                "en_ruta": vehiculos.filter(estado="EN_RUTA").count(),
                "en_taller": vehiculos.filter(estado="EN_TALLER").count(),
                "gasto_mantenimiento": gasto_total,
            },
            "vehiculos": vehiculos,
            "asignaciones": Asignacion.objects.select_related(
                "vehiculo", "chofer"
            ).filter(estado="ACTIVA"),
            "alertas_mantenimiento": Mantenimiento.objects.select_related("vehiculo")
            .filter(estado__in=["PENDIENTE", "EN_PROCESO"])
            .exclude(vehiculo__estado="BAJA"),
            "alertas_polizas": PolizaSeguro.objects.select_related("vehiculo")
            .filter(fecha_vencimiento__lte=limite_alerta)
            .exclude(vehiculo__estado="BAJA"),
        }

        template = get_template("control_vehicular/reporte_pdf.html")
        html = template.render(context)
        fecha_arch = timezone.localtime(timezone.now()).strftime("%Y%m%d_%H%M")
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="FleetPro_Reporte_{fecha_arch}.pdf"'
        )

        pisa_status = pisa.CreatePDF(html, dest=response)  # type: ignore
        if pisa_status.err:  # type: ignore
            logger.error("PDF generation failed.")
            return HttpResponse(f"Error generating PDF <pre>{html}</pre>", status=500)

        return response


# ==========================================
# VEHICLE MANAGEMENT
# ==========================================


class AgregarVehiculoView(AdminRequiredMixin, FleetFormMixin, CreateView):
    """Renders crear_vehiculo.html for vehicle creation. Requires ADMIN role."""

    model = Vehiculo
    form_class = VehiculoForm
    titulo = "Nuevo Vehículo"
    url_regreso_name = "flotilla"
    texto_regreso = "Volver a Flotilla"
    success_url = reverse_lazy("flotilla")


class EditarVehiculoView(AdminRequiredMixin, FleetFormMixin, UpdateView):
    """Renders crear_vehiculo.html for vehicle editing. Requires ADMIN role."""

    model = Vehiculo
    form_class = VehiculoForm
    url_regreso_name = "flotilla"
    texto_regreso = "Volver a Flotilla"
    success_url = reverse_lazy("flotilla")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        # Dynamically sets titulo with vehicle brand and model
        context = super().get_context_data(**kwargs)
        vehiculo = self.object
        context["titulo"] = (
            f"Editar Vehículo: {vehiculo.get_marca_display()} {vehiculo.modelo}"
        )
        return context


class EliminarVehiculoView(AdminRequiredMixin, View):
    """Decommissions a vehicle (soft delete). Requires ADMIN role."""

    login_url = "/login/"

    def post(self, request: HttpRequest, id: int) -> HttpResponseRedirect:
        vehiculo = get_object_or_404(Vehiculo, id=id)
        services.dar_baja_vehiculo(vehiculo)
        return redirect("flotilla")


class VehiculosBajaView(LoginRequiredMixin, ListView):
    """Renders vehiculos_baja.html with decommissioned vehicles. Requires authenticated user."""

    template_name = "control_vehicular/vehiculos_baja.html"
    context_object_name = "vehiculos"
    login_url = "/login/"

    def get_queryset(self):
        return Vehiculo.objects.filter(estado="BAJA")


class ReactivarVehiculoView(AdminRequiredMixin, View):
    """Reactivates a decommissioned vehicle. Requires ADMIN role."""

    login_url = "/login/"

    def post(self, request: HttpRequest, id: int) -> HttpResponseRedirect:
        vehiculo = get_object_or_404(Vehiculo, id=id)
        services.reactivar_vehiculo(vehiculo)
        return redirect("vehiculos_baja")


# ==========================================
# MAINTENANCE MANAGEMENT
# ==========================================


class RegistrarMantenimientoView(StaffRequiredMixin, FleetFormMixin, CreateView):
    """Renders crear_vehiculo.html for maintenance registration. Requires STAFF role."""

    model = Mantenimiento
    form_class = MantenimientoForm
    titulo = "Registrar Mantenimiento"
    url_regreso_name = "historial_mantenimientos"
    texto_regreso = "Volver a Mantenimientos"
    success_url = reverse_lazy("historial_mantenimientos")


class EditarMantenimientoView(StaffRequiredMixin, FleetFormMixin, UpdateView):
    """Renders crear_vehiculo.html for maintenance editing. Requires STAFF role."""

    model = Mantenimiento
    form_class = MantenimientoForm
    titulo = "Gestionar Mantenimiento"
    url_regreso_name = "historial_mantenimientos"
    texto_regreso = "Volver a Mantenimientos"
    success_url = reverse_lazy("historial_mantenimientos")


class FinalizarMantenimientoView(StaffRequiredMixin, View):
    """Marks maintenance as completed. Requires STAFF role."""

    login_url = "/login/"

    def post(self, request: HttpRequest, id: int) -> HttpResponseRedirect:
        mant = get_object_or_404(Mantenimiento, id=id)
        services.finalizar_mantenimiento(mant)
        return redirect("flotilla")


class HistorialMantenimientosView(LoginRequiredMixin, ListView):
    """Renders historial_mantenimientos.html with maintenance records. Requires authenticated user."""

    template_name = "control_vehicular/historial_mantenimientos.html"
    context_object_name = "mantenimientos"
    login_url = "/login/"

    def get_queryset(self):
        return Mantenimiento.objects.exclude(vehiculo__estado="BAJA").order_by(
            "-fecha_servicio"
        )


# ==========================================
# INSURANCE POLICIES
# ==========================================


class RegistrarPolizaView(AdminRequiredMixin, FleetFormMixin, CreateView):
    """Renders crear_vehiculo.html for insurance policy creation. Requires ADMIN role."""

    model = PolizaSeguro
    form_class = PolizaSeguroForm
    titulo = "Registrar Póliza de Seguro"
    url_regreso_name = "dashboard"
    texto_regreso = "Volver al Dashboard"
    success_url = reverse_lazy("dashboard")


class ListaPolizasView(LoginRequiredMixin, ListView):
    """Renders polizas.html with insurance policies. Requires authenticated user."""

    template_name = "control_vehicular/polizas.html"
    context_object_name = "polizas"
    login_url = "/login/"

    def get_queryset(self):
        return (
            PolizaSeguro.objects.select_related("vehiculo")
            .exclude(vehiculo__estado="BAJA")
            .order_by("fecha_vencimiento")
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        # Adds current date for expiration comparison
        context = super().get_context_data(**kwargs)
        context["hoy"] = timezone.now().date()
        return context


class EditarPolizaView(LoginRequiredMixin, FleetFormMixin, UpdateView):
    """Renders crear_vehiculo.html for insurance policy editing. Requires authenticated user."""

    model = PolizaSeguro
    form_class = PolizaSeguroForm
    url_regreso_name = "lista_polizas"
    texto_regreso = "Volver a Pólizas"
    success_url = reverse_lazy("lista_polizas")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        # Dynamically sets titulo with vehicle plates
        context = super().get_context_data(**kwargs)
        poliza = self.object
        context["titulo"] = f"Editar Póliza: {poliza.vehiculo.placas}"
        return context


# ==========================================
# DRIVER MANAGEMENT
# ==========================================


class ListaChoferesView(LoginRequiredMixin, ListView):
    """Renders choferes.html with active drivers. Requires authenticated user."""

    template_name = "control_vehicular/choferes.html"
    context_object_name = "choferes"
    login_url = "/login/"

    def get_queryset(self):
        return Chofer.objects.filter(estado="ACTIVO")


class RegistrarChoferView(AdminRequiredMixin, FleetFormMixin, CreateView):
    """Renders crear_vehiculo.html for driver registration. Requires ADMIN role."""

    model = Chofer
    form_class = ChoferForm
    titulo = "Registrar Nuevo Operador"
    url_regreso_name = "lista_choferes"
    texto_regreso = "Volver a Operadores"
    success_url = reverse_lazy("lista_choferes")


class EditarChoferView(AdminRequiredMixin, FleetFormMixin, UpdateView):
    """Renders crear_vehiculo.html for driver editing. Requires ADMIN role."""

    model = Chofer
    form_class = ChoferForm
    titulo = "⚙️ Editar Datos del Chofer"
    url_regreso_name = "lista_choferes"
    texto_regreso = "Volver a Operadores"
    success_url = reverse_lazy("lista_choferes")


class BajaChoferView(AdminRequiredMixin, View):
    """Deactivates a driver (soft delete). Requires ADMIN role."""

    login_url = "/login/"

    def post(self, request: HttpRequest, id: int) -> HttpResponseRedirect:
        chofer = get_object_or_404(Chofer, id=id)
        services.dar_baja_chofer(chofer)
        return redirect("lista_choferes")


class ChoferesBajaView(LoginRequiredMixin, ListView):
    """Renders choferes_baja.html with deactivated drivers. Requires authenticated user."""

    template_name = "control_vehicular/choferes_baja.html"
    context_object_name = "choferes"
    login_url = "/login/"

    def get_queryset(self):
        return Chofer.objects.filter(estado="BAJA")


class ReactivarChoferView(AdminRequiredMixin, View):
    """Reactivates a deactivated driver. Requires ADMIN role."""

    login_url = "/login/"

    def post(self, request: HttpRequest, id: int) -> HttpResponseRedirect:
        chofer = get_object_or_404(Chofer, id=id)
        services.reactivar_chofer(chofer)
        return redirect("choferes_baja")


# ==========================================
# OPERATIONAL ASSIGNMENTS
# ==========================================


class AsignarVehiculoView(AdminRequiredMixin, FleetFormMixin, CreateView):
    """Renders crear_vehiculo.html for vehicle assignment. Requires ADMIN role."""

    model = Asignacion
    form_class = AsignacionForm
    titulo = "Asignar Vehículo a Operador"
    url_regreso_name = "flotilla"
    texto_regreso = "Volver a Flotilla"
    success_url = reverse_lazy("flotilla")

    def get_initial(self) -> dict[str, Any]:
        # Pre-fills vehicle field from query parameter
        initial = super().get_initial()
        vehiculo_id = self.request.GET.get("vehiculo")
        if vehiculo_id:
            initial["vehiculo"] = vehiculo_id
        return initial

    def form_valid(self, form: AsignacionForm) -> HttpResponseRedirect:
        # Saves assignment and activates vehicle state via service layer
        asignacion = form.save(commit=False)
        services.activar_asignacion(asignacion)
        return HttpResponseRedirect(self.get_success_url())


class LiberarVehiculoView(AdminRequiredMixin, View):
    """Releases vehicle from assignment and updates mileage. Requires ADMIN role."""

    login_url = "/login/"

    def post(self, request: HttpRequest, id: int) -> HttpResponseRedirect:
        vehiculo = get_object_or_404(Vehiculo, id=id)
        nuevo_km_raw = request.POST.get("kilometraje_regreso")
        services.liberar_vehiculo(vehiculo, nuevo_km_raw)
        return redirect("flotilla")
