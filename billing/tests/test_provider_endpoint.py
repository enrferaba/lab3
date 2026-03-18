from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from billing.models import Barrel, Provider


User = get_user_model()


class ProviderEndpointTests(APITestCase):
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
    def create_barrel(provider: Provider, number: str, liters: int, billed: bool) -> Barrel:
        return Barrel.objects.create(
            provider=provider,
            number=number,
            oil_type="olive",
            liters=liters,
            billed=billed,
        )

    def test_provider_list_returns_only_the_logged_in_user_provider(self):
        provider = self.create_provider("Acme Oils", "TAX-12345")
        self.create_provider("Other Oils", "TAX-99999")
        self.create_barrel(provider, "BAR-001", liters=120, billed=True)
        self.create_barrel(provider, "BAR-002", liters=80, billed=False)

        user = self.create_user("provider_user", provider)
        self.client.force_authenticate(user=user)

        response = self.client.get(reverse("provider-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIn("name", response.data[0])
        self.assertIn("tax_id", response.data[0])
        self.assertIn("liters_billed", response.data[0])
        self.assertIn("liters_to_bill", response.data[0])
        self.assertEqual(response.data[0]["name"], provider.name)
        self.assertEqual(response.data[0]["tax_id"], provider.tax_id)
        self.assertEqual(response.data[0]["liters_billed"], 120)
        self.assertEqual(response.data[0]["liters_to_bill"], 80)

    def test_provider_list_returns_all_providers_for_superuser(self):
        provider_a = self.create_provider("Acme Oils", "TAX-12345")
        provider_b = self.create_provider("Beta Oils", "TAX-67890")
        self.create_barrel(provider_a, "BAR-001", liters=120, billed=True)
        self.create_barrel(provider_a, "BAR-002", liters=80, billed=False)
        self.create_barrel(provider_b, "BAR-003", liters=50, billed=False)

        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="strongpass123",
        )
        self.client.force_authenticate(user=admin)

        response = self.client.get(reverse("provider-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        providers_by_id = {provider_data["id"]: provider_data for provider_data in response.data}
        self.assertEqual(providers_by_id[provider_a.id]["liters_billed"], 120)
        self.assertEqual(providers_by_id[provider_a.id]["liters_to_bill"], 80)
        self.assertEqual(providers_by_id[provider_b.id]["liters_billed"], 0)
        self.assertEqual(providers_by_id[provider_b.id]["liters_to_bill"], 50)

    def test_provider_detail_returns_provider_data_for_superuser(self):
        provider = self.create_provider("Acme Oils", "TAX-12345")
        admin = User.objects.create_superuser(
            username="admin-detail",
            email="admin-detail@example.com",
            password="strongpass123",
        )
        self.client.force_authenticate(user=admin)

        response = self.client.get(reverse("provider-detail", args=[provider.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], provider.id)
        self.assertEqual(response.data["name"], provider.name)

    def test_provider_detail_returns_403_for_non_superusers(self):
        provider = self.create_provider("Acme Oils", "TAX-12345")
        user = self.create_user("provider_user_detail", provider)
        self.client.force_authenticate(user=user)

        response = self.client.get(reverse("provider-detail", args=[provider.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
