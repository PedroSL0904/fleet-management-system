import datetime
from decimal import Decimal
from typing import Any, TYPE_CHECKING

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

# ==========================================
# TYPE HINTING HELPERS
# ==========================================
if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager
    class AsignacionManager(RelatedManager["Asignacion"]):
        pass
else:
    AsignacionManager = Any


# ==========================================
# ENTERPRISE VALIDATORS (Poka-Yoke)
# ==========================================
# Strict rules to prevent human error and ensure data integrity.


plate_validator = RegexValidator(
    regex=r'^[A-Z0-9\-]{6,10}$',
    message="Formato inválido. Usa solo mayúsculas, números y guiones (Ej. UMK-123-A)."
)

vin_validator = RegexValidator(
    regex=r'^[A-HJ-NPR-Z0-9]{17}$',
    message="El VIN debe tener 17 caracteres alfanuméricos. No se permiten las letras I, O, ni Q."
)

phone_validator = RegexValidator(
    regex=r'^\d{10}$',
    message="El teléfono debe tener exactamente 10 números, sin espacios ni ladas internacionales."
)

def current_year() -> int:
    return datetime.date.today().year

def validar_vencimiento_licencia(value: datetime.date) -> None:
    """Valida que la licencia no esté vencida ni tenga una fecha irreal."""
    hoy = datetime.date.today()
    if value < hoy:
        raise ValidationError("Inconsistencia: La licencia ya está vencida o vence hoy. No es válida para registro.")
    
    limite_maximo = hoy + datetime.timedelta(days=365 * 10) # 10 años de vigencia máxima
    if value > limite_maximo:
        raise ValidationError("Inconsistencia: La fecha de vencimiento es irreal (supera los 10 años permitidos).")


# ==========================================
# 1. USER PROFILES
# ==========================================
class PerfilUsuario(models.Model):
    ROLES = (
        ('ADMIN', 'Administrador General'),
        ('MECANICO', 'Soporte / Mecánico'),
        ('CHOFER', 'Chofer'),
    )
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rol = models.CharField(max_length=15, choices=ROLES, default='CHOFER')
    numero_licencia = models.CharField(max_length=50, blank=True, null=True, verbose_name="Número de Licencia")
    vencimiento_licencia = models.DateField(blank=True, null=True, verbose_name="Vencimiento de Licencia")

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuarios"

    def __str__(self) -> str:
        rol_display = getattr(self, 'get_rol_display', lambda: self.rol)()
        return f"{self.usuario.username} - {rol_display}"


