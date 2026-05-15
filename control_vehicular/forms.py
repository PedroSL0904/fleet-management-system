import json
import datetime
from typing import Any, cast

from django import forms
from django.core.exceptions import ValidationError
from .models import Vehiculo, Mantenimiento, PolizaSeguro, Asignacion, Chofer
# ==========================================
# ENTERPRISE AUTOMOTIVE CATALOG (DEFINITIVE EDITION)
# ==========================================
CATALOGO_AUTOS: dict[str, list[tuple[str, str]]] = {
    # ================= COREANAS =================
    'KIA': [('K3', 'K3'), ('K4', 'K4'), ('RIO', 'Rio'), ('FORTE', 'Forte'), ('SOUL', 'Soul'), ('OPTIMA', 'Optima'), ('STINGER', 'Stinger'), ('SPORTAGE', 'Sportage'), ('SELTOS', 'Seltos'), ('SORENTO', 'Sorento'), ('NIRO', 'Niro'), ('EV6', 'EV6'), ('EV9', 'EV9'), ('CARNIVAL', 'Carnival / Sedona'), ('TELLURIDE', 'Telluride')],
    'HYUNDAI': [('GRAND_I10', 'Grand i10'), ('HB20', 'HB20'), ('ACCENT', 'Accent'), ('ELANTRA', 'Elantra'), ('SONATA', 'Sonata'), ('CRETA', 'Creta'), ('IX35', 'ix35'), ('TUCSON', 'Tucson'), ('SANTA_FE', 'Santa Fe'), ('PALISADE', 'Palisade'), ('IONIQ', 'Ioniq / Ioniq 5'), ('STARIA', 'Staria'), ('H100', 'H-100')],

    # ================= JAPONESAS =================
    'NISSAN': [('VERSA', 'Versa'), ('SENTRA', 'Sentra'), ('MARCH', 'March'), ('ALTIMA', 'Altima'), ('MAXIMA', 'Maxima'), ('NP300', 'NP300 / Frontier'), ('URVAN', 'Urvan'), ('KICKS', 'Kicks'), ('XTRAIL', 'X-Trail'), ('PATHFINDER', 'Pathfinder'), ('ARMADA', 'Armada'), ('LEAF', 'Leaf'), ('TSURU', 'Tsuru'), ('TIIDA', 'Tiida'), ('NOTE', 'Note'), ('Z', 'Nissan Z / 370Z')],
    'TOYOTA': [('YARIS', 'Yaris'), ('COROLLA', 'Corolla'), ('CAMRY', 'Camry'), ('PRIUS', 'Prius'), ('RAIZE', 'Raize'), ('COROLLA_CROSS', 'Corolla Cross'), ('HILUX', 'Hilux'), ('TACOMA', 'Tacoma'), ('TUNDRA', 'Tundra'), ('HIACE', 'Hiace'), ('RAV4', 'RAV4'), ('HIGHLANDER', 'Highlander'), ('SIENNA', 'Sienna'), ('AVANZA', 'Avanza'), ('SUPRA', 'Supra'), ('LAND_CRUISER', 'Land Cruiser')],
    'HONDA': [('CITY', 'City'), ('CIVIC', 'Civic'), ('ACCORD', 'Accord'), ('FIT', 'Fit'), ('CRV', 'CR-V'), ('HRV', 'HR-V'), ('BRV', 'BR-V'), ('PILOT', 'Pilot'), ('ODYSSEY', 'Odyssey'), ('RIDGELINE', 'Ridgeline')],
    'MAZDA': [('MAZDA2', 'Mazda 2'), ('MAZDA3', 'Mazda 3'), ('MAZDA6', 'Mazda 6'), ('CX3', 'CX-3'), ('CX30', 'CX-30'), ('CX5', 'CX-5'), ('CX50', 'CX-50'), ('CX70', 'CX-70'), ('CX9', 'CX-9'), ('CX90', 'CX-90'), ('MX5', 'MX-5 Miata')],
    'SUZUKI': [('SWIFT', 'Swift'), ('IGNIS', 'Ignis'), ('BALENO', 'Baleno'), ('CIAZ', 'Ciaz'), ('VITARA', 'Vitara / Grand Vitara'), ('SCROSS', 'S-Cross'), ('JIMNY', 'Jimny'), ('ERTIGA', 'Ertiga'), ('FRONX', 'Fronx')],
    'MITSUBISHI': [('L200', 'L200'), ('OUTLANDER', 'Outlander'), ('MIRAGE', 'Mirage / G4'), ('MONTERO', 'Montero Sport'), ('ECLIPSE_CROSS', 'Eclipse Cross'), ('XPANDER', 'Xpander'), ('LANCER', 'Lancer')],
    'SUBARU': [('IMPREZA', 'Impreza'), ('WRX', 'WRX'), ('FORESTER', 'Forester'), ('OUTBACK', 'Outback'), ('CROSSTREK', 'Crosstrek / XV'), ('BRZ', 'BRZ')],
    'LEXUS': [('IS', 'IS'), ('ES', 'ES'), ('LS', 'LS'), ('UX', 'UX'), ('NX', 'NX'), ('RX', 'RX'), ('LX', 'LX')],
    'INFINITI': [('Q50', 'Q50'), ('Q60', 'Q60'), ('QX50', 'QX50'), ('QX55', 'QX55'), ('QX60', 'QX60'), ('QX80', 'QX80')],

    # ================= NORTEAMERICANAS =================
    'CHEVROLET': [('AVEO', 'Aveo'), ('ONIX', 'Onix'), ('CAVALIER', 'Cavalier'), ('SPARK', 'Spark'), ('BEAT', 'Beat'), ('CRUZE', 'Cruze'), ('MALIBU', 'Malibu'), ('CAMARO', 'Camaro'), ('CORVETTE', 'Corvette'), ('SILVERADO', 'Silverado / Cheyenne'), ('COLORADO', 'Colorado'), ('S10', 'S10 Max'), ('TRACKER', 'Tracker'), ('TRAX', 'Trax'), ('EQUINOX', 'Equinox'), ('BLAZER', 'Blazer'), ('TAHOE', 'Tahoe'), ('SUBURBAN', 'Suburban'), ('CAPTIVA', 'Captiva'), ('GROOVE', 'Groove'), ('TORNADO', 'Tornado / Van')],
    'FORD': [('FIGO', 'Figo'), ('FIESTA', 'Fiesta'), ('FOCUS', 'Focus'), ('FUSION', 'Fusion'), ('MUSTANG', 'Mustang / Mach-E'), ('MAVERICK', 'Maverick'), ('RANGER', 'Ranger'), ('F150', 'F-150 / Lobo'), ('F250', 'Super Duty'), ('TRANSIT', 'Transit'), ('BRONCO', 'Bronco / Sport'), ('ECOSPORT', 'EcoSport'), ('ESCAPE', 'Escape'), ('EDGE', 'Edge'), ('TERRITORY', 'Territory'), ('EXPLORER', 'Explorer'), ('EXPEDITION', 'Expedition')],
    'DODGE': [('ATTITUDE', 'Attitude'), ('NEON', 'Neon'), ('VISION', 'Vision'), ('CHARGER', 'Charger'), ('CHALLENGER', 'Challenger'), ('JOURNEY', 'Journey'), ('DURANGO', 'Durango')],
    'RAM': [('RAM700', 'Ram 700'), ('RAM1500', 'Ram 1500'), ('RAM2500', 'Ram 2500'), ('RAM4000', 'Ram 4000'), ('PROMASTER', 'ProMaster / Rapid')],
    'JEEP': [('RENEGADE', 'Renegade'), ('COMPASS', 'Compass'), ('CHEROKEE', 'Cherokee'), ('WRANGLER', 'Wrangler'), ('GRAND_CHEROKEE', 'Grand Cherokee'), ('GLADIATOR', 'Gladiator'), ('WAGONEER', 'Wagoneer')],
    'GMC': [('TERRAIN', 'Terrain'), ('ACADIA', 'Acadia'), ('YUKON', 'Yukon'), ('SIERRA', 'Sierra'), ('CANYON', 'Canyon')],
    'CADILLAC': [('CT4', 'CT4'), ('CT5', 'CT5'), ('XT4', 'XT4'), ('XT5', 'XT5'), ('XT6', 'XT6'), ('ESCALADE', 'Escalade')],
    'TESLA': [('MODEL_3', 'Model 3'), ('MODEL_Y', 'Model Y'), ('MODEL_S', 'Model S'), ('MODEL_X', 'Model X'), ('CYBERTRUCK', 'Cybertruck')],

    # ================= EUROPEAS =================
    'VOLKSWAGEN': [('GOL', 'Gol'), ('VENTO', 'Vento'), ('VIRTUS', 'Virtus'), ('JETTA', 'Jetta / GLI'), ('POLO', 'Polo'), ('GOLF', 'Golf / GTI'), ('BORA', 'Bora'), ('BEETLE', 'Beetle'), ('PASSAT', 'Passat'), ('NIVUS', 'Nivus'), ('TCROSS', 'T-Cross'), ('TAOS', 'Taos'), ('TIGUAN', 'Tiguan'), ('TERAMONT', 'Teramont'), ('SAVEIRO', 'Saveiro'), ('AMAROK', 'Amarok'), ('TRANSPORTER', 'Transporter'), ('CADDY', 'Caddy'), ('CRAFTER', 'Crafter')],
    'SEAT': [('IBIZA', 'Ibiza'), ('LEON', 'León'), ('TOLEDO', 'Toledo'), ('ARONA', 'Arona'), ('ATECA', 'Ateca'), ('TARRACO', 'Tarraco')],
    'CUPRA': [('FORMENTOR', 'Formentor'), ('LEON_CUPRA', 'Cupra León'), ('ATECA_CUPRA', 'Cupra Ateca')],
    'BMW': [('SERIE_1', 'Serie 1'), ('SERIE_2', 'Serie 2'), ('SERIE_3', 'Serie 3'), ('SERIE_4', 'Serie 4'), ('SERIE_5', 'Serie 5'), ('X1', 'X1'), ('X2', 'X2'), ('X3', 'X3'), ('X4', 'X4'), ('X5', 'X5'), ('X6', 'X6'), ('X7', 'X7'), ('Z4', 'Z4'), ('M2', 'M2'), ('M3', 'M3 / M4')],
    'MERCEDES_BENZ': [('CLASE_A', 'Clase A'), ('CLASE_C', 'Clase C'), ('CLASE_E', 'Clase E'), ('CLASE_S', 'Clase S'), ('GLA', 'GLA'), ('GLB', 'GLB'), ('GLC', 'GLC'), ('GLE', 'GLE'), ('GLS', 'GLS'), ('CLASE_G', 'Clase G'), ('SPRINTER', 'Sprinter')],
    'AUDI': [('A1', 'A1'), ('A3', 'A3'), ('A4', 'A4'), ('A5', 'A5'), ('A6', 'A6'), ('Q2', 'Q2'), ('Q3', 'Q3'), ('Q5', 'Q5'), ('Q7', 'Q7'), ('Q8', 'Q8'), ('TT', 'TT'), ('R8', 'R8')],
    'RENAULT': [('KWID', 'Kwid'), ('SANDERO', 'Sandero'), ('STEPWAY', 'Stepway'), ('LOGAN', 'Logan'), ('CLIO', 'Clio'), ('DUSTER', 'Duster'), ('CAPTUR', 'Captur'), ('KOLEOS', 'Koleos'), ('OROCH', 'Oroch'), ('KANGOO', 'Kangoo'), ('MASTER', 'Master')],
    'PEUGEOT': [('208', '208'), ('301', '301'), ('2008', '2008'), ('3008', '3008'), ('5008', '5008'), ('PARTNER', 'Partner'), ('MANAGER', 'Manager'), ('RIFTER', 'Rifter'), ('LANDTREK', 'Landtrek')],
    'FIAT': [('MOBI', 'Mobi'), ('UNO', 'Uno'), ('PALIO', 'Palio'), ('ARGO', 'Argo'), ('PULSE', 'Pulse'), ('FASTBACK', 'Fastback'), ('DUCATO', 'Ducato')],
    'VOLVO': [('XC40', 'XC40'), ('XC60', 'XC60'), ('XC90', 'XC90'), ('S60', 'S60'), ('EX30', 'EX30')],
    'PORSCHE': [('911', '911 Carrera / Turbo'), ('718', '718 Boxster / Cayman'), ('TAYCAN', 'Taycan'), ('MACAN', 'Macan'), ('CAYENNE', 'Cayenne'), ('PANAMERA', 'Panamera')],
    'LAND_ROVER': [('DEFENDER', 'Defender'), ('DISCOVERY', 'Discovery / Sport'), ('EVOQUE', 'Range Rover Evoque'), ('VELAR', 'Range Rover Velar'), ('SPORT', 'Range Rover Sport')],
    'FERRARI': [('ROMA', 'Roma'), ('296', '296 GTB'), ('SF90', 'SF90 Stradale'), ('PUROSANGUE', 'Purosangue'), ('F8', 'F8 Tributo')],
    'LAMBORGHINI': [('URUS', 'Urus'), ('HURACAN', 'Huracán'), ('REVUELTO', 'Revuelto'), ('AVENTADOR', 'Aventador')],

    # ================= CHINAS =================
    'MG': [('MG5', 'MG5'), ('MG3', 'MG3'), ('MG_GT', 'MG GT'), ('ZS', 'ZS'), ('HS', 'HS'), ('ONE', 'MG ONE'), ('RX8', 'RX8'), ('MG4', 'MG4 Electric')],
    'CHIREY': [('TIGGO_2', 'Tiggo 2 Pro'), ('TIGGO_4', 'Tiggo 4 Pro'), ('TIGGO_7', 'Tiggo 7 Pro'), ('TIGGO_8', 'Tiggo 8 Pro / Max'), ('ARRIZO_8', 'Arrizo 8')],
    'OMODA': [('C5', 'Omoda C5'), ('O5', 'Omoda O5 / GT')],
    'JAC': [('J7', 'J7'), ('SEI2', 'Sei2'), ('SEI3', 'Sei3'), ('SEI4', 'Sei4 Pro'), ('SEI6', 'Sei6 Pro'), ('FRISON', 'Frison T6/T8/T9'), ('E10X', 'E10X')],
    'BYD': [('DOLPHIN', 'Dolphin / Mini'), ('SEAL', 'Seal'), ('YUAN', 'Yuan Plus'), ('TANG', 'Tang'), ('HAN', 'Han'), ('SONG', 'Song Plus')],
    'GEELY': [('COOLRAY', 'Coolray'), ('GEOMETRY_C', 'Geometry C'), ('STARRAY', 'Starray'), ('OKAVANGO', 'Okavango')],
    'GWM': [('HAVAL_H6', 'Haval H6'), ('JOLION', 'Haval Jolion'), ('ORA_03', 'Ora 03'), ('POER', 'Poer'), ('TANK_300', 'Tank 300')],
    'JETOUR': [('DASHING', 'Dashing'), ('X70', 'X70 / Plus'), ('X90', 'X90 Plus')],

    # ================= COMODÍN =================
    'OTRA': [('OTRO', 'Otro Modelo (Especificar en notas)')],
}

