"""Phase 11 regressions: public services only, isolated databases, no live providers."""
from datetime import datetime, timezone, timedelta

import pytest
from pydantic import ValidationError

from trading_copilot.watchlists.store import WatchlistStore
from trading_copilot.watchlists.service import WatchlistService
from trading_copilot.watchlists.models import WatchlistCreate, WatchlistUpdate, WatchlistItemCreate, WatchlistItemUpdate
from trading_copilot.alerts.store import AlertStore
from trading_copilot.alerts.service import AlertService
from trading_copilot.alerts.models import AlertCreate, AlertUpdate, AlertTestRequest
from trading_copilot.calendar.service import CalendarService
from trading_copilot.calendar.models import CalendarExportRequest
from trading_copilot.events.store import EventStore
from trading_copilot.models.events import MarketEvent


def test_watchlist_crud_default_notes_reorder_reload(tmp_path):
    path = tmp_path / 'watch.db'
    service = WatchlistService(WatchlistStore(path))
    first = service.create_watchlist(WatchlistCreate(name='First', is_default=True))
    second = service.create_watchlist(WatchlistCreate(name='Second'))
    service.set_default_watchlist(second.id)
    service = WatchlistService(WatchlistStore(path))
    assert [w.id for w in service.get_all_watchlists() if w.is_default] == [second.id]
    assert service.set_default_watchlist('missing') is None
    assert service.get_default_watchlist().id == second.id
    service.update_watchlist(second.id, WatchlistUpdate(name='Renamed', description='Research'))
    service.add_item(second.id, WatchlistItemCreate(symbol=' aapl ', notes='Original'))
    service.add_item(second.id, WatchlistItemCreate(symbol='BRK.B'))
    with pytest.raises(ValueError, match='already'):
        service.add_item(second.id, WatchlistItemCreate(symbol='aapl'))
    with pytest.raises(KeyError):
        service.add_item('missing', WatchlistItemCreate(symbol='AAPL'))
    service.update_item(second.id, 'aapl', WatchlistItemUpdate(notes='Edited'))
    service.reorder_items(second.id, ['brk.b', 'aapl'])
    service = WatchlistService(WatchlistStore(path))
    result = service.get_watchlist_with_items(second.id)
    assert result.name == 'Renamed'
    assert result.symbols == ['BRK.B', 'AAPL']
    assert [i.symbol for i in result.items] == result.symbols
    assert result.items[1].notes == 'Edited'
    service.update_item(second.id, 'AAPL', WatchlistItemUpdate(notes=None))
    assert service.get_item(second.id, 'AAPL').notes is None
    for bad in [['AAPL'], ['AAPL', 'AAPL'], ['AAPL', 'MSFT']]:
        with pytest.raises(ValueError, match='exactly once'):
            service.reorder_items(second.id, bad)
    assert service.get_symbols(second.id) == ['BRK.B', 'AAPL']
    assert service.remove_item(second.id, 'aapl')
    assert service.delete_watchlist(second.id)
    assert WatchlistStore(path).get_items(second.id) == []
    assert service.get_watchlist(first.id) is not None


@pytest.fixture
def alerts(tmp_path):
    return AlertService(AlertStore(tmp_path / 'alerts.db'))


def create_alert(service, **kwargs):
    return service.create_alert(AlertCreate(**{'name': 'Rule', 'alert_type': 'price', 'symbols': ['aapl'], 'condition': 'above', 'threshold': 100, **kwargs}))


def test_alert_crud_dryrun_real_values_unavailable_history_ack(alerts):
    alert = create_alert(alerts)
    request = AlertTestRequest(alert_id=alert.id)
    unavailable = alerts.test_alert(request)
    assert unavailable.status == 'unavailable'
    assert unavailable.would_trigger is None
    assert unavailable.current_values == {}
    assert unavailable.symbols_checked == []
    observation = {'AAPL': {'price': 101, 'source': 'isolated-provider', 'as_of': '2026-10-14T12:00:00Z'}}
    result = alerts.test_alert(request, observation)
    assert result.would_trigger is True
    assert result.current_values == observation
    assert alerts.get_triggers() == []
    assert alerts.get_alert(alert.id).trigger_count == 0
    triggers = alerts.evaluate_alerts(observation)
    assert len(triggers) == 1
    assert triggers[0].metadata['observation'] == observation['AAPL']
    assert alerts.evaluate_alerts(observation) == []  # cooldown
    assert len(alerts.get_recent_triggers()) == 1
    assert alerts.acknowledge_trigger(triggers[0].id)
    reloaded = AlertService(AlertStore(alerts.store.db_path))
    assert reloaded.get_triggers()[0].acknowledged
    assert reloaded.get_triggers()[0].acknowledged_at is not None
    updated = reloaded.update_alert(alert.id, AlertUpdate(name='Updated', channels=['in_app'], threshold=0, description='Edited'))
    assert updated.channels == ['in_app']  # no uppercase enum corruption
    assert updated.threshold == 0
    assert reloaded.deactivate_alert(alert.id).is_active is False
    assert reloaded.evaluate_alerts({'AAPL': {'price': 1000}}) == []
    assert reloaded.activate_alert(alert.id).is_active is True
    assert reloaded.delete_alert(alert.id)
    assert reloaded.get_alert(alert.id) is None
    # Historical triggers survive rule deletion for research.
    assert len(reloaded.get_triggers()) == 1
    with pytest.raises(KeyError):
        reloaded.test_alert(request)


