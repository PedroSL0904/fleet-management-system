from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),
    path("flotilla/", views.flotilla, name="flotilla"),
    path("exportar-pdf/", views.exportar_pdf, name="exportar_pdf"),
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
        "eliminar-vehiculo/<int:id>/", views.eliminar_vehiculo, name="eliminar_vehiculo"
    ),
    path("vehiculos-baja/", views.vehiculos_baja, name="vehiculos_baja"),
    path(
        "reactivar-vehiculo/<int:id>/",
        views.reactivar_vehiculo,
        name="reactivar_vehiculo",
    ),
    # Drivers
    path("choferes/", views.lista_choferes, name="lista_choferes"),
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
    path("baja-chofer/<int:id>/", views.baja_chofer, name="baja_chofer"),
    path("choferes-baja/", views.choferes_baja, name="choferes_baja"),
    path("reactivar-chofer/<int:id>/", views.reactivar_chofer, name="reactivar_chofer"),
    # Operations & Assignments
    path(
        "asignar-vehiculo/",
        views.AsignarVehiculoView.as_view(),
        name="asignar_vehiculo",
    ),
    path("liberar-vehiculo/<int:id>/", views.liberar_vehiculo, name="liberar_vehiculo"),
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
        views.historial_mantenimientos,
        name="historial_mantenimientos",
    ),
    path(
        "finalizar-mantenimiento/<int:id>/",
        views.finalizar_mantenimiento,
        name="finalizar_mantenimiento",
    ),
    path("polizas/", views.lista_polizas, name="lista_polizas"),
    path(
        "registrar-poliza/",
        views.RegistrarPolizaView.as_view(),
        name="registrar_poliza",
    ),
    path("editar-poliza/<int:id>/", views.editar_poliza, name="editar_poliza"),
]
