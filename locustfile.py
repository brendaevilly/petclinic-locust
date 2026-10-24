"""Perfis de carga do Trabalho 06 — Spring PetClinic Microservices.

Endpoints verificados nesta versão (via API Gateway na porta 8080):

  Enunciado              Caminho real
  ---------------------  --------------------------------
  GET /owners            GET  /api/customer/owners
  GET /owners/{id}       GET  /api/customer/owners/{id}
  GET /vets              GET  /api/vet/vets
  POST /owners           POST /api/customer/owners

Uso:
  python -m locust -f locustfile.py ReadProfile --host http://localhost:8080
  python -m locust -f locustfile.py WriteProfile --host http://localhost:8080
"""

from __future__ import annotations

import json
import random
import uuid
import urllib.request

from locust import HttpUser, between, tag


OWNER_PAYLOAD_CITIES = ("Madison", "Monona", "Sun Prairie", "McFarland", "Windsor")


def _owner_payload() -> dict[str, str]:
    suffix = uuid.uuid4().hex[:8]
    return {
        "firstName": f"Load{suffix[:4]}",
        "lastName": f"User{suffix[4:]}",
        "address": f"{random.randint(1, 9999)} Test Ave.",
        "city": random.choice(OWNER_PAYLOAD_CITIES),
        "telephone": f"{random.randint(1000000000, 1999999999)}",
    }


class PetClinicUser(HttpUser):
    abstract = True
    wait_time = between(1, 2)
    owner_ids: list[int] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    def on_start(self) -> None:
        self._refresh_owner_ids()

    def _refresh_owner_ids(self) -> None:
        # Fora do client do Locust para não misturar bootstrap nas métricas.
        url = f"{self.host.rstrip('/')}/api/customer/owners"
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                owners = json.loads(response.read().decode("utf-8"))
            ids = [owner["id"] for owner in owners if "id" in owner]
            if ids:
                self.owner_ids = ids
        except Exception:
            pass

    def _random_owner_id(self) -> int:
        return random.choice(self.owner_ids)

    @tag("owners")
    def get_owners(self) -> None:
        with self.client.get("/api/customer/owners", name="GET /owners", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")
                return
            try:
                owners = response.json()
                ids = [owner["id"] for owner in owners if "id" in owner]
                if ids:
                    self.owner_ids = ids
                response.success()
            except Exception as exc:  # noqa: BLE001
                response.failure(str(exc))

    @tag("owner")
    def get_owner_by_id(self) -> None:
        owner_id = self._random_owner_id()
        self.client.get(f"/api/customer/owners/{owner_id}", name="GET /owners/{id}")

    @tag("vets")
    def get_vets(self) -> None:
        self.client.get("/api/vet/vets", name="GET /vets")

    @tag("create")
    def post_owner(self) -> None:
        with self.client.post(
            "/api/customer/owners",
            json=_owner_payload(),
            name="POST /owners",
            catch_response=True,
        ) as response:
            if response.status_code not in (200, 201):
                response.failure(f"HTTP {response.status_code}")
                return
            try:
                created = response.json()
                created_id = created.get("id")
                if created_id:
                    self.owner_ids.append(int(created_id))
                response.success()
            except Exception as exc:  # noqa: BLE001
                response.failure(str(exc))


class ReadProfile(PetClinicUser):
    """Perfil 1 — 45% GET /owners, 35% GET /owners/{id}, 15% GET /vets, 5% POST /owners."""

    tasks = {
        PetClinicUser.get_owners: 45,
        PetClinicUser.get_owner_by_id: 35,
        PetClinicUser.get_vets: 15,
        PetClinicUser.post_owner: 5,
    }


class WriteProfile(PetClinicUser):
    """Perfil 2 — 20% GET /owners, 20% GET /owners/{id}, 20% GET /vets, 40% POST /owners."""

    tasks = {
        PetClinicUser.get_owners: 20,
        PetClinicUser.get_owner_by_id: 20,
        PetClinicUser.get_vets: 20,
        PetClinicUser.post_owner: 40,
    }
