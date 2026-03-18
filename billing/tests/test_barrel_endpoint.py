from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from billing.models import Barrel, Invoice, Provider


User = get_user_model()


class BarrelEndpointTests(APITestCase):
    @staticmethod
    def create_provider(name: str, tax_id: str) -> Provider:
        return Provider.objects.create(
            name=name,
            address=f"{name} address",
            tax_id=tax_id,
        )

    @staticmethod
    def create_user(username: str, provider: Provider) -> User:
        return User.objects.create_user(
            username=username,
            password="strongpass123",
            provider=provider,
        )

    @staticmethod
    def create_barrel(provider: Provider, number: str, liters: int = 100) -> Barrel:
        return Barrel.objects.create(
            provider=provider,
            number=number,
            oil_type="olive",
            liters=liters,
        )

    @staticmethod
    def create_invoice(provider: Provider, invoice_no: str) -> Invoice:
        return Invoice.objects.create(
            provider=provider,
            invoice_no=invoice_no,
            issued_on=date(2026, 3, 18),
        )

    def test_create_barrel_uses_logged_in_user_provider(self):
        provider_a = self.create_provider("Acme Oils", "TAX-12345")
        provider_b = self.create_provider("Beta Oils", "TAX-67890")
        user = self.create_user("provider_user", provider_a)
        self.client.force_authenticate(user=user)

        payload = {
            "provider": provider_b.id,
            "number": "BAR-001",
            "oil_type": "olive",
            "liters": 100,
        }

        response = self.client.post(reverse("barrel-list"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_barrel = Barrel.objects.get(id=response.data["id"])
        self.assertEqual(response.data["provider"], provider_a.id)
        self.assertEqual(created_barrel.provider_id, provider_a.id)
        self.assertNotEqual(created_barrel.provider_id, provider_b.id)

    def test_delete_barrel_returns_400_when_barrel_has_invoice_lines(self):
        provider = self.create_provider("Acme Oils", "TAX-12345")
        user = self.create_user("provider_user_delete", provider)
        barrel = self.create_barrel(provider, "BAR-001")
        invoice = self.create_invoice(provider, "INV-001")
        invoice.add_line_for_barrel(
            barrel=barrel,
            liters=barrel.liters,
            unit_price_per_liter=Decimal("1.25"),
            description="Invoice line",
        )
        self.client.force_authenticate(user=user)

        response = self.client.delete(reverse("barrel-detail", args=[barrel.id]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)
        self.assertTrue(Barrel.objects.filter(id=barrel.id).exists())