# Flattens the dictionary into a single list of choices for Django's validation engine
TODOS_LOS_MODELOS = [(codigo, nombre) for marca_modelos in CATALOGO_AUTOS.values() for codigo, nombre in marca_modelos]
# ==========================================
# UTILITY FUNCTIONS
# ==========================================
def current_year() -> int:
    """Returns the current Gregorian year for dynamic form validation."""
    return datetime.date.today().year


# ==========================================
# CORE ENTITY FORMS
# ==========================================

class VehiculoForm(forms.ModelForm):
    
    modelo = forms.ChoiceField(
        choices=[('', 'Primero selecciona una marca...')] + TODOS_LOS_MODELOS,
        widget=forms.Select(attrs={'class': 'form-select border-primary shadow-sm'})
    )

    def get_catalogo_json(self) -> str:
        """Serializes the brand/model catalog to JSON for the dynamic dropdown."""
        return json.dumps(CATALOGO_AUTOS, ensure_ascii=False)
    
    class Meta:
        model = Vehiculo
        fields = ['marca', 'modelo', 'anio', 'placas', 'vin', 'kilometraje_actual', 'foto']
        exclude = ['estado'] 
        
        widgets: dict[str, forms.Widget] = {
            'marca': forms.Select(attrs={'class': 'form-select border-primary shadow-sm'}),
            'placas': forms.TextInput(attrs={'class': 'form-control border-primary shadow-sm text-uppercase', 'pattern': r'^[A-Z0-9\-]{6,10}$'}),
            'vin': forms.TextInput(attrs={'class': 'form-control border-primary shadow-sm text-uppercase', 'pattern': r'^[A-HJ-NPR-Z0-9]{17}$', 'maxlength': '17'}),
            'kilometraje_actual': forms.NumberInput(attrs={'class': 'form-control border-primary shadow-sm', 'min': '0', 'step': '0.01'}),
            'foto': forms.FileInput(attrs={'class': 'form-control border-primary shadow-sm'}),
        }
        
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        
        # Obtenemos el año actual
        anio_actual = datetime.date.today().year
        
        # Generamos una lista de años desde el actual hasta el 2000 hacia atrás
        opciones_anios = [(anio, str(anio)) for anio in range(anio_actual, 1999, -1)]
        
        # ¡EL FIX ESTÁ AQUÍ! Pasamos las 'choices' directo adentro del Select
        self.fields['anio'].widget = forms.Select(
            attrs={'class': 'form-select border-primary shadow-sm'},
            choices=[('', 'Selecciona el año...')] + opciones_anios
        )

    def clean(self) -> dict[str, Any]:
        """
        Cross-field backend validation. 
        Ensures the selected Model strictly belongs to the selected Brand.
        """
        cleaned_data = super().clean()
        marca = cleaned_data.get('marca')
        modelo = cleaned_data.get('modelo')

        # Proceed only if both fields are present and valid so far
        if marca and modelo:
            # Extract the valid model codes for the chosen brand
            modelos_validos = [mod[0] for mod in CATALOGO_AUTOS.get(marca, [])]
            
            if modelo not in modelos_validos:
                raise ValidationError({
                    'modelo': f"Inconsistencia de datos: El modelo seleccionado no pertenece a la marca {marca}."
                })
                
        return cleaned_data

    def get_catalogo_json(self) -> str:
        """Serializes the Python dictionary into JSON for the Frontend JavaScript."""
        return json.dumps(CATALOGO_AUTOS)