# ==========================================
# 2. FLEET DIRECTORY
# ==========================================
class Vehiculo(models.Model):
    # Dictionaries to eliminate typing errors (Replaces free-text CharFields)
    MARCAS = (
        ('NISSAN', 'Nissan'), ('TOYOTA', 'Toyota'), ('HONDA', 'Honda'),
        ('MAZDA', 'Mazda'), ('SUZUKI', 'Suzuki'), ('MITSUBISHI', 'Mitsubishi'),
        ('SUBARU', 'Subaru'), ('CHEVROLET', 'Chevrolet'), ('FORD', 'Ford'),
        ('DODGE', 'Dodge'), ('RAM', 'RAM'), ('JEEP', 'Jeep'), ('GMC', 'GMC'), 
        ('CADILLAC', 'Cadillac'), ('VOLKSWAGEN', 'Volkswagen'), ('SEAT', 'SEAT'), 
        ('CUPRA', 'Cupra'), ('BMW', 'BMW'), ('MERCEDES_BENZ', 'Mercedes-Benz'), 
        ('AUDI', 'Audi'), ('RENAULT', 'Renault'), ('PEUGEOT', 'Peugeot'), 
        ('FIAT', 'Fiat'), ('VOLVO', 'Volvo'), ('KIA', 'Kia'), ('HYUNDAI', 'Hyundai'), 
        ('MG', 'MG'), ('CHIREY', 'Chirey'), ('OMODA', 'Omoda'), ('JAC', 'JAC'), 
        ('BYD', 'BYD'), ('GEELY', 'Geely'), ('GWM', 'GWM'), ('JETOUR', 'Jetour'), 
        ('TESLA', 'Tesla'), ('PORSCHE', 'Porsche'), ('LAND_ROVER', 'Land Rover'), 
        ('LEXUS', 'Lexus'), ('INFINITI', 'Infiniti'), ('FERRARI', 'Ferrari'), 
        ('LAMBORGHINI', 'Lamborghini'), ('OTRA', 'Otra (Especificar en modelo)'),
    )
    ESTADOS = (
        ('DISPONIBLE', 'Disponible'),
        ('EN_RUTA', 'En Ruta'),
        ('EN_TALLER', 'En Mantenimiento'),
        ('BAJA', 'Dado de Baja'),
    )
    
    # Applied strict Regex and Min/Max validators
    placas = models.CharField(max_length=10, unique=True, validators=[plate_validator], verbose_name="Placas")
    marca = models.CharField(max_length=20, choices=MARCAS, default='NISSAN', verbose_name="Marca")
    modelo = models.CharField(max_length=50, verbose_name="Modelo")
    anio = models.IntegerField(
        validators=[MinValueValidator(2000), MaxValueValidator(current_year() + 1)],
        verbose_name="Año"
    )
    vin = models.CharField(max_length=17, unique=True, validators=[vin_validator], verbose_name="Número de Serie (VIN)")
    estado = models.CharField(max_length=15, choices=ESTADOS, default='DISPONIBLE', verbose_name="Estado Operativo")
    kilometraje_actual = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'), 
        validators=[MinValueValidator(Decimal('0.00'))], # Prevents negative mileage
        verbose_name="Kilometraje Actual"
    )
    foto = models.ImageField(upload_to='vehiculos/', blank=True, null=True, verbose_name="Fotografía")

    asignacion_set: AsignacionManager

    class Meta:
        verbose_name = "Vehículo"
        verbose_name_plural = "Vehículos"
        ordering = ['marca', 'modelo']

    def __str__(self) -> str:
        marca_display = getattr(self, 'get_marca_display', lambda: self.marca)()
        return f"{marca_display} {self.modelo} ({self.placas})"

    def get_chofer_actual(self) -> str:
        viaje_actual = self.asignacion_set.select_related('chofer').filter(estado='ACTIVA').first()
        if viaje_actual and hasattr(viaje_actual, 'chofer'):
            return f"{viaje_actual.chofer.nombre} {viaje_actual.chofer.apellidos}"
        return "Sin asignar"


# ==========================================
# 3. DRIVERS DIRECTORY
# ==========================================
class Chofer(models.Model):
    TIPOS_LICENCIA = (
        ('A', 'Tipo A (Particulares)'),
        ('B', 'Tipo B (Mercantil/Transporte)'),
        ('C', 'Tipo C (Carga)'),
    )
    ESTADOS_CHOFER = (
        ('ACTIVO', 'Activo'),
        ('BAJA', 'Dado de Baja'),
    )
    
    nombre = models.CharField(max_length=50, verbose_name="Nombre(s)")
    apellidos = models.CharField(max_length=50, verbose_name="Apellidos")
    # Applied Phone Regex Validator
    telefono = models.CharField(max_length=10, validators=[phone_validator], verbose_name="Teléfono (10 dígitos)")
    tipo_licencia = models.CharField(max_length=2, choices=TIPOS_LICENCIA, default='A', verbose_name="Tipo de Licencia")
    numero_licencia = models.CharField(max_length=50, unique=True, verbose_name="Número de Licencia")
    vencimiento_licencia = models.DateField(
        validators=[validar_vencimiento_licencia], 
        verbose_name="Vencimiento de Licencia"
    )
    estado = models.CharField(max_length=10, choices=ESTADOS_CHOFER, default='ACTIVO', verbose_name="Estado Laboral")
    foto = models.ImageField(upload_to='choferes/', blank=True, null=True, verbose_name="Fotografía")

    class Meta:
        verbose_name = "Chofer"
        verbose_name_plural = "Choferes"
        ordering = ['apellidos', 'nombre']

    def __str__(self) -> str:
        return f"{self.nombre} {self.apellidos} - Lic. Tipo {self.tipo_licencia}"


