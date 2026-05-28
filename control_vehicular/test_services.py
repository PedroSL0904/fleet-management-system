import datetime
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User

from control_vehicular.models import Vehiculo, Chofer, Asignacion, Mantenimiento
from control_vehicular import services


class DarBajaVehiculoTest(TestCase):
    def setUp(self) -> None:
        self.vehiculo = Vehiculo.objects.create(
            placas="TST-001-A", marca="NISSAN", modelo="Versa",
            anio=2024, vin="1HTST1234567890AB",
        )

    def test_cambia_estado_a_baja(self) -> None:
        services.dar_baja_vehiculo(self.vehiculo)
        self.vehiculo.refresh_from_db()
        self.assertEqual(self.vehiculo.estado, 'BAJA')


class ReactivarVehiculoTest(TestCase):
    def setUp(self) -> None:
        self.vehiculo = Vehiculo.objects.create(
            placas="TST-002-A", marca="TOYOTA", modelo="Corolla",
            anio=2024, vin="2HTST1234567890AB", estado='BAJA',
        )
        self.chofer = Chofer.objects.create(
            nombre="Juan", apellidos="Perez", telefono="4421234567",
            numero_licencia="LIC001",
            vencimiento_licencia=datetime.date.today() + datetime.timedelta(days=365),
        )

    def test_reactivar_sin_dependencias(self) -> None:
        services.reactivar_vehiculo(self.vehiculo)
        self.vehiculo.refresh_from_db()
        self.assertEqual(self.vehiculo.estado, 'DISPONIBLE')

    def test_reactivar_con_mantenimiento_en_proceso(self) -> None:
        Mantenimiento.objects.create(
            vehiculo=self.vehiculo, tipo='PREVENTIVO',
            fecha_servicio=datetime.date.today(), costo=Decimal('1000.00'),
            taller="Taller X", descripcion_trabajo="Afinacion",
            estado='EN_PROCESO',
        )
        services.reactivar_vehiculo(self.vehiculo)
        self.vehiculo.refresh_from_db()
        self.assertEqual(self.vehiculo.estado, 'EN_TALLER')

    def test_reactivar_con_asignacion_activa(self) -> None:
        Asignacion.objects.create(
            vehiculo=self.vehiculo, chofer=self.chofer, estado='ACTIVA',
        )
        services.reactivar_vehiculo(self.vehiculo)
        self.vehiculo.refresh_from_db()
        self.assertEqual(self.vehiculo.estado, 'EN_RUTA')


class ActivarAsignacionTest(TestCase):
    def setUp(self) -> None:
        self.vehiculo = Vehiculo.objects.create(
            placas="TST-003-A", marca="HONDA", modelo="Civic",
            anio=2024, vin="3HTST1234567890AB",
        )
        self.chofer = Chofer.objects.create(
            nombre="Maria", apellidos="Lopez", telefono="4429876543",
            numero_licencia="LIC002",
            vencimiento_licencia=datetime.date.today() + datetime.timedelta(days=365),
        )

    def test_asignacion_cambia_estado_vehiculo_a_en_ruta(self) -> None:
        asignacion = Asignacion(
            vehiculo=self.vehiculo, chofer=self.chofer, estado='ACTIVA',
        )
        services.activar_asignacion(asignacion)
        self.vehiculo.refresh_from_db()
        self.assertEqual(self.vehiculo.estado, 'EN_RUTA')
        self.assertEqual(asignacion.estado, 'ACTIVA')


class LiberarVehiculoTest(TestCase):
    def setUp(self) -> None:
        self.vehiculo = Vehiculo.objects.create(
            placas="TST-004-A", marca="MAZDA", modelo="Mazda 3",
            anio=2024, vin="4HTST1234567890AB", estado='EN_RUTA',
            kilometraje_actual=Decimal('5000.00'),
        )
        self.chofer = Chofer.objects.create(
            nombre="Carlos", apellidos="Ruiz", telefono="4425551234",
            numero_licencia="LIC003",
            vencimiento_licencia=datetime.date.today() + datetime.timedelta(days=365),
        )
        self.asignacion = Asignacion.objects.create(
            vehiculo=self.vehiculo, chofer=self.chofer, estado='ACTIVA',
        )

    def test_liberar_actualiza_km_y_finaliza_asignacion(self) -> None:
        services.liberar_vehiculo(self.vehiculo, '6500.50')
        self.vehiculo.refresh_from_db()
        self.asignacion.refresh_from_db()
        self.assertEqual(self.vehiculo.estado, 'DISPONIBLE')
        self.assertEqual(self.vehiculo.kilometraje_actual, Decimal('6500.50'))
        self.assertEqual(self.asignacion.estado, 'FINALIZADA')
        self.assertIsNotNone(self.asignacion.fecha_devolucion)

    def test_liberar_sin_km(self) -> None:
        services.liberar_vehiculo(self.vehiculo)
        self.vehiculo.refresh_from_db()
        self.assertEqual(self.vehiculo.estado, 'DISPONIBLE')
        self.assertEqual(self.vehiculo.kilometraje_actual, Decimal('5000.00'))

    def test_liberar_con_km_invalido(self) -> None:
        services.liberar_vehiculo(self.vehiculo, 'abc')
        self.vehiculo.refresh_from_db()
        self.assertEqual(self.vehiculo.estado, 'DISPONIBLE')
        self.assertEqual(self.vehiculo.kilometraje_actual, Decimal('5000.00'))


class FinalizarMantenimientoTest(TestCase):
    def setUp(self) -> None:
        self.vehiculo = Vehiculo.objects.create(
            placas="TST-005-A", marca="FORD", modelo="Figo",
            anio=2024, vin="5HTST1234567890AB", estado='EN_TALLER',
        )
        self.mantenimiento = Mantenimiento.objects.create(
            vehiculo=self.vehiculo, tipo='CORRECTIVO',
            fecha_servicio=datetime.date.today(), costo=Decimal('3000.00'),
            taller="Taller Y", descripcion_trabajo="Cambio de frenos",
            estado='EN_PROCESO',
        )

    def test_finalizar_cambia_vehiculo_a_disponible(self) -> None:
        services.finalizar_mantenimiento(self.mantenimiento)
        self.mantenimiento.refresh_from_db()
        self.vehiculo.refresh_from_db()
        self.assertEqual(self.mantenimiento.estado, 'FINALIZADO')
        self.assertEqual(self.vehiculo.estado, 'DISPONIBLE')


class DarBajaYReactivarChoferTest(TestCase):
    def setUp(self) -> None:
        self.chofer = Chofer.objects.create(
            nombre="Ana", apellidos="Garcia", telefono="4427778899",
            numero_licencia="LIC004",
            vencimiento_licencia=datetime.date.today() + datetime.timedelta(days=365),
        )

    def test_dar_baja_chofer(self) -> None:
        services.dar_baja_chofer(self.chofer)
        self.chofer.refresh_from_db()
        self.assertEqual(self.chofer.estado, 'BAJA')

    def test_reactivar_chofer(self) -> None:
        self.chofer.estado = 'BAJA'
        self.chofer.save()
        services.reactivar_chofer(self.chofer)
        self.chofer.refresh_from_db()
        self.assertEqual(self.chofer.estado, 'ACTIVO')
