import logging
from decimal import Decimal
from datetime import timedelta
from typing import Any

from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template.loader import get_template
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Avg
from django.views.generic import CreateView, UpdateView

from xhtml2pdf import pisa  # type: ignore

from .models import Vehiculo, Asignacion, Mantenimiento, PolizaSeguro, Chofer
from .forms import (
    VehiculoForm,
    MantenimientoForm,
    PolizaSeguroForm,
    ChoferForm,
    AsignacionForm,
)
from . import services
from .decorators import (
    admin_required,
    staff_required,
    AdminRequiredMixin,
    StaffRequiredMixin,
)

logger = logging.getLogger(__name__)

FORM_TEMPLATE = "control_vehicular/crear_vehiculo.html"


class FleetFormMixin:
    template_name = FORM_TEMPLATE
    titulo: str = ""
    url_regreso_name: str = ""
    texto_regreso: str = "Volver"
    pk_url_kwarg = "id"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["titulo"] = self.titulo
        context["url_regreso"] = reverse(self.url_regreso_name)
        context["texto_regreso"] = self.texto_regreso
        return context


# ==========================================
# DASHBOARD & REPORTING VIEWS (FBVs)
# ==========================================


@login_required(login_url="/login/")
def dashboard(request: HttpRequest) -> HttpResponse:
    hoy = timezone.now().date()
    limite_30 = hoy + timedelta(days=30)
    limite_7 = hoy + timedelta(days=7)

    vehiculos_activos = Vehiculo.objects.exclude(estado="BAJA")
    total_v = vehiculos_activos.count()
    disponibles = vehiculos_activos.filter(estado="DISPONIBLE").count()
    en_ruta = vehiculos_activos.filter(estado="EN_RUTA").count()
    en_taller = vehiculos_activos.filter(estado="EN_TALLER").count()

    tasa_disponibilidad = round((disponibles / total_v * 100), 1) if total_v > 0 else 0

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

    context: dict[str, Any] = {
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
        "total_alertas_criticas": polizas_criticas.count() + mant_activos.count(),
        "hoy": hoy,
    }

    return render(request, "control_vehicular/dashboard.html", context)


@login_required(login_url="/login/")
def flotilla(request: HttpRequest) -> HttpResponse:
    vehiculos_activos = Vehiculo.objects.exclude(estado="BAJA")
    context: dict[str, Any] = {
        "vehiculos": vehiculos_activos,
        "total_vehiculos": vehiculos_activos.count(),
        "disponibles": vehiculos_activos.filter(estado="DISPONIBLE").count(),
        "en_taller": vehiculos_activos.filter(estado="EN_TALLER").count(),
        "en_ruta": vehiculos_activos.filter(estado="EN_RUTA").count(),
    }
    return render(request, "control_vehicular/flotilla.html", context)


@login_required(login_url="/login/")
def exportar_pdf(request: HttpRequest) -> HttpResponse:
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
        "asignaciones": Asignacion.objects.select_related("vehiculo", "chofer").filter(
            estado="ACTIVA"
        ),
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
# VEHICLE CRUD (CBVs)
# ==========================================


class AgregarVehiculoView(AdminRequiredMixin, FleetFormMixin, CreateView):
    model = Vehiculo
    form_class = VehiculoForm
    titulo = "Nuevo Vehículo"
    url_regreso_name = "flotilla"
    texto_regreso = "Volver a Flotilla"
    success_url = reverse_lazy("flotilla")


class EditarVehiculoView(AdminRequiredMixin, FleetFormMixin, UpdateView):
    model = Vehiculo
    form_class = VehiculoForm
    url_regreso_name = "flotilla"
    texto_regreso = "Volver a Flotilla"
    success_url = reverse_lazy("flotilla")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        vehiculo = self.object
        context["titulo"] = (
            f"Editar Vehículo: {vehiculo.get_marca_display()} {vehiculo.modelo}"
        )
        return context


@admin_required
def eliminar_vehiculo(request: HttpRequest, id: int) -> HttpResponseRedirect:
    vehiculo = get_object_or_404(Vehiculo, id=id)
    if request.method == "POST":
        services.dar_baja_vehiculo(vehiculo)
    return redirect("flotilla")


@login_required(login_url="/login/")
def vehiculos_baja(request: HttpRequest) -> HttpResponse:
    context: dict[str, Any] = {"vehiculos": Vehiculo.objects.filter(estado="BAJA")}
    return render(request, "control_vehicular/vehiculos_baja.html", context)


@admin_required
def reactivar_vehiculo(request: HttpRequest, id: int) -> HttpResponseRedirect:
    vehiculo = get_object_or_404(Vehiculo, id=id)
    if request.method == "POST":
        services.reactivar_vehiculo(vehiculo)
    return redirect("vehiculos_baja")


# ==========================================
# MAINTENANCE & INSURANCE (CBVs + FBVs)
# ==========================================


class RegistrarMantenimientoView(StaffRequiredMixin, FleetFormMixin, CreateView):
    model = Mantenimiento
    form_class = MantenimientoForm
    titulo = "Registrar Mantenimiento"
    url_regreso_name = "historial_mantenimientos"
    texto_regreso = "Volver a Mantenimientos"
    success_url = reverse_lazy("historial_mantenimientos")


class EditarMantenimientoView(StaffRequiredMixin, FleetFormMixin, UpdateView):
    model = Mantenimiento
    form_class = MantenimientoForm
    titulo = "Gestionar Mantenimiento"
    url_regreso_name = "historial_mantenimientos"
    texto_regreso = "Volver a Mantenimientos"
    success_url = reverse_lazy("historial_mantenimientos")


