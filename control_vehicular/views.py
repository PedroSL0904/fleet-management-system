import logging
from decimal import Decimal, InvalidOperation
from datetime import timedelta
from typing import Any

from django.urls import reverse
from django.utils import timezone
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template.loader import get_template
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Avg

from xhtml2pdf import pisa # type: ignore

from .models import Vehiculo, Asignacion, Mantenimiento, PolizaSeguro, Chofer
from .forms import VehiculoForm, MantenimientoForm, PolizaSeguroForm, ChoferForm, AsignacionForm

logger = logging.getLogger(__name__)


# ==========================================
# DASHBOARD & REPORTING
# ==========================================

@login_required(login_url='/login/')
def dashboard(request: HttpRequest) -> HttpResponse:
    hoy = timezone.now().date()
    limite_30 = hoy + timedelta(days=30)
    limite_7  = hoy + timedelta(days=7)

    vehiculos_activos = Vehiculo.objects.exclude(estado='BAJA')
    total_v     = vehiculos_activos.count()
    disponibles = vehiculos_activos.filter(estado='DISPONIBLE').count()
    en_ruta     = vehiculos_activos.filter(estado='EN_RUTA').count()
    en_taller   = vehiculos_activos.filter(estado='EN_TALLER').count()

    tasa_disponibilidad = round((disponibles / total_v * 100), 1) if total_v > 0 else 0

    gasto_total    = Mantenimiento.objects.filter(estado='FINALIZADO').aggregate(total=Sum('costo'))['total'] or Decimal('0.00')
    costo_promedio = Mantenimiento.objects.filter(estado='FINALIZADO').aggregate(avg=Avg('costo'))['avg']   or Decimal('0.00')
    km_promedio    = vehiculos_activos.aggregate(avg=Avg('kilometraje_actual'))['avg'] or Decimal('0.00')

    # Maintenance counts for bar chart
    mant_preventivo = Mantenimiento.objects.filter(tipo='PREVENTIVO').count()
    mant_correctivo = Mantenimiento.objects.filter(tipo='CORRECTIVO').count()
    mant_estetico   = Mantenimiento.objects.filter(tipo='ESTETICO').count()

    total_viajes    = Asignacion.objects.count()
    viajes_este_mes = Asignacion.objects.filter(fecha_salida__month=hoy.month, fecha_salida__year=hoy.year).count()

    # Active maintenance (pending or in-progress)
    mant_activos = Mantenimiento.objects.select_related('vehiculo').filter(
        estado__in=['PENDIENTE', 'EN_PROCESO']
    ).exclude(vehiculo__estado='BAJA')

    # Insurance policies expiring within 7 days (critical) and 30 days (warning)
    # Only show policies that haven't expired yet (fecha_vencimiento >= hoy)
    polizas_criticas = PolizaSeguro.objects.select_related('vehiculo').filter(
        fecha_vencimiento__gte=hoy,
        fecha_vencimiento__lte=limite_7,
    ).exclude(vehiculo__estado='BAJA')

    polizas_proximas = PolizaSeguro.objects.select_related('vehiculo').filter(
        fecha_vencimiento__gte=hoy,
        fecha_vencimiento__lte=limite_30,
    ).exclude(vehiculo__estado='BAJA')

    # Driver licenses expiring within 30 days
    licencias_proximas = Chofer.objects.filter(
        estado='ACTIVO',
        vencimiento_licencia__gte=hoy,
        vencimiento_licencia__lte=limite_30,
    )

    asignaciones_activas   = Asignacion.objects.select_related('vehiculo', 'chofer').filter(estado='ACTIVA')
    mantenimientos_recientes = Mantenimiento.objects.exclude(vehiculo__estado='BAJA').select_related('vehiculo').order_by('-fecha_servicio')[:5]
    vehiculo_mas_km        = vehiculos_activos.order_by('-kilometraje_actual').first()

    context: dict[str, Any] = {
        'total_vehiculos': total_v,
        'disponibles': disponibles,
        'en_ruta': en_ruta,
        'en_taller': en_taller,
        'tasa_disponibilidad': tasa_disponibilidad,
        'total_choferes': Chofer.objects.filter(estado='ACTIVO').count(),
        'gasto_total': gasto_total,
        'costo_promedio': round(costo_promedio, 2),
        'total_viajes': total_viajes,
        'viajes_este_mes': viajes_este_mes,
        'asignaciones_activas': asignaciones_activas,
        'mant_preventivo': mant_preventivo,
        'mant_correctivo': mant_correctivo,
        'mant_estetico': mant_estetico,
        'mant_activos': mant_activos,
        'mantenimientos_recientes': mantenimientos_recientes,
        'vehiculo_mas_km': vehiculo_mas_km,
        'km_promedio': round(km_promedio, 0),
        'polizas_criticas': polizas_criticas,
        'polizas_proximas': polizas_proximas,
        'licencias_proximas': licencias_proximas,
        'total_alertas_criticas': polizas_criticas.count() + mant_activos.count(),
        'hoy': hoy,
    }

    return render(request, 'control_vehicular/dashboard.html', context)