class ChoferForm(forms.ModelForm):
    """
    Form for managing Driver records.
    Enforces specific patterns for phone numbers and custom HTML5 date constraints.
    """
    vencimiento_licencia = forms.DateField(
        label="Vencimiento de Licencia",
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={'class': 'form-control border-primary shadow-sm', 'type': 'date'}
        )
    )

    foto = forms.ImageField(
        label="Fotografía del Chofer",
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control border-primary shadow-sm'}),
        help_text='Solo usa este campo si deseas reemplazar la foto actual.'   
        )

    class Meta:
        model = Chofer
        fields = ['nombre', 'apellidos', 'telefono', 'tipo_licencia', 'numero_licencia', 'vencimiento_licencia', 'foto']
        
        widgets: dict[str, forms.Widget] = {
            'nombre': forms.TextInput(attrs={'class': 'form-control border-primary shadow-sm', 'placeholder': 'Ej. Juan'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control border-primary shadow-sm', 'placeholder': 'Ej. Pérez'}),
            
            # Strict 10-digit enforcement for phone numbers using raw string (r'')
            'telefono': forms.TextInput(attrs={
                'class': 'form-control border-primary shadow-sm', 
                'placeholder': 'Ej. 4421234567',
                'pattern': r'^\d{10}$',
                'maxlength': '10',
                'title': 'El teléfono debe contener exactamente 10 dígitos numéricos.'
            }),
            'tipo_licencia': forms.Select(attrs={'class': 'form-select border-primary shadow-sm'}),
            'numero_licencia': forms.TextInput(attrs={'class': 'form-control border-primary shadow-sm'}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the form and ensures HTML5 date inputs are correctly populated and restricted."""
        super().__init__(*args, **kwargs)
        
        # 1. Recuperar valor existente si estamos editando
        if self.instance and self.instance.pk and self.instance.vencimiento_licencia:
            self.fields['vencimiento_licencia'].initial = self.instance.vencimiento_licencia.strftime('%Y-%m-%d')
            
        # 2. BLINDAJE DEL CALENDARIO HTML
        hoy = datetime.date.today()
        # Calculamos una fecha máxima razonable (ej. 10 años a futuro)
        fecha_maxima = hoy + datetime.timedelta(days=365 * 10) 
        
        self.fields['vencimiento_licencia'].widget.attrs.update({
            'min': hoy.strftime('%Y-%m-%d'),       # Bloquea fechas pasadas
            'max': fecha_maxima.strftime('%Y-%m-%d') # Bloquea fechas irreales
        })


# ==========================================
# OPERATIONAL FORMS
# ==========================================

class AsignacionForm(forms.ModelForm):
    """
    Form for assigning Vehicles to Drivers.
    Implements business rules via QuerySet filtering to prevent operational conflicts.
    """
    class Meta:
        model = Asignacion
        fields = ['vehiculo', 'chofer']
        
        widgets: dict[str, forms.Widget] = {
            'vehiculo': forms.Select(attrs={'class': 'form-select border-primary shadow-sm'}),
            'chofer': forms.Select(attrs={'class': 'form-select border-primary shadow-sm'}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Filters available vehicles and active, unassigned drivers."""
        super().__init__(*args, **kwargs)
        
        vehiculo_field = cast(forms.ModelChoiceField, self.fields['vehiculo'])
        vehiculo_field.queryset = Vehiculo.objects.filter(estado='DISPONIBLE')
        
        chofer_field = cast(forms.ModelChoiceField, self.fields['chofer'])
        chofer_field.queryset = Chofer.objects.filter(estado='ACTIVO').exclude(asignacion__estado='ACTIVA')


class MantenimientoForm(forms.ModelForm):
    """
    Form for logging vehicle maintenance records.
    """
    fecha_servicio = forms.DateField(
        label="Fecha de Salida al Taller",
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control border-primary shadow-sm', 'type': 'date'})
    )
    
    fecha_regreso = forms.DateField(
        label="Fecha de Regreso",
        required=False,
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control border-primary shadow-sm', 'type': 'date'})
    )

    class Meta:
        model = Mantenimiento
        fields = ['vehiculo', 'tipo', 'fecha_servicio', 'fecha_regreso', 'costo', 'taller', 'descripcion_trabajo', 'estado', 'comprobante']
        
        widgets: dict[str, forms.Widget] = {
            'vehiculo': forms.Select(attrs={'class': 'form-select border-primary shadow-sm'}),
            'tipo': forms.Select(attrs={'class': 'form-select border-primary shadow-sm'}),
            
            'costo': forms.NumberInput(attrs={
                'class': 'form-control border-primary shadow-sm', 
                'placeholder': 'Ej. 1500.50',
                'min': '0',
                'step': '0.01'
            }),
            'taller': forms.TextInput(attrs={'class': 'form-control border-primary shadow-sm', 'placeholder': 'Nombre del taller'}),
            'descripcion_trabajo': forms.Textarea(attrs={'class': 'form-control border-primary shadow-sm', 'rows': 3}),
            'estado': forms.Select(attrs={'class': 'form-select border-primary shadow-sm'}),
            'comprobante': forms.ClearableFileInput(attrs={'class': 'form-control border-primary shadow-sm'}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the form and correctly formats dates for editing."""
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.fecha_servicio:
                self.fields['fecha_servicio'].initial = self.instance.fecha_servicio.strftime('%Y-%m-%d')
            if self.instance.fecha_regreso:
                self.fields['fecha_regreso'].initial = self.instance.fecha_regreso.strftime('%Y-%m-%d')
    
    def clean(self) -> dict[str, Any]:
        """Validación cruzada para evitar fechas de regreso ilógicas."""
        cleaned_data = super().clean()
        fecha_servicio = cleaned_data.get('fecha_servicio')
        fecha_regreso = cleaned_data.get('fecha_regreso')

        # Solo validamos si el usuario llenó ambos campos
        if fecha_servicio and fecha_regreso:
            if fecha_regreso < fecha_servicio:
                # Disparamos el error específicamente en el campo 'fecha_regreso'
                raise ValidationError({
                    'fecha_regreso': "¡Error temporal! La fecha de regreso no puede ser anterior a la fecha de salida al taller."
                })
                
        return cleaned_data


class PolizaSeguroForm(forms.ModelForm):
    """
    Form for registering and updating vehicle insurance policies.
    """
    class Meta:
        model = PolizaSeguro
        fields = '__all__'
        
        widgets: dict[str, forms.Widget] = {
            'vehiculo': forms.Select(attrs={'class': 'form-select border-primary shadow-sm'}),
            'aseguradora': forms.Select(attrs={'class': 'form-select border-primary shadow-sm'}),
            'numero_poliza': forms.TextInput(attrs={'class': 'form-control border-primary shadow-sm', 'placeholder': 'Ej. POL-12345'}),
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control border-primary shadow-sm'}),
        }