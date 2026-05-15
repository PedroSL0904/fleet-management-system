from django.contrib import admin
from .models import PerfilUsuario, Vehiculo, Asignacion, Mantenimiento, PolizaSeguro

admin.site.site_header = "Administración de FleetPro"
admin.site.site_title = "Portal FleetPro"
admin.site.index_title = "Panel de Control de Flotilla"

admin.site.register(PerfilUsuario)
admin.site.register(Vehiculo)
admin.site.register(Asignacion)
admin.site.register(Mantenimiento)
admin.site.register(PolizaSeguro)