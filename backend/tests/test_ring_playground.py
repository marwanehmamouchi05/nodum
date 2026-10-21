"""Official sandbox discovery never becomes live linking or tenant authority."""
from unittest.mock import patch

from test_product_release import product  # noqa: F401
from test_authorization import headers


def test_playground_requires_operator_and_private_token(product, api, monkeypatch):
    repo, users, _ = product
    assert api("GET", "/ring/playground/devices")[0] == 401
    for name in ["demo-resident", "demo-business", "demo-staff", "demo-admin"]:
        assert api("GET", "/ring/playground/devices", headers=headers(repo, users[name].id))[0] == 403
    monkeypatch.delenv("RING_PLAYGROUND_TOKEN", raising=False)
    assert api("GET", "/ring/playground/devices", headers=headers(repo, users["demo-manager"].id))[0] == 503


def test_official_discovery_is_filtered_and_does_not_change_accounts(product, api, monkeypatch):
    repo, users, _ = product
    monkeypatch.setenv("RING_PLAYGROUND_TOKEN", "synthetic-private-playground-token")
    before = repo.list_ring_accounts(), repo.list_ring_events(), repo.list_permissions()
    remote = {"data": [{"id": "sandbox-device", "type": "devices", "attributes": {
        "name": "Official sandbox device", "image_url": "https://example.test/private", "secret": "not returned"}}]}
    with patch("app.integrations.ring.client.RingClient.api", return_value=remote) as call:
        status, body = api("GET", "/ring/playground/devices", headers=headers(repo, users["demo-manager"].id))
    assert status == 200 and body["source"] == "official_ring_playground"
    assert body["devices"] == [{"id": "sandbox-device", "name": "Official sandbox device"}]
    assert "image_url" not in str(body) and "synthetic-private-playground-token" not in str(body)
    call.assert_called_once_with("GET", "/v1/devices", "synthetic-private-playground-token")
    assert (repo.list_ring_accounts(), repo.list_ring_events(), repo.list_permissions()) == before


def test_playground_production_requires_explicit_demo(product, api, monkeypatch):
    repo, users, _ = product
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_PUBLIC_ORIGIN", "https://test")
    assert api("GET", "/ring/playground/devices", headers=[(k, v.replace(b"nodum_session=", b"__Host-nodum_session=")) for k, v in headers(repo, users["demo-manager"].id)])[0] == 403
