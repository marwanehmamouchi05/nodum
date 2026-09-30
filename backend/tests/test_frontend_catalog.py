def test_catalog_uses_repository_and_hides_credential_material(api, repo):
    status, data = api("GET", "/building/catalog")
    assert status == 200
    assert len(data["people"]) == len(repo.list_people())
    assert len(data["zones"]) == len(repo.list_zones())
    assert data["businesses"][0]["id"] == "atlas-dental"
    assert data["work_orders"]
    assert data["credentials"]
    assert set(data["credentials"][0]) == {"id", "kind", "person_id", "active"}
