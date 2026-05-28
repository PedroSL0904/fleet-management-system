from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from control_vehicular.models import PerfilUsuario, Vehiculo, Chofer
import datetime


class RBACTestCase(TestCase):
    def setUp(self) -> None:
        self.client = Client()

        self.admin_user = User.objects.create_user(
            username="admin", password="testpass123"
        )
        PerfilUsuario.objects.create(usuario=self.admin_user, rol="ADMIN")

        self.mecanico_user = User.objects.create_user(
            username="mecanico", password="testpass123"
        )
        PerfilUsuario.objects.create(usuario=self.mecanico_user, rol="MECANICO")

        self.chofer_user = User.objects.create_user(
            username="chofer", password="testpass123"
        )
        PerfilUsuario.objects.create(usuario=self.chofer_user, rol="CHOFER")

        self.user_sin_perfil = User.objects.create_user(
            username="sinperfil", password="testpass123"
        )

        self.vehiculo = Vehiculo.objects.create(
            placas="TST-100-A",
            marca="NISSAN",
            modelo="Versa",
            anio=2024,
            vin="9HTST1234567890AB",
        )
        self.chofer = Chofer.objects.create(
            nombre="Test",
            apellidos="Driver",
            telefono="4420001122",
            numero_licencia="LICRBAC",
            vencimiento_licencia=datetime.date.today() + datetime.timedelta(days=365),
        )


class AdminOnlyViewsTest(RBACTestCase):
    def test_admin_puede_acceder_agregar_vehiculo(self) -> None:
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("agregar_vehiculo"))
        self.assertEqual(response.status_code, 200)

    def test_mecanico_no_puede_acceder_agregar_vehiculo(self) -> None:
        self.client.login(username="mecanico", password="testpass123")
        response = self.client.get(reverse("agregar_vehiculo"))
        self.assertEqual(response.status_code, 403)

    def test_chofer_no_puede_acceder_agregar_vehiculo(self) -> None:
        self.client.login(username="chofer", password="testpass123")
        response = self.client.get(reverse("agregar_vehiculo"))
        self.assertEqual(response.status_code, 403)

    def test_sin_perfil_no_puede_acceder_agregar_vehiculo(self) -> None:
        self.client.login(username="sinperfil", password="testpass123")
        response = self.client.get(reverse("agregar_vehiculo"))
        self.assertEqual(response.status_code, 403)

    def test_chofer_no_puede_registrar_chofer(self) -> None:
        self.client.login(username="chofer", password="testpass123")
        response = self.client.get(reverse("registrar_chofer"))
        self.assertEqual(response.status_code, 403)

    def test_admin_puede_registrar_chofer(self) -> None:
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("registrar_chofer"))
        self.assertEqual(response.status_code, 200)

    def test_chofer_no_puede_registrar_poliza(self) -> None:
        self.client.login(username="chofer", password="testpass123")
        response = self.client.get(reverse("registrar_poliza"))
        self.assertEqual(response.status_code, 403)

    def test_mecanico_no_puede_registrar_poliza(self) -> None:
        self.client.login(username="mecanico", password="testpass123")
        response = self.client.get(reverse("registrar_poliza"))
        self.assertEqual(response.status_code, 403)


class StaffViewsTest(RBACTestCase):
    def test_admin_puede_registrar_mantenimiento(self) -> None:
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("registrar_mantenimiento"))
        self.assertEqual(response.status_code, 200)

    def test_mecanico_puede_registrar_mantenimiento(self) -> None:
        self.client.login(username="mecanico", password="testpass123")
        response = self.client.get(reverse("registrar_mantenimiento"))
        self.assertEqual(response.status_code, 200)

    def test_chofer_no_puede_registrar_mantenimiento(self) -> None:
        self.client.login(username="chofer", password="testpass123")
        response = self.client.get(reverse("registrar_mantenimiento"))
        self.assertEqual(response.status_code, 403)


class PublicViewsTest(RBACTestCase):
    def test_dashboard_requiere_login(self) -> None:
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_todos_los_roles_pueden_ver_dashboard(self) -> None:
        for username in ["admin", "mecanico", "chofer"]:
            self.client.login(username=username, password="testpass123")
            response = self.client.get(reverse("dashboard"))
            self.assertEqual(response.status_code, 200)

    def test_todos_los_roles_pueden_ver_flotilla(self) -> None:
        for username in ["admin", "mecanico", "chofer"]:
            self.client.login(username=username, password="testpass123")
            response = self.client.get(reverse("flotilla"))
            self.assertEqual(response.status_code, 200)

    def test_todos_los_roles_pueden_ver_historial(self) -> None:
        for username in ["admin", "mecanico", "chofer"]:
            self.client.login(username=username, password="testpass123")
            response = self.client.get(reverse("historial_mantenimientos"))
            self.assertEqual(response.status_code, 200)
