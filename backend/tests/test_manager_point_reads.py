"""Single-record mutations must not load every tenant's operational history."""
from datetime import timedelta

from conftest import NOW
from test_manager import manager, report  # noqa: F401
from test_structure import structure  # noqa: F401
from app.models.manager import VisitorInput, MaintenanceUpdate


def test_record_updates_do_not_bulk_load_operational_history(manager, monkeypatch):
    visitor=manager.invite(VisitorInput(location_id='demo-org:reference:apartment-101',name='Synthetic visitor',
        starts_at=NOW,ends_at=NOW+timedelta(hours=1)))
    issue=report(manager)
    def forbidden(kind):
        raise AssertionError('Single-record mutation loaded full operational history')
    monkeypatch.setattr(manager.repo,'list_operational_records',forbidden)
    assert manager.arrive(visitor['id'])['checked_in_at']
    result=manager.update_maintenance(issue['id'],MaintenanceUpdate(status='in_progress'))
    assert result['status']=='in_progress'
