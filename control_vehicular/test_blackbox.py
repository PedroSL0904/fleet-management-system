"""
Black-Box Test Suite for FleetPro.

Strategy: Tests input/output behavior without inspecting internal implementation.
Focus: Form validation boundaries, HTTP responses, and observable system behavior.
Categories: Valid input, invalid input, boundary values, and edge cases.
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
from control_vehicular.forms import (
    VehiculoForm,
    ChoferForm,
    MantenimientoForm,
    AsignacionForm,
    PolizaSeguroForm,
)


# ==========================================
# HELPER FIXTURES
# ==========================================


def create_admin_user() -> User:
    """Creates a test admin user with profile."""
    user = User.objects.create_user(username="admin_bb", password="test123")
    PerfilUsuario.objects.create(usuario=user, rol="ADMIN")
    return user


def create_driver(estado: str = "ACTIVO") -> Chofer:
    """Creates a test driver with configurable state."""
    return Chofer.objects.create(
        nombre="Test",
        apellidos="Driver",
        telefono="4421234567",
        tipo_licencia="A",
        numero_licencia=f"LICBB{estado}",
        vencimiento_licencia=datetime.date.today() + datetime.timedelta(days=365),
        estado=estado,
    )


def create_vehicle(estado: str = "DISPONIBLE") -> Vehiculo:
    """Creates a test vehicle with configurable state."""
    return Vehiculo.objects.create(
        placas=f"BB-{estado[:3]}-01",
        marca="NISSAN",
        modelo="VERSA",
        anio=2024,
        vin=f"1HGCM82633A{estado[:6].ljust(6, '0')}",
        estado=estado,
    )


# ==========================================
# 1. VEHICULO FORM BLACK-BOX TESTS
# ==========================================


class VehiculoFormBlackBoxTest(TestCase):
    """
    Black-box tests for VehiculoForm.
    Tests observable validation behavior without inspecting model internals.
    """

    def test_valid_input_creates_vehicle(self) -> None:
        """Valid data passes validation."""
        form_data = {
            "marca": "NISSAN",
            "modelo": "VERSA",
            "anio": 2024,
            "placas": "BB-001-A",
            "vin": "1HGCM82633A123456",
            "kilometraje_actual": "1000.00",
        }
        form = VehiculoForm(data=form_data)
        self.assertTrue(
            form.is_valid(), f"Form should be valid. Errors: {form.errors}"
        )

    def test_invalid_placas_format_rejected(self) -> None:
        """Lowercase placas should be rejected by pattern validator."""
        form_data = {
            "marca": "NISSAN",
            "modelo": "VERSA",
            "anio": 2024,
            "placas": "bb-001-a",
            "vin": "1HGCM82633A123456",
            "kilometraje_actual": "0.00",
        }
        form = VehiculoForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("placas", form.errors)

    def test_invalid_vin_with_forbidden_letters_rejected(self) -> None:
        """VIN containing I, O, or Q should be rejected (ISO 3779 standard)."""
        form_data = {
            "marca": "TOYOTA",
            "modelo": "COROLLA",
            "anio": 2024,
            "placas": "BB-002-A",
            "vin": "1HGCM82633A12345I",
            "kilometraje_actual": "0.00",
        }
        form = VehiculoForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("vin", form.errors)

    def test_model_not_belonging_to_brand_rejected(self) -> None:
        """Cross-field validation: COROLLA is not a Nissan model."""
        form_data = {
            "marca": "NISSAN",
            "modelo": "COROLLA",
            "anio": 2024,
            "placas": "BB-003-A",
            "vin": "1HGCM82633A123456",
            "kilometraje_actual": "0.00",
        }
        form = VehiculoForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("modelo", form.errors)

    def test_negative_mileage_rejected(self) -> None:
        """Negative mileage should be rejected by MinValueValidator."""
        form_data = {
            "marca": "NISSAN",
            "modelo": "VERSA",
            "anio": 2024,
            "placas": "BB-004-A",
            "vin": "1HGCM82633A123456",
            "kilometraje_actual": "-100.00",
        }
        form = VehiculoForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("kilometraje_actual", form.errors)

    def test_future_year_above_maximum_rejected(self) -> None:
        """Year beyond current+1 should be rejected."""
        next_year = datetime.date.today().year + 5
        form_data = {
            "marca": "NISSAN",
            "modelo": "VERSA",
            "anio": next_year,
            "placas": "BB-005-A",
            "vin": "1HGCM82633A123456",
            "kilometraje_actual": "0.00",
        }
        form = VehiculoForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("anio", form.errors)


# ==========================================
# 2. CHOFER FORM BLACK-BOX TESTS
# ==========================================


class ChoferFormBlackBoxTest(TestCase):
    """
    Black-box tests for ChoferForm.
    Focus: Phone pattern, license expiration date constraints.
    """

    def test_valid_driver_data_passes(self) -> None:
        """Valid driver data passes validation."""
        form_data = {
            "nombre": "Juan",
            "apellidos": "Pérez",
            "telefono": "4421234567",
            "tipo_licencia": "A",
            "numero_licencia": "LICBB-100",
            "vencimiento_licencia": (
                datetime.date.today() + datetime.timedelta(days=365)
            ).strftime("%Y-%m-%d"),
        }
        form = ChoferForm(data=form_data)
        self.assertTrue(
            form.is_valid(), f"Form should be valid. Errors: {form.errors}"
        )

    def test_phone_with_letters_rejected(self) -> None:
        """Phone with non-numeric characters should be rejected."""
        form_data = {
            "nombre": "Juan",
            "apellidos": "Pérez",
            "telefono": "442-123-4567",
            "tipo_licencia": "A",
            "numero_licencia": "LICBB-101",
            "vencimiento_licencia": (
                datetime.date.today() + datetime.timedelta(days=365)
            ).strftime("%Y-%m-%d"),
        }
        form = ChoferForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("telefono", form.errors)

    def test_phone_wrong_length_rejected(self) -> None:
        """Phone with fewer than 10 digits should be rejected."""
        form_data = {
            "nombre": "Juan",
            "apellidos": "Pérez",
            "telefono": "442123",
            "tipo_licencia": "A",
            "numero_licencia": "LICBB-102",
            "vencimiento_licencia": (
                datetime.date.today() + datetime.timedelta(days=365)
            ).strftime("%Y-%m-%d"),
        }
        form = ChoferForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("telefono", form.errors)

    def test_expired_license_rejected(self) -> None:
        """License expired yesterday should be rejected."""
        form_data = {
            "nombre": "Juan",
            "apellidos": "Pérez",
            "telefono": "4421234567",
            "tipo_licencia": "A",
            "numero_licencia": "LICBB-103",
            "vencimiento_licencia": (
                datetime.date.today() - datetime.timedelta(days=1)
            ).strftime("%Y-%m-%d"),
        }
        form = ChoferForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("vencimiento_licencia", form.errors)


# ==========================================
# 3. MANTENIMIENTO FORM BLACK-BOX TESTS
# ==========================================


class MantenimientoFormBlackBoxTest(TestCase):
    """
    Black-box tests for MantenimientoForm.
    Focus: Date cross-validation (return >= service).
    """

    def setUp(self) -> None:
        self.vehiculo = create_vehicle()

    def test_valid_dates_pass(self) -> None:
        """Return date after service date passes."""
        form_data = {
            "vehiculo": self.vehiculo.id,
            "tipo": "PREVENTIVO",
            "fecha_servicio": "2024-01-15",
            "fecha_regreso": "2024-01-20",
            "costo": "1500.50",
            "taller": "Taller Test",
            "descripcion_trabajo": "Cambio de aceite",
            "estado": "PENDIENTE",
        }
        form = MantenimientoForm(data=form_data)
        self.assertTrue(
            form.is_valid(), f"Form should be valid. Errors: {form.errors}"
        )

    def test_return_before_service_rejected(self) -> None:
        """Return date before service date should be rejected."""
        form_data = {
            "vehiculo": self.vehiculo.id,
            "tipo": "PREVENTIVO",
            "fecha_servicio": "2024-01-20",
            "fecha_regreso": "2024-01-15",
            "costo": "1500.50",
            "taller": "Taller Test",
            "descripcion_trabajo": "Cambio de aceite",
            "estado": "PENDIENTE",
        }
        form = MantenimientoForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("fecha_regreso", form.errors)

    def test_negative_cost_rejected(self) -> None:
        """Negative cost should be rejected."""
        form_data = {
            "vehiculo": self.vehiculo.id,
            "tipo": "PREVENTIVO",
            "fecha_servicio": "2024-01-15",
            "costo": "-100.00",
            "taller": "Taller Test",
            "descripcion_trabajo": "Cambio de aceite",
            "estado": "PENDIENTE",
        }
        form = MantenimientoForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("costo", form.errors)


# ==========================================
# 4. ASIGNACION FORM BLACK-BOX TESTS
# ==========================================


class AsignacionFormBlackBoxTest(TestCase):
    """
    Black-box tests for AsignacionForm.
    Focus: Queryset filtering (only available vehicles and unassigned drivers).
    """

    def test_only_disponible_vehicles_in_queryset(self) -> None:
        """Vehicle queryset should exclude non-DISPONIBLE vehicles."""
        disponible = create_vehicle(estado="DISPONIBLE")
        en_ruta = create_vehicle(estado="EN_RUTA")
        form = AsignacionForm()
        vehiculo_ids = list(form.fields["vehiculo"].queryset.values_list("id", flat=True))
        self.assertIn(disponible.id, vehiculo_ids)
        self.assertNotIn(en_ruta.id, vehiculo_ids)

    def test_only_active_unassigned_drivers_in_queryset(self) -> None:
        """Driver queryset should exclude drivers with active assignments."""
        driver_libre = create_driver(estado="ACTIVO")
        driver_asignado = Chofer.objects.create(
            nombre="Asignado",
            apellidos="Test",
            telefono="4429876543",
            tipo_licencia="B",
            numero_licencia="LICBB-ASSIGN",
            vencimiento_licencia=datetime.date.today() + datetime.timedelta(days=365),
            estado="ACTIVO",
        )
        vehiculo = create_vehicle(estado="EN_RUTA")
        Asignacion.objects.create(
            vehiculo=vehiculo, chofer=driver_asignado, estado="ACTIVA"
        )
        form = AsignacionForm()
        chofer_ids = list(form.fields["chofer"].queryset.values_list("id", flat=True))
        self.assertIn(driver_libre.id, chofer_ids)
        self.assertNotIn(driver_asignado.id, chofer_ids)


# ==========================================
# 5. HTTP RESPONSE BLACK-BOX TESTS
# ==========================================


class HTTPResponseBlackBoxTest(TestCase):
    """
    Black-box tests for HTTP responses.
    Focus: Status codes, redirects, and template rendering.
    """

    def setUp(self) -> None:
        self.admin = create_admin_user()
        self.client.login(username="admin_bb", password="test123")

    def test_dashboard_returns_200(self) -> None:
        """Authenticated user gets 200 on dashboard."""
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_renders_expected_template(self) -> None:
        """Dashboard should render dashboard.html."""
        response = self.client.get(reverse("dashboard"))
        self.assertTemplateUsed(response, "control_vehicular/dashboard.html")

    def test_unauthenticated_dashboard_redirects(self) -> None:
        """Anonymous user gets redirected to login."""
        self.client.logout()
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_post_to_delete_vehicle_redirects_to_flotilla(self) -> None:
        """POST to delete vehicle should redirect to flotilla."""
        vehiculo = create_vehicle()
        response = self.client.post(reverse("eliminar_vehiculo", args=[vehiculo.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn("flotilla", response.url)

    def test_get_to_delete_vehicle_does_not_decommission(self) -> None:
        """GET request should NOT trigger decommission (security)."""
        vehiculo = create_vehicle()
        self.client.get(reverse("eliminar_vehiculo", args=[vehiculo.id]))
        vehiculo.refresh_from_db()
        self.assertEqual(vehiculo.estado, "DISPONIBLE")


# ==========================================
# 6. CONTEXT PROCESSOR BLACK-BOX TESTS
# ==========================================


class ContextProcessorBlackBoxTest(TestCase):
    """
    Black-box tests for alertas_globales context processor.
    Focus: Observable context variables per user state.
    """

    def test_anonymous_user_gets_empty_context(self) -> None:
        """Unauthenticated request should return empty dict."""
        from django.test import RequestFactory
        from django.contrib.auth.models import AnonymousUser
        from control_vehicular.context_processors import alertas_globales

        factory = RequestFactory()
        request = factory.get("/")
        request.user = AnonymousUser()
        context = alertas_globales(request)
        self.assertEqual(context, {})

    def test_authenticated_user_gets_alerts_keys(self) -> None:
        """Authenticated request should include alerts keys."""
        from django.test import RequestFactory
        from control_vehicular.context_processors import alertas_globales

        factory = RequestFactory()
        request = factory.get("/")
        request.user = self._make_user()
        context = alertas_globales(request)
        self.assertIn("alertas_mantenimientos_global", context)
        self.assertIn("alertas_polizas_global", context)
        self.assertIn("total_alertas", context)

    def _make_user(self) -> User:
        user = User.objects.create_user(username="ctx_user", password="test123")
        return user


# ==========================================
# 7. EDGE CASES & BOUNDARY VALUES
# ==========================================


class EdgeCaseBlackBoxTest(TestCase):
    """
    Black-box boundary value tests.
    Focus: Limit values, empty inputs, special characters.
    """

    def test_empty_form_submission_rejected(self) -> None:
        """Empty form data should fail validation."""
        form = VehiculoForm(data={})
        self.assertFalse(form.is_valid())
        self.assertGreater(len(form.errors), 0)

    def test_special_characters_in_placas_rejected(self) -> None:
        """Placas with special characters outside the pattern should be rejected."""
        form_data = {
            "marca": "NISSAN",
            "modelo": "VERSA",
            "anio": 2024,
            "placas": "BB@001#A",
            "vin": "1HGCM82633A123456",
            "kilometraje_actual": "0.00",
        }
        form = VehiculoForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("placas", form.errors)

    def test_vin_too_short_rejected(self) -> None:
        """VIN with fewer than 17 characters should be rejected."""
        form_data = {
            "marca": "NISSAN",
            "modelo": "VERSA",
            "anio": 2024,
            "placas": "BB-010-A",
            "vin": "1HGCM82633A12345",
            "kilometraje_actual": "0.00",
        }
        form = VehiculoForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("vin", form.errors)

    def test_placas_minimum_length_boundary(self) -> None:
        """Placas with exactly 6 characters (minimum) should be accepted."""
        form_data = {
            "marca": "NISSAN",
            "modelo": "VERSA",
            "anio": 2024,
            "placas": "BB-001",
            "vin": "1HGCM82633A123456",
            "kilometraje_actual": "0.00",
        }
        form = VehiculoForm(data=form_data)
        self.assertTrue(
            form.is_valid(), f"6-char placas should pass. Errors: {form.errors}"
        )

    def test_zero_mileage_accepted(self) -> None:
        """Zero mileage (brand new vehicle) should be valid."""
        form_data = {
            "marca": "NISSAN",
            "modelo": "VERSA",
            "anio": 2024,
            "placas": "BB-011-A",
            "vin": "1HGCM82633A123456",
            "kilometraje_actual": "0.00",
        }
        form = VehiculoForm(data=form_data)
        self.assertTrue(
            form.is_valid(), f"Zero mileage should pass. Errors: {form.errors}"
        )
