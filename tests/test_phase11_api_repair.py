"""HTTP Phase 11 contracts with injected isolated services; no API lifespan/production DB."""
import pytest
from fastapi.testclient import TestClient
from trading_copilot.watchlists.service import WatchlistService
from trading_copilot.watchlists.store import WatchlistStore
from trading_copilot.alerts.service import AlertService
from trading_copilot.alerts.store import AlertStore
from trading_copilot.calendar.service import CalendarService
from trading_copilot.events.store import EventStore


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    import backend.main as backend
    monkeypatch.setattr(backend, 'watchlist_service', WatchlistService(WatchlistStore(tmp_path / 'isolated.db')))
    monkeypatch.setattr(backend, 'alert_service', AlertService(AlertStore(tmp_path / 'isolated.db')))
    monkeypatch.setattr(backend, 'calendar_service', CalendarService(EventStore(tmp_path / 'isolated.db')))
    return TestClient(backend.app, raise_server_exceptions=False)


def test_watchlist_http_crud_reorder_notes_default_and_duplicates(api_client):
    client = api_client
    response = client.post('/api/v1/watchlists', json={'name': 'HTTP research'})
    assert response.status_code == 201
    identifier = response.json()['id']
    root = '/api/v1/watchlists/' + identifier
    for symbol in ['AAPL', 'BRK.B']:
        assert client.post(root + '/items', json={'symbol': symbol}).status_code == 201
    duplicate = client.post(root + '/items', json={'symbol': 'aapl'})
    assert duplicate.status_code in (400, 409)
    assert client.patch(root + '/items/AAPL', json={'notes': 'Preserved'}).status_code == 200
    assert client.post(root + '/reorder', json={'symbols': ['BRK.B', 'AAPL']}).status_code == 200
    response = client.get(root)
    assert response.json()['symbols'] == ['BRK.B', 'AAPL']
    assert response.json()['items'][1]['notes'] == 'Preserved'
    assert client.patch(root, json={'is_default': True, 'name': 'Renamed'}).status_code == 200
    assert client.get('/api/v1/watchlists/default').json()['id'] == identifier
    assert client.post(root + '/reorder', json={'symbols': ['AAPL']}).status_code in (400, 422)
    assert client.delete(root + '/items/AAPL').status_code == 204
    assert client.delete(root).status_code == 204
    assert client.get(root).status_code == 404


def test_alert_http_dryrun_unavailable_and_crud(api_client):
    client = api_client
    response = client.post('/api/v1/alerts', json={'name': 'HTTP alert', 'alert_type': 'price', 'symbols': ['AAPL'], 'condition': 'above', 'threshold': 100})
    assert response.status_code == 201
    identifier = response.json()['id']
    root = '/api/v1/alerts/' + identifier
    tested = client.post('/api/v1/alerts/test', json={'alert_id': identifier})
    assert tested.status_code == 200
    assert tested.json()['status'] == 'unavailable'
    assert tested.json()['would_trigger'] is None
    assert tested.json()['current_values'] == {}
    assert client.get(root).json()['trigger_count'] == 0
    assert client.patch(root, json={'name': 'Edited', 'channels': ['in_app'], 'is_active': False}).status_code == 200
    assert client.get(root).json()['is_active'] is False
    assert client.post(root + '/activate').json()['is_active'] is True
    assert client.get('/api/v1/alerts/triggers/recent').status_code == 200
    assert client.patch(root, json={'channels': ['INVALID']}).status_code == 422
    assert client.get(root).json()['channels'] == ['in_app']
    assert client.delete(root).status_code == 204
    assert client.get(root).status_code == 404


def test_calendar_http_accepts_dates_and_rejects_invalid_bounds(api_client):
    response = api_client.post('/api/v1/calendar/export', json={'from_date': '2026-10-14', 'to_date': '2026-10-14', 'importance': ['HIGH']})
    assert response.status_code == 200
    assert response.json()['event_count'] == 0
    assert response.json()['content'].startswith('BEGIN:VCALENDAR\r\n')
    assert api_client.post('/api/v1/calendar/export', json={'from_date': '2026-10-15', 'to_date': '2026-10-14'}).status_code in (400, 422)


def test_missing_parent_and_alert_dryrun_return_404(api_client):
    assert api_client.post('/api/v1/watchlists/missing/items', json={'symbol': 'AAPL'}).status_code == 404
    assert api_client.post('/api/v1/alerts/test', json={'alert_id': 'missing'}).status_code == 404