@login_required(login_url='/login/')
def flotilla(request: HttpRequest) -> HttpResponse:
    vehiculos_activos = Vehiculo.objects.exclude(estado='BAJA')
    context: dict[str, Any] = {
        'vehiculos': vehiculos_activos,
        'total_vehiculos': vehiculos_activos.count(),
        'disponibles': vehiculos_activos.filter(estado='DISPONIBLE').count(),
        'en_taller': vehiculos_activos.filter(estado='EN_TALLER').count(),
        'en_ruta': vehiculos_activos.filter(estado='EN_RUTA').count(),
    }
    return render(request, 'control_vehicular/flotilla.html', context)


@login_required(login_url='/login/')
def exportar_pdf(request: HttpRequest) -> HttpResponse:
    hoy           = timezone.now().date()
    limite_alerta = hoy + timedelta(days=30)
    vehiculos     = Vehiculo.objects.exclude(estado='BAJA')
    gasto_total   = Mantenimiento.objects.filter(estado='FINALIZADO').aggregate(total=Sum('costo'))['total'] or Decimal('0.00')

    context: dict[str, Any] = {
        'fecha_generacion': timezone.now(),
        'generado_por': getattr(request.user, 'get_full_name', lambda: request.user.username)(),
        'kpis': {
            'total': vehiculos.count(),
            'disponibles': vehiculos.filter(estado='DISPONIBLE').count(),
            'en_ruta': vehiculos.filter(estado='EN_RUTA').count(),
            'en_taller': vehiculos.filter(estado='EN_TALLER').count(),
            'gasto_mantenimiento': gasto_total,
        },
        'vehiculos': vehiculos,
        'asignaciones': Asignacion.objects.select_related('vehiculo', 'chofer').filter(estado='ACTIVA'),
        'alertas_mantenimiento': Mantenimiento.objects.select_related('vehiculo').filter(estado__in=['PENDIENTE', 'EN_PROCESO']).exclude(vehiculo__estado='BAJA'),
        'alertas_polizas': PolizaSeguro.objects.select_related('vehiculo').filter(fecha_vencimiento__lte=limite_alerta).exclude(vehiculo__estado='BAJA'),
    }

    template    = get_template('control_vehicular/reporte_pdf.html')
    html        = template.render(context)
    fecha_arch  = timezone.localtime(timezone.now()).strftime("%Y%m%d_%H%M")
    response    = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="FleetPro_Reporte_{fecha_arch}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response) # type: ignore
    if pisa_status.err: # type: ignore
        logger.error("PDF generation failed.")
        return HttpResponse(f'Error generating PDF <pre>{html}</pre>', status=500)

    return response


# ==========================================
# VEHICLE MANAGEMENT
# ==========================================