# ==========================================
# 4. ASSIGNMENTS LOG
# ==========================================
class Asignacion(models.Model):
    ESTADOS = (
        ('ACTIVA', 'Activa (En Ruta)'),
        ('FINALIZADA', 'Finalizada (Devuelto)'),
    )
    
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, verbose_name="Vehículo")
    chofer = models.ForeignKey(Chofer, on_delete=models.CASCADE, verbose_name="Operador")
    fecha_salida = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Salida")
    fecha_devolucion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Devolución")
    estado = models.CharField(max_length=15, choices=ESTADOS, default='ACTIVA', verbose_name="Estado")

    class Meta:
        verbose_name = "Asignación de Viaje"
        verbose_name_plural = "Bitácora de Asignaciones"
        ordering = ['-fecha_salida']

    def __str__(self) -> str:
        return f"Viaje: {self.vehiculo.placas} - {self.chofer.nombre}"


# ==========================================
# 5. MAINTENANCE
# ==========================================
class Mantenimiento(models.Model):
    TIPOS = (
        ('PREVENTIVO', 'Preventivo (Afinación, Aceite)'),
        ('CORRECTIVO', 'Correctivo (Falla mecánica)'),
        ('ESTETICO', 'Estético (Hojalatería, Lavado)'),
    )
    ESTADOS_MANTENIMIENTO = (
        ('PENDIENTE', 'Pendiente'),
        ('EN_PROCESO', 'En Proceso'),
        ('FINALIZADO', 'Finalizado'),
    )
    
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, verbose_name="Vehículo")
    tipo = models.CharField(max_length=15, choices=TIPOS, verbose_name="Tipo de Servicio")
    fecha_servicio = models.DateField(verbose_name="Fecha Salida")
    fecha_regreso = models.DateField(blank=True, null=True, verbose_name="Fecha Regreso Estimada")
    # Prevents negative costs
    costo = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))], verbose_name="Costo Total")
    taller = models.CharField(max_length=100, verbose_name="Taller")
    descripcion_trabajo = models.TextField(verbose_name="Descripción")
    estado = models.CharField(max_length=20, choices=ESTADOS_MANTENIMIENTO, default='PENDIENTE', verbose_name="Estado")
    comprobante = models.FileField(upload_to='comprobantes/', blank=True, null=True, verbose_name="Factura")

    class Meta:
        verbose_name = "Registro de Mantenimiento"
        verbose_name_plural = "Historial de Mantenimientos"
        ordering = ['-fecha_servicio']

    def __str__(self) -> str:
        tipo_display = getattr(self, 'get_tipo_display', lambda: self.tipo)()
        return f"{tipo_display} - {self.vehiculo.placas}"


# ==========================================
# 6. INSURANCE POLICIES
# ==========================================
class PolizaSeguro(models.Model):
    ASEGURADORAS = (
        ('QUALITAS', 'Quálitas'),
        ('GNP', 'GNP Seguros'),
        ('HDI', 'HDI Seguros'),
        ('MAPFRE', 'MAPFRE'),
        ('AXA', 'AXA Seguros'),
        ('INBURSA', 'Inbursa'),
        ('ZURICH', 'Zurich'),
        ('OTRA', 'Otra'),
    )
    
    vehiculo = models.OneToOneField(Vehiculo, on_delete=models.CASCADE, verbose_name="Vehículo")
    # Transformed from free-text to strict choices
    aseguradora = models.CharField(max_length=50, choices=ASEGURADORAS, verbose_name="Aseguradora")
    numero_poliza = models.CharField(max_length=50, verbose_name="No. Póliza")
    fecha_vencimiento = models.DateField(verbose_name="Vencimiento")

    class Meta:
        verbose_name = "Póliza de Seguro"
        verbose_name_plural = "Pólizas de Seguros"
        ordering = ['fecha_vencimiento']

    def estado_semaforo(self) -> str:
        dias_restantes = (self.fecha_vencimiento - timezone.now().date()).days
        if dias_restantes <= 0:
            return 'VENCIDA'
        elif dias_restantes <= 30:
            return 'POR_VENCER'
        return 'VIGENTE'

    def __str__(self) -> str:
        aseg_display = getattr(self, 'get_aseguradora_display', lambda: self.aseguradora)()
        return f"Póliza {aseg_display} - {self.vehiculo.placas}"