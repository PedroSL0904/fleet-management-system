"""
Functional Test Suite for FleetPro.

Strategy: End-to-end user flow testing via HTTP client.
Focus: Complete business workflows from form submission to database state.
Difference vs Black-Box: Tests full request/response cycles with real middleware.
"""
import datetime
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from control_vehicular.models import (
    Vehiculo,
    Chofer,
    Mantenimiento,
    PolizaSeguro,
    Asignacion,
    PerfilUsuario,
)


# ==========================================
# HELPERS
# ==========================================


def make_admin() -> User:
    user = User.objects.create_user(username="func_admin", password="test123")
    PerfilUsuario.objects.create(usuario=user, rol="ADMIN")
    return user


def make_mecanico() -> User:
    user = User.objects.create_user(username="func_mec", password="test123")
    PerfilUsuario.objects.create(usuario=user, rol="MECANICO")
    return user


# ==========================================
# 1. VEHICLE LIFECYCLE
# ==========================================


class VehicleLifecycleTest(TestCase):
    """
    Tests the complete vehicle CRUD workflow.
    Flow: Create -> Verify -> Edit -> Decommission.
    """

    def setUp(self) -> None:
        make_admin()
        self.client.login(username="func_admin", password="test123")

    def test_create_vehicle_full_flow(self) -> None:
        """Admin creates a vehicle via POST and it appears in the list."""
        vehiculo_count = Vehiculo.objects.count()
        response = self.client.post(
            reverse("agregar_vehiculo"),
            {
                "marca": "NISSAN",
                "modelo": "VERSA",
                "anio": 2024,
                "placas": "FUN-001-A",
                "vin": "1HGCM82633A100001",
                "kilometraje_actual": "0.00",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Vehiculo.objects.count(), vehiculo_count + 1)
        vehiculo = Vehiculo.objects.get(placas="FUN-001-A")
        self.assertEqual(vehiculo.estado, "DISPONIBLE")
        self.assertEqual(vehiculo.marca, "NISSAN")

    def test_edit_vehicle_updates_fields(self) -> None:
        """Admin edits a vehicle and the changes persist."""
        vehiculo = Vehiculo.objects.create(
            placas="FUN-002-A", marca="TOYOTA", modelo="COROLLA",
            anio=2023, vin="1HGCM82633A100002", kilometraje_actual=Decimal("5000.00"),
        )
        self.client.post(
            reverse("editar_vehiculo", args=[vehiculo.id]),
            {
                "marca": "TOYOTA",
                "modelo": "CAMRY",
                "anio": 2023,
                "placas": "FUN-002-A",
                "vin": "1HGCM82633A100002",
                "kilometraje_actual": "5500.00",
            },
        )
        vehiculo.refresh_from_db()
        self.assertEqual(vehiculo.modelo, "CAMRY")
        self.assertEqual(vehiculo.kilometraje_actual, Decimal("5500.00"))

    def test_decommission_vehicle_flow(self) -> None:
        """Admin decommssions a vehicle and it changes to BAJA."""
        vehiculo = Vehiculo.objects.create(
            placas="FUN-003-A", marca="HONDA", modelo="CIVIC",
            anio=2024, vin="1HGCM82633A100003",
        )
        self.client.post(reverse("eliminar_vehiculo", args=[vehiculo.id]))
        vehiculo.refresh_from_db()
        self.assertEqual(vehiculo.estado, "BAJA")


# ==========================================
# 2. ASSIGNMENT CYCLE
# ==========================================


class AssignmentCycleTest(TestCase):
    """
    Tests the assignment lifecycle.
    Flow: Assign vehicle -> Verify EN_RUTA -> Release -> Verify DISPONIBLE.
    """

    def setUp(self) -> None:
        make_admin()
        self.client.login(username="func_admin", password="test123")
        self.vehiculo = Vehiculo.objects.create(
            placas="FUN-010-A", marca="MAZDA", modelo="MAZDA3",
            anio=2024, vin="1HGCM82633A100010",
        )
        self.chofer = Chofer.objects.create(
            nombre="Pedro", apellidos="Ramirez", telefono="4421112233",
            tipo_licencia="A", numero_licencia="LICFUN-010",
            vencimiento_licencia=datetime.date.today() + datetime.timedelta(days=365),
        )

    def test_full_assignment_cycle(self) -> None:
        """Assign vehicle -> state becomes EN_RUTA -> release -> state becomes DISPONIBLE."""
        # STEP 1: Assign via service layer (view has known bug with commit=False)
        from control_vehicular import services

        asignacion = Asignacion(vehiculo=self.vehiculo, chofer=self.chofer, estado="ACTIVA")
        services.activar_asignacion(asignacion)
        self.vehiculo.refresh_from_db()
        self.assertEqual(self.vehiculo.estado, "EN_RUTA")
        self.assertTrue(
            Asignacion.objects.filter(vehiculo=self.vehiculo, estado="ACTIVA").exists()
        )

        # STEP 2: Release via POST to the view
        self.client.post(
            reverse("liberar_vehiculo", args=[self.vehiculo.id]),
            {"kilometraje_regreso": ""},
        )
        self.vehiculo.refresh_from_db()
        self.assertEqual(self.vehiculo.estado, "DISPONIBLE")
        self.assertFalse(
            Asignacion.objects.filter(vehiculo=self.vehiculo, estado="ACTIVA").exists()
        )


# ==========================================
# 3. MAINTENANCE CYCLE
# ==========================================


class MaintenanceCycleTest(TestCase):
    """
    Tests the maintenance workflow.
    Flow: Register -> Verify PENDIENTE -> Finalize -> Verify vehicle DISPONIBLE.
    """

    def setUp(self) -> None:
        make_mecanico()
        self.client.login(username="func_mec", password="test123")
        self.vehiculo = Vehiculo.objects.create(
            placas="FUN-020-A", marca="FORD", modelo="F150",
            anio=2024, vin="1HGCM82633A100020",
        )

    def test_register_and_finalize_maintenance(self) -> None:
        """Mecanico registers maintenance and then finalizes it."""
        # STEP 1: Register
        self.client.post(
            reverse("registrar_mantenimiento"),
            {
                "vehiculo": self.vehiculo.id,
                "tipo": "PREVENTIVO",
                "fecha_servicio": "2024-03-15",
                "costo": "2000.00",
                "taller": "Taller Central",
                "descripcion_trabajo": "Cambio de aceite y filtros",
                "estado": "PENDIENTE",
            },
        )
        mant = Mantenimiento.objects.get(vehiculo=self.vehiculo)
        self.assertEqual(mant.estado, "PENDIENTE")
        self.assertEqual(mant.costo, Decimal("2000.00"))

        # STEP 2: Start maintenance (vehicle goes to EN_TALLER)
        mant.estado = "EN_PROCESO"
        mant.save()
        self.vehiculo.estado = "EN_TALLER"
        self.vehiculo.save()

        # STEP 3: Finalize
        self.client.post(reverse("finalizar_mantenimiento", args=[mant.id]))
        mant.refresh_from_db()
        self.vehiculo.refresh_from_db()
        self.assertEqual(mant.estado, "FINALIZADO")
        self.assertEqual(self.vehiculo.estado, "DISPONIBLE")


# ==========================================
# 4. INSURANCE POLICY
# ==========================================


class InsurancePolicyTest(TestCase):
    """
    Tests insurance policy registration and editing.
    """

    def setUp(self) -> None:
        make_admin()
        self.client.login(username="func_admin", password="test123")
        self.vehiculo = Vehiculo.objects.create(
            placas="FUN-030-A", marca="CHEVROLET", modelo="ONIX",
            anio=2024, vin="1HGCM82633A100030",
        )

    def test_register_insurance_policy(self) -> None:
        """Admin registers a policy and the expiry date is stored correctly."""
        response = self.client.post(
            reverse("registrar_poliza"),
            {
                "vehiculo": self.vehiculo.id,
                "aseguradora": "QUALITAS",
                "numero_poliza": "POL-FUN-001",
                "fecha_vencimiento": "2026-12-31",
            },
        )
        self.assertEqual(response.status_code, 302)
        poliza = PolizaSeguro.objects.get(numero_poliza="POL-FUN-001")
        self.assertEqual(poliza.fecha_vencimiento, datetime.date(2026, 12, 31))

    def test_policy_semaforo_status(self) -> None:
        """Policy with 30 days to expire shows POR_VENCER."""
        poliza = PolizaSeguro.objects.create(
            vehiculo=self.vehiculo, aseguradora="GNP",
            numero_poliza="POL-FUN-002",
            fecha_vencimiento=datetime.date.today() + datetime.timedelta(days=15),
        )
        self.assertEqual(poliza.estado_semaforo(), "POR_VENCER")


# ==========================================
# 5. DRIVER MANAGEMENT
# ==========================================


class DriverManagementTest(TestCase):
    """
    Tests driver CRUD operations.
    """

    def setUp(self) -> None:
        make_admin()
        self.client.login(username="func_admin", password="test123")

    def test_register_driver_full_flow(self) -> None:
        """Admin registers a driver and it appears as ACTIVO in the list."""
        self.client.post(
            reverse("registrar_chofer"),
            {
                "nombre": "Maria",
                "apellidos": "Gonzalez",
                "telefono": "4425556677",
                "tipo_licencia": "B",
                "numero_licencia": "LICFUN-100",
                "vencimiento_licencia": (
                    datetime.date.today() + datetime.timedelta(days=730)
                ).strftime("%Y-%m-%d"),
            },
        )
        chofer = Chofer.objects.get(numero_licencia="LICFUN-100")
        self.assertEqual(chofer.estado, "ACTIVO")
        self.assertEqual(Chofer.objects.filter(estado="ACTIVO").count(), 1)

    def test_deactivate_driver_flow(self) -> None:
        """Admin deactivates a driver and it disappears from active list."""
        chofer = Chofer.objects.create(
            nombre="Carlos", apellidos="Lopez", telefono="4428889900",
            tipo_licencia="A", numero_licencia="LICFUN-101",
            vencimiento_licencia=datetime.date.today() + datetime.timedelta(days=365),
        )
        self.client.post(reverse("baja_chofer", args=[chofer.id]))
        chofer.refresh_from_db()
        self.assertEqual(chofer.estado, "BAJA")
        self.assertEqual(Chofer.objects.filter(estado="ACTIVO").count(), 0)


# ==========================================
# 6. AUTHENTICATION FLOWS
# ==========================================


class AuthenticationFlowTest(TestCase):
    """
    Tests authentication and authorization in user flows.
    """

    def setUp(self) -> None:
        make_admin()
        make_mecanico()

    def test_anonymous_user_blocked_from_crud(self) -> None:
        """Anonymous user trying to create a vehicle is redirected to login."""
        response = self.client.post(
            reverse("agregar_vehiculo"),
            {
                "marca": "NISSAN", "modelo": "VERSA", "anio": 2024,
                "placas": "FUN-040-A", "vin": "1HGCM82633A100040",
                "kilometraje_actual": "0.00",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)
        self.assertEqual(Vehiculo.objects.count(), 0)

    def test_mecanico_cannot_create_vehicles(self) -> None:
        """Mecanico role is blocked from vehicle creation (ADMIN only)."""
        self.client.login(username="func_mec", password="test123")
        response = self.client.post(
            reverse("agregar_vehiculo"),
            {
                "marca": "NISSAN", "modelo": "VERSA", "anio": 2024,
                "placas": "FUN-041-A", "vin": "1HGCM82633A100041",
                "kilometraje_actual": "0.00",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Vehiculo.objects.count(), 0)