@staff_required
def finalizar_mantenimiento(request: HttpRequest, id: int) -> HttpResponseRedirect:
    mant = get_object_or_404(Mantenimiento, id=id)
    if request.method == "POST":
        services.finalizar_mantenimiento(mant)
    return redirect("flotilla")


@login_required(login_url="/login/")
def historial_mantenimientos(request: HttpRequest) -> HttpResponse:
    mantenimientos = Mantenimiento.objects.exclude(vehiculo__estado="BAJA").order_by(
        "-fecha_servicio"
    )
    context: dict[str, Any] = {"mantenimientos": mantenimientos}
    return render(request, "control_vehicular/historial_mantenimientos.html", context)


class RegistrarPolizaView(AdminRequiredMixin, FleetFormMixin, CreateView):
    model = PolizaSeguro
    form_class = PolizaSeguroForm
    titulo = "Registrar Póliza de Seguro"
    url_regreso_name = "dashboard"
    texto_regreso = "Volver al Dashboard"
    success_url = reverse_lazy("dashboard")


# ==========================================
# DRIVER MANAGEMENT (CBVs + FBVs)
# ==========================================


@login_required(login_url="/login/")
def lista_choferes(request: HttpRequest) -> HttpResponse:
    context: dict[str, Any] = {"choferes": Chofer.objects.filter(estado="ACTIVO")}
    return render(request, "control_vehicular/choferes.html", context)


class RegistrarChoferView(AdminRequiredMixin, FleetFormMixin, CreateView):
    model = Chofer
    form_class = ChoferForm
    titulo = "Registrar Nuevo Operador"
    url_regreso_name = "lista_choferes"
    texto_regreso = "Volver a Operadores"
    success_url = reverse_lazy("lista_choferes")


class EditarChoferView(AdminRequiredMixin, FleetFormMixin, UpdateView):
    model = Chofer
    form_class = ChoferForm
    titulo = "⚙️ Editar Datos del Chofer"
    url_regreso_name = "lista_choferes"
    texto_regreso = "Volver a Operadores"
    success_url = reverse_lazy("lista_choferes")


@admin_required
def baja_chofer(request: HttpRequest, id: int) -> HttpResponseRedirect:
    chofer = get_object_or_404(Chofer, id=id)
    if request.method == "POST":
        services.dar_baja_chofer(chofer)
    return redirect("lista_choferes")


@login_required(login_url="/login/")
def choferes_baja(request: HttpRequest) -> HttpResponse:
    context: dict[str, Any] = {"choferes": Chofer.objects.filter(estado="BAJA")}
    return render(request, "control_vehicular/choferes_baja.html", context)


@admin_required
def reactivar_chofer(request: HttpRequest, id: int) -> HttpResponseRedirect:
    chofer = get_object_or_404(Chofer, id=id)
    if request.method == "POST":
        services.reactivar_chofer(chofer)
    return redirect("choferes_baja")


# ==========================================
# OPERATIONAL ASSIGNMENTS (CBV + FBV)
# ==========================================


class AsignarVehiculoView(AdminRequiredMixin, FleetFormMixin, CreateView):
    model = Asignacion
    form_class = AsignacionForm
    titulo = "Asignar Vehículo a Operador"
    url_regreso_name = "flotilla"
    texto_regreso = "Volver a Flotilla"
    success_url = reverse_lazy("flotilla")

    def get_initial(self) -> dict[str, Any]:
        initial = super().get_initial()
        vehiculo_id = self.request.GET.get("vehiculo")
        if vehiculo_id:
            initial["vehiculo"] = vehiculo_id
        return initial

    def form_valid(self, form: AsignacionForm) -> HttpResponseRedirect:
        asignacion = form.save(commit=False)
        services.activar_asignacion(asignacion)
        return HttpResponseRedirect(self.get_success_url())


@admin_required
def liberar_vehiculo(request: HttpRequest, id: int) -> HttpResponseRedirect:
    if request.method == "POST":
        vehiculo = get_object_or_404(Vehiculo, id=id)
        nuevo_km_raw = request.POST.get("kilometraje_regreso")
        services.liberar_vehiculo(vehiculo, nuevo_km_raw)
    return redirect("flotilla")


# ==========================================
# INSURANCE POLICIES (FBVs)
# ==========================================


@login_required(login_url="/login/")
def lista_polizas(request: HttpRequest) -> HttpResponse:
    polizas = (
        PolizaSeguro.objects.select_related("vehiculo")
        .exclude(vehiculo__estado="BAJA")
        .order_by("fecha_vencimiento")
    )
    hoy = timezone.now().date()
    context: dict[str, Any] = {"polizas": polizas, "hoy": hoy}
    return render(request, "control_vehicular/polizas.html", context)


@login_required(login_url="/login/")
def editar_poliza(request: HttpRequest, id: int) -> HttpResponse:
    poliza = get_object_or_404(PolizaSeguro, id=id)
    if request.method == "POST":
        form = PolizaSeguroForm(request.POST, instance=poliza)
        if form.is_valid():
            form.save()
            return redirect("lista_polizas")
    else:
        form = PolizaSeguroForm(instance=poliza)
    context: dict[str, Any] = {
        "form": form,
        "titulo": f"Editar Póliza: {poliza.vehiculo.placas}",
        "url_regreso": reverse("lista_polizas"),
        "texto_regreso": "Volver a Pólizas",
    }
    return render(request, "control_vehicular/crear_vehiculo.html", context)