@login_required(login_url='/login/')
def agregar_vehiculo(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = VehiculoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('flotilla')
    else:
        form = VehiculoForm()
    return render(request, 'control_vehicular/crear_vehiculo.html', {'form': form})


@login_required(login_url='/login/')
def editar_vehiculo(request: HttpRequest, id: int) -> HttpResponse:
    vehiculo = get_object_or_404(Vehiculo, id=id)
    if request.method == 'POST':
        form = VehiculoForm(request.POST, request.FILES, instance=vehiculo)
        if form.is_valid():
            form.save()
            return redirect('flotilla')
    else:
        form = VehiculoForm(instance=vehiculo)
    context: dict[str, Any] = {
        'form': form,
        'titulo': f'Editar Vehículo: {vehiculo.get_marca_display()} {vehiculo.modelo}',
        'url_regreso': reverse('flotilla'),
        'texto_regreso': 'Volver a Flotilla',
    }
    return render(request, 'control_vehicular/crear_vehiculo.html', context)


@login_required(login_url='/login/')
def eliminar_vehiculo(request: HttpRequest, id: int) -> HttpResponseRedirect:
    vehiculo = get_object_or_404(Vehiculo, id=id)
    if request.method == 'POST':
        vehiculo.estado = 'BAJA'
        vehiculo.save()
    return redirect('flotilla')


@login_required(login_url='/login/')
def vehiculos_baja(request: HttpRequest) -> HttpResponse:
    context: dict[str, Any] = {'vehiculos': Vehiculo.objects.filter(estado='BAJA')}
    return render(request, 'control_vehicular/vehiculos_baja.html', context)


@login_required(login_url='/login/')
def reactivar_vehiculo(request: HttpRequest, id: int) -> HttpResponseRedirect:
    vehiculo = get_object_or_404(Vehiculo, id=id)
    if request.method == 'POST':
        if Mantenimiento.objects.filter(vehiculo=vehiculo, estado='EN_PROCESO').exists():
            vehiculo.estado = 'EN_TALLER'
        elif Asignacion.objects.filter(vehiculo=vehiculo, estado='ACTIVA').exists():
            vehiculo.estado = 'EN_RUTA'
        else:
            vehiculo.estado = 'DISPONIBLE'
        vehiculo.save()
    return redirect('vehiculos_baja')


# ==========================================
# MAINTENANCE
# ==========================================

@login_required(login_url='/login/')
def registrar_mantenimiento(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = MantenimientoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('historial_mantenimientos')
    else:
        form = MantenimientoForm()
    context: dict[str, Any] = {
        'form': form,
        'titulo': 'Registrar Mantenimiento',
        'url_regreso': reverse('historial_mantenimientos'),
        'texto_regreso': 'Volver a Mantenimientos',
    }
    return render(request, 'control_vehicular/crear_vehiculo.html', context)


@login_required(login_url='/login/')
def editar_mantenimiento(request: HttpRequest, id: int) -> HttpResponse:
    mant = get_object_or_404(Mantenimiento, id=id)
    if request.method == 'POST':
        form = MantenimientoForm(request.POST, request.FILES, instance=mant)
        if form.is_valid():
            form.save()
            return redirect('historial_mantenimientos')
    else:
        form = MantenimientoForm(instance=mant)
    context: dict[str, Any] = {
        'form': form,
        'titulo': 'Gestionar Mantenimiento',
        'url_regreso': reverse('historial_mantenimientos'),
        'texto_regreso': 'Volver a Mantenimientos',
    }
    return render(request, 'control_vehicular/crear_vehiculo.html', context)


@login_required(login_url='/login/')
def finalizar_mantenimiento(request: HttpRequest, id: int) -> HttpResponseRedirect:
    mant = get_object_or_404(Mantenimiento, id=id)
    if request.method == 'POST':
        mant.estado = 'FINALIZADO'
        mant.save()
        if mant.vehiculo.estado == 'EN_TALLER':
            mant.vehiculo.estado = 'DISPONIBLE'
            mant.vehiculo.save()
    return redirect('flotilla')


@login_required(login_url='/login/')
def historial_mantenimientos(request: HttpRequest) -> HttpResponse:
    mantenimientos = Mantenimiento.objects.exclude(vehiculo__estado='BAJA').order_by('-fecha_servicio')
    context: dict[str, Any] = {'mantenimientos': mantenimientos}
    return render(request, 'control_vehicular/historial_mantenimientos.html', context)


# ==========================================
# INSURANCE POLICIES
# ==========================================

@login_required(login_url='/login/')
def lista_polizas(request: HttpRequest) -> HttpResponse:
    polizas = PolizaSeguro.objects.select_related('vehiculo').exclude(
        vehiculo__estado='BAJA'
    ).order_by('fecha_vencimiento')
    hoy = timezone.now().date()
    context: dict[str, Any] = {'polizas': polizas, 'hoy': hoy}
    return render(request, 'control_vehicular/polizas.html', context)


@login_required(login_url='/login/')
def registrar_poliza(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = PolizaSeguroForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_polizas')
    else:
        form = PolizaSeguroForm()
    context: dict[str, Any] = {
        'form': form,
        'titulo': 'Registrar Póliza de Seguro',
        'url_regreso': reverse('lista_polizas'),
        'texto_regreso': 'Volver a Pólizas',
    }
    return render(request, 'control_vehicular/crear_vehiculo.html', context)


@login_required(login_url='/login/')
def editar_poliza(request: HttpRequest, id: int) -> HttpResponse:
    poliza = get_object_or_404(PolizaSeguro, id=id)
    if request.method == 'POST':
        form = PolizaSeguroForm(request.POST, instance=poliza)
        if form.is_valid():
            form.save()
            return redirect('lista_polizas')
    else:
        form = PolizaSeguroForm(instance=poliza)
    context: dict[str, Any] = {
        'form': form,
        'titulo': f'Editar Póliza: {poliza.vehiculo.placas}',
        'url_regreso': reverse('lista_polizas'),
        'texto_regreso': 'Volver a Pólizas',
    }
    return render(request, 'control_vehicular/crear_vehiculo.html', context)


# ==========================================
# DRIVER MANAGEMENT
# ==========================================

@login_required(login_url='/login/')
def lista_choferes(request: HttpRequest) -> HttpResponse:
    context: dict[str, Any] = {'choferes': Chofer.objects.filter(estado='ACTIVO')}
    return render(request, 'control_vehicular/choferes.html', context)


@login_required(login_url='/login/')
def registrar_chofer(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = ChoferForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('lista_choferes')
    else:
        form = ChoferForm()
    context: dict[str, Any] = {
        'form': form,
        'titulo': 'Registrar Nuevo Operador',
        'url_regreso': reverse('lista_choferes'),
        'texto_regreso': 'Volver a Operadores',
    }
    return render(request, 'control_vehicular/crear_vehiculo.html', context)


@login_required(login_url='/login/')
def editar_chofer(request: HttpRequest, id: int) -> HttpResponse:
    chofer = get_object_or_404(Chofer, id=id)
    if request.method == 'POST':
        form = ChoferForm(request.POST, request.FILES, instance=chofer)
        if form.is_valid():
            form.save()
            return redirect('lista_choferes')
    else:
        form = ChoferForm(instance=chofer)
    context: dict[str, Any] = {
        'form': form,
        'titulo': f'Editar Operador: {chofer.nombre} {chofer.apellidos}',
        'url_regreso': reverse('lista_choferes'),
        'texto_regreso': 'Volver a Operadores',
    }
    return render(request, 'control_vehicular/crear_vehiculo.html', context)


@login_required(login_url='/login/')
def baja_chofer(request: HttpRequest, id: int) -> HttpResponseRedirect:
    chofer = get_object_or_404(Chofer, id=id)
    if request.method == 'POST':
        chofer.estado = 'BAJA'
        chofer.save()
    return redirect('lista_choferes')


@login_required(login_url='/login/')
def choferes_baja(request: HttpRequest) -> HttpResponse:
    context: dict[str, Any] = {'choferes': Chofer.objects.filter(estado='BAJA')}
    return render(request, 'control_vehicular/choferes_baja.html', context)


@login_required(login_url='/login/')
def reactivar_chofer(request: HttpRequest, id: int) -> HttpResponseRedirect:
    chofer = get_object_or_404(Chofer, id=id)
    if request.method == 'POST':
        chofer.estado = 'ACTIVO'
        chofer.save()
    return redirect('choferes_baja')


# ==========================================
# ASSIGNMENTS
# ==========================================

@login_required(login_url='/login/')
def asignar_vehiculo(request: HttpRequest) -> HttpResponse:
    datos_iniciales: dict[str, Any] = {}
    vehiculo_id = request.GET.get('vehiculo')
    if vehiculo_id:
        datos_iniciales['vehiculo'] = vehiculo_id

    if request.method == 'POST':
        form = AsignacionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('flotilla')
    else:
        form = AsignacionForm(initial=datos_iniciales)
    context: dict[str, Any] = {
        'form': form,
        'titulo': 'Asignar Vehículo a Operador',
        'url_regreso': reverse('flotilla'),
        'texto_regreso': 'Volver a Flotilla',
    }
    return render(request, 'control_vehicular/crear_vehiculo.html', context)


@login_required(login_url='/login/')
def liberar_vehiculo(request: HttpRequest, id: int) -> HttpResponseRedirect:
    if request.method == 'POST':
        vehiculo = get_object_or_404(Vehiculo, id=id)
        nuevo_km_raw = request.POST.get('kilometraje_regreso')
        if nuevo_km_raw:
            try:
                vehiculo.kilometraje_actual = Decimal(nuevo_km_raw)
            except InvalidOperation:
                logger.warning(f"Invalid mileage input: {nuevo_km_raw}")
        vehiculo.estado = 'DISPONIBLE'
        vehiculo.save()

        asignacion = Asignacion.objects.filter(vehiculo=vehiculo, estado='ACTIVA').first()
        if asignacion:
            asignacion.estado = 'FINALIZADA'
            asignacion.save()

    return redirect('flotilla')