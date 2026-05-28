from django.test import TestCase
from .models import Vehiculo

# ==========================================
# UNIT TESTS: VEHICLE DIRECTORY
# ==========================================


class VehiculoModelTest(TestCase):
    """
    Test suite for the Vehiculo core entity.
    Validates model creation, default values, and string representations
    using an isolated test database.
    """

    def setUp(self) -> None:
        """
        Initializes the test environment before each test method runs.
        Creates a dummy vehicle instance in the temporary test database.
        """
        self.vehiculo = Vehiculo.objects.create(
            placas="TST-123-A",
            marca="Toyota",
            modelo="Corolla",
            anio=2024,
            vin="1HTST1234567890AB",
            # Note: 'estado' and 'kilometraje_actual' are omitted
            # to test if Django applies the default values properly.
        )

    def test_vehiculo_creation_and_defaults(self) -> None:
        """
        Asserts that a vehicle is created successfully and
        that default values (like 'DISPONIBLE') are applied correctly by the ORM.
        """
        # Retrieve the newly created vehicle from the test database
        vehiculo_db = Vehiculo.objects.get(placas="TST-123-A")

        # Validate data integrity
        self.assertEqual(vehiculo_db.marca, "Toyota")

        # Validate default business logic values
        self.assertEqual(
            vehiculo_db.estado, "DISPONIBLE", "Initial state must be 'DISPONIBLE'"
        )
        self.assertEqual(float(vehiculo_db.kilometraje_actual), 0.00)

    def test_vehiculo_string_representation(self) -> None:
        """
        Asserts that the __str__ magic method returns the correctly formatted string.
        """
        expected_string = "Toyota Corolla (TST-123-A)"
        self.assertEqual(str(self.vehiculo), expected_string)
