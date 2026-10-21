"""Optional static hosting does not swallow API routes or expose other files."""
import importlib


def test_backend_only_root_is_preserved(api):
    main = importlib.import_module("app.main")
    status, body = api("GET", "/", target_app=main.create_app())
    assert status == 200 and body["name"] == "Nodum API"


def test_bundled_product_serves_html_assets_and_keeps_api(api, monkeypatch, tmp_path):
    main = importlib.import_module("app.main")
    monkeypatch.setattr(main, "__file__", str(tmp_path / "main.py"))
    product = tmp_path / "web" / "product"
    (product / "assets").mkdir(parents=True)
    (product / "index.html").write_text("<html>synthetic product</html>")
    (product / "assets" / "app.js").write_text("console.log('synthetic')")
    (tmp_path / "private.txt").write_text("must not be served")
    app = main.create_app()
    assert api("GET", "/", target_app=app)[0] == 307
    assert api("GET", "/app/", target_app=app) == (200, "<html>synthetic product</html>")
    assert api("GET", "/app/assets/app.js", target_app=app)[0] == 200
    assert api("GET", "/health", target_app=app) == (200, {"status": "healthy"})
    assert api("GET", "/app/../../private.txt", target_app=app)[0] == 404
    assert api("GET", "/app/auth/session", target_app=app)[0] == 404