@pytest.mark.parametrize('condition,previous,current,expected', [
    ('above', 100, 100, False), ('below', 100, 0, True), ('equals', 1, 100, True),
    ('crosses_above', 100, 101, True), ('crosses_above', 101, 102, False),
    ('crosses_below', 100, 99, True), ('crosses_below', 99, 98, False),
    ('changes', 0, 0, False), ('changes', 0, 1, True),
])
def test_alert_conditions(alerts, condition, previous, current, expected):
    alert = create_alert(alerts, condition=condition)
    response = alerts.test_alert(AlertTestRequest(alert_id=alert.id), {'AAPL': {'price': current, 'previous_price': previous}})
    assert response.status == 'evaluated'
    assert response.would_trigger is expected


@pytest.mark.parametrize('data', [{'price': None}, {'price': float('nan')}, {'price': True}, {'price': 101}])
def test_crossings_require_valid_previous_observation(alerts, data):
    alert = create_alert(alerts, condition='crosses_above')
    response = alerts.test_alert(AlertTestRequest(alert_id=alert.id), {'AAPL': data})
    assert response.would_trigger is None
    assert response.status == 'unavailable'


def test_alert_unsupported_type_and_invalid_update(alerts):
    alert = create_alert(alerts, alert_type='earnings')
    assert alerts.test_alert(AlertTestRequest(alert_id=alert.id), {'AAPL': {'price': 200}}).would_trigger is None
    with pytest.raises(ValidationError):
        AlertUpdate(condition='arbitrary')
    with pytest.raises(ValidationError):
        AlertUpdate(channels=['IN_APP'])


def test_empty_symbol_scope_means_supplied_data_only(alerts):
    alert = create_alert(alerts, symbols=[])
    request = AlertTestRequest(alert_id=alert.id)
    assert alerts.test_alert(request).would_trigger is None
    assert alerts.test_alert(request, {'XYZ': {'price': 0}}).symbols_checked == ['XYZ']
    assert alerts.evaluate_alerts({'XYZ': {'price': 101}})[0].symbol == 'XYZ'


def test_dryrun_preserves_existing_history_cooldown_and_observations(alerts):
    from copy import deepcopy
    alert = create_alert(alerts)
    observations = {'AAPL': {'price': 101, 'source': 'injected-observation', 'market_as_of': '2026-10-14T12:00:00Z'}}
    alerts.evaluate_alerts(observations)
    before_alert = alerts.get_alert(alert.id).model_dump()
    before_history = [trigger.model_dump() for trigger in alerts.get_triggers()]
    before_observations = deepcopy(observations)
    response = alerts.test_alert(AlertTestRequest(alert_id=alert.id), observations)
    assert response.status == 'evaluated'
    assert response.would_trigger is True  # condition only; no dispatch despite cooldown
    assert response.current_values == before_observations
    assert observations == before_observations
    assert alerts.get_alert(alert.id).model_dump() == before_alert
    assert [trigger.model_dump() for trigger in alerts.get_triggers()] == before_history


def event(**kwargs):
    return MarketEvent(**{'event_type': 'earnings', 'title': 'Event', 'source': 'test-fixture', 'source_id': kwargs.get('event_id'), **kwargs})


def test_calendar_date_session_exact_midnight_timezone_and_undated(tmp_path):
    store = EventStore(tmp_path / 'events.db')
    events = [
        event(event_id='date', scheduled_at=datetime(2026, 10, 14, tzinfo=timezone.utc)),
        event(event_id='session', scheduled_at=datetime(2026, 10, 14, 21, tzinfo=timezone.utc), metadata={'time': 'amc'}),
        event(event_id='exact', scheduled_at=datetime(2026, 10, 14, tzinfo=timezone.utc), metadata={'time_precision': 'exact'}),
        event(event_id='offset', scheduled_at=datetime(2026, 10, 14, 9, 30, tzinfo=timezone(timedelta(hours=-4))), metadata={'time_precision': 'exact'}),
        event(event_id='undated'),
        event(event_id='filing', released_at=datetime(2026, 10, 14, 17, tzinfo=timezone.utc), metadata={'release_time_precision': 'filing_accepted'}),
    ]
    for e in events:
        store.upsert_event(e)
    result = CalendarService(store).export_events(CalendarExportRequest())
    content = result.content.replace('\r\n ', '')
    assert result.event_count == 5
    assert result.skipped_event_count == 1
    assert content.count('DTSTART;VALUE=DATE:20261014') == 3
    assert 'DTSTART:20261014T000000Z' in content  # exact midnight is valid
    assert 'DTSTART:20261014T133000Z' in content
    assert 'DTSTART:20261014T210000Z' not in content
    assert 'Session: amc' in content
    assert 'UID:undated' not in content
    assert 'DTEND' not in content  # never manufacture duration
    assert 'SEC filing acceptance is not the announcement release time' in content


def test_calendar_filter_bounds_escaping_and_utf8_folding(tmp_path):
    store = EventStore(tmp_path / 'events.db')
    store.upsert_event(event(symbol='AAPL', scheduled_at=datetime(2026, 10, 14, 23, tzinfo=timezone.utc), importance='high', title='雪' * 80 + ', test; line\nnext'))
    store.upsert_event(event(symbol='MSFT', scheduled_at=datetime(2026, 10, 15, tzinfo=timezone.utc), importance='low'))
    service = CalendarService(store)
    request = CalendarExportRequest(from_date='2026-10-14', to_date='2026-10-14', symbols=['aapl'], importance=['HIGH'])
    result = service.export_events(request)
    assert result.event_count == 1
    assert all(len(line.encode('utf-8')) <= 75 for line in result.content.split('\r\n'))
    assert '\\, test\\; line\\nnext' in result.content.replace('\r\n ', '')
    with pytest.raises(ValueError):
        service.export_events(CalendarExportRequest(from_date='2026-10-15', to_date='2026-10-14'))
