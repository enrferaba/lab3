from datetime import date

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from billing.models import Barrel, Invoice, InvoiceLine, Provider


User = get_user_model()


class InvoiceEndpointTests(APITestCase):
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

    def test_add_line_returns_400_when_barrel_provider_does_not_match_invoice_provider(self):
        provider_a = self.create_provider("Acme Oils", "TAX-12345")
        provider_b = self.create_provider("Beta Oils", "TAX-67890")
        user_a = self.create_user("provider_user", provider_a)
        invoice = self.create_invoice(provider_a, "INV-001")
        barrel = self.create_barrel(provider_b, "BAR-001")
        self.client.force_authenticate(user=user_a)

        payload = {
            "barrel": barrel.id,
            "liters": barrel.liters,
            "unit_price": "1.25",
            "description": "Invoice line",
        }

        response = self.client.post(
            reverse("invoice-add-line", args=[invoice.id]),
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)
        self.assertIn("provider", str(response.data["detail"]).lower())
        self.assertEqual(InvoiceLine.objects.count(), 0)
        barrel.refresh_from_db()
        self.assertFalse(barrel.billed)

    def test_invoice_list_returns_only_invoices_from_the_logged_in_user_provider(self):
        provider_a = self.create_provider("Acme Oils", "TAX-12345")
        provider_b = self.create_provider("Beta Oils", "TAX-67890")
        user_a = self.create_user("provider_user_list", provider_a)
        own_invoice = self.create_invoice(provider_a, "INV-001")
        other_invoice = self.create_invoice(provider_b, "INV-002")
        self.client.force_authenticate(user=user_a)

        response = self.client.get(reverse("invoice-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_invoice_ids = {invoice_data["id"] for invoice_data in response.data}
        self.assertIn(own_invoice.id, returned_invoice_ids)
        self.assertNotIn(other_invoice.id, returned_invoice_ids)

    def test_invoice_detail_returns_404_for_invoices_from_other_providers(self):
        provider_a = self.create_provider("Acme Oils", "TAX-12345")
        provider_b = self.create_provider("Beta Oils", "TAX-67890")
        user_a = self.create_user("provider_user_detail", provider_a)
        other_invoice = self.create_invoice(provider_b, "INV-002")
        self.client.force_authenticate(user=user_a)

        response = self.client.get(reverse("invoice-detail", args=[other_invoice.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
