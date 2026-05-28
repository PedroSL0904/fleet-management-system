from django.urls import path
from . import views

urlpatterns = [
    # Dashboard & Reporting
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("flotilla/", views.FlotillaView.as_view(), name="flotilla"),
    path("exportar-pdf/", views.ExportarPDFView.as_view(), name="exportar_pdf"),
    # Vehicle Management
    path(
        "agregar-vehiculo/",
        views.AgregarVehiculoView.as_view(),
        name="agregar_vehiculo",
    ),
    path(
        "editar-vehiculo/<int:id>/",
        views.EditarVehiculoView.as_view(),
        name="editar_vehiculo",
    ),
    path(
        "eliminar-vehiculo/<int:id>/",
        views.EliminarVehiculoView.as_view(),
        name="eliminar_vehiculo",
    ),
    path("vehiculos-baja/", views.VehiculosBajaView.as_view(), name="vehiculos_baja"),
    path(
        "reactivar-vehiculo/<int:id>/",
        views.ReactivarVehiculoView.as_view(),
        name="reactivar_vehiculo",
    ),
    # Drivers
    path("choferes/", views.ListaChoferesView.as_view(), name="lista_choferes"),
    path(
        "registrar-chofer/",
        views.RegistrarChoferView.as_view(),
        name="registrar_chofer",
    ),
    path(
        "editar-chofer/<int:id>/",
        views.EditarChoferView.as_view(),
        name="editar_chofer",
    ),
    path("baja-chofer/<int:id>/", views.BajaChoferView.as_view(), name="baja_chofer"),
    path("choferes-baja/", views.ChoferesBajaView.as_view(), name="choferes_baja"),
    path(
        "reactivar-chofer/<int:id>/",
        views.ReactivarChoferView.as_view(),
        name="reactivar_chofer",
    ),
    # Operations & Assignments
    path(
        "asignar-vehiculo/",
        views.AsignarVehiculoView.as_view(),
        name="asignar_vehiculo",
    ),
    path(
        "liberar-vehiculo/<int:id>/",
        views.LiberarVehiculoView.as_view(),
        name="liberar_vehiculo",
    ),
    # Maintenance & Insurance
    path(
        "registrar-mantenimiento/",
        views.RegistrarMantenimientoView.as_view(),
        name="registrar_mantenimiento",
    ),
    path(
        "editar-mantenimiento/<int:id>/",
        views.EditarMantenimientoView.as_view(),
        name="editar_mantenimiento",
    ),
    path(
        "historial-mantenimientos/",
        views.HistorialMantenimientosView.as_view(),
        name="historial_mantenimientos",
    ),
    path(
        "finalizar-mantenimiento/<int:id>/",
        views.FinalizarMantenimientoView.as_view(),
        name="finalizar_mantenimiento",
    ),
    path("polizas/", views.ListaPolizasView.as_view(), name="lista_polizas"),
    path(
        "registrar-poliza/",
        views.RegistrarPolizaView.as_view(),
        name="registrar_poliza",
    ),
    path(
        "editar-poliza/<int:id>/",
        views.EditarPolizaView.as_view(),
        name="editar_poliza",
    ),
]
