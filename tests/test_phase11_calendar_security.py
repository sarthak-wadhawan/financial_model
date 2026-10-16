"""S1: hostile retained facts cannot become ICS properties or executable links."""
from datetime import datetime, timezone

import pytest

from trading_copilot.calendar.models import CalendarEvent, CalendarExportRequest
from trading_copilot.calendar.security import safe_calendar_url
from trading_copilot.calendar.service import CalendarService
from trading_copilot.events.store import EventStore
from trading_copilot.models.events import MarketEvent


def calendar_event(**overrides):
    return CalendarEvent(**{
        'uid': 'valid-id@trading-copilot', 'summary': 'Fixture',
        'dtstart': datetime(2026, 10, 14, tzinfo=timezone.utc),
        'dtstamp': datetime(2026, 10, 14, tzinfo=timezone.utc),
        **overrides,
    })


@pytest.mark.parametrize('control', ['\r\n', '\r', '\n', '\x00', '\t', '\x1f', '\x7f', '\x85', '\u202e'])
@pytest.mark.parametrize('field', ['uid', 'url', 'categories'])
def test_serializer_rejects_injected_non_text_properties(field, control):
    value = 'https://example.com/' + control + 'BEGIN:VALARM'
    event = calendar_event(**{field: [value] if field == 'categories' else value})
    before = event.model_dump()
    with pytest.raises(ValueError, match='Invalid calendar'):
        CalendarService(None)._generate_ics([event])
    assert event.model_dump() == before  # no stripping/repaired identities


@pytest.mark.parametrize('url', [
    'javascript:alert(1)', 'data:text/plain,fixture', 'file:///fixture',
    '//example.com/file', '/relative', 'https://', 'https://user:pass@example.com/file',
    'https://@example.com/file', 'https://example.com:99999/file',
    'https://example.com:/file', 'https://example.com/%0D%0ABEGIN:VALARM',
    'https://example.com/%00', 'https://example.com/%C2%85',
    'https://example.com/%zz', 'https://example.com/%FF',
    'https://example.com\\@evil.example/', 'https://[::1]evil/path',
    'https://bad..example/path', 'https://example.com/<fixture>',
])
def test_serializer_rejects_unsafe_navigation_urls(url):
    assert safe_calendar_url(url) is None
    with pytest.raises(ValueError, match='Invalid calendar URL'):
        CalendarService(None)._generate_ics([calendar_event(url=url)])


@pytest.mark.parametrize('url', [
    'https://www.sec.gov/Archives/edgar/data/1/report.htm?a=1&b=2#item',
    'https://www.bls.gov/news.release/cpi.htm',
    'HTTP://Example.COM:8080/source?q=a%20b', 'https://[2001:db8::1]/source',
])
def test_valid_source_urls_are_verbatim_and_text_is_escaped(url):
    event = calendar_event(url=url, uid='id,part;value', summary='First\r\nBEGIN:VALARM',
                           categories=['earnings,quarter;annual'], description='Raw\x00evidence')
    content = CalendarService(None)._generate_ics([event]).replace('\r\n ', '')
    assert f'URL:{url}\r\n' in content
    assert 'UID:id\\,part\\;value\r\n' in content
    assert 'CATEGORIES:earnings\\,quarter\\;annual\r\n' in content
    assert 'SUMMARY:First\\nBEGIN:VALARM\r\n' in content
    assert '\r\nBEGIN:VALARM' not in content
    assert 'DESCRIPTION:Raw[U+0000]evidence' in content


def test_export_suppresses_hostile_links_skips_bad_uid_and_preserves_evidence(tmp_path):
    store = EventStore(tmp_path / 'isolated.db')
    malicious_url = 'https://example.com/\r\nBEGIN:VALARM\r\nACTION:DISPLAY\x00'
    poison_uid = 'bad\r\nBEGIN:VALARM'
    date = datetime(2026, 10, 14, tzinfo=timezone.utc)
    records = [
        MarketEvent(event_id='safe-date', event_type='earnings', title='Date', source='fixture', source_id='one', scheduled_at=date, source_url=malicious_url),
        MarketEvent(event_id='safe-session', event_type='earnings', title='Session', source='fixture', source_id='two', scheduled_at=date.replace(hour=21), metadata={'time': 'amc'}),
        MarketEvent(event_id='safe-exact', event_type='earnings', title='Exact', source='fixture', source_id='three', scheduled_at=date, source_url='https://www.sec.gov/source', metadata={'time_precision': 'exact'}),
        MarketEvent(event_id=poison_uid, event_type='earnings', title='Poison ID', source='fixture', source_id='four', scheduled_at=date),
    ]
    for record in records:
        store.upsert_event(record)
    before = {record.event_id: store.get_event(record.event_id).model_dump() for record in records}
    before_revisions = {record.event_id: store.get_revisions(record.event_id) for record in records}
    result = CalendarService(store).export_events(CalendarExportRequest())
    content = result.content.replace('\r\n ', '')
    assert result.event_count == 3
    assert result.skipped_event_count == 1
    assert '\r\nBEGIN:VALARM' not in content
    assert '\r\nACTION:DISPLAY' not in content
    assert '\x00' not in content
    assert 'URL:https://example.com' not in content
    assert 'Source: https://example.com/\\nBEGIN:VALARM\\nACTION:DISPLAY[U+0000]' in content
    assert 'URL:https://www.sec.gov/source\r\n' in content
    assert content.count('DTSTART;VALUE=DATE:20261014') == 2
    assert 'DTSTART:20261014T000000Z' in content  # valid exact midnight preserved
    assert 'DTSTART:20261014T210000Z' not in content  # session is not exact
    assert 'Session: amc' in content
    for record in records:
        assert store.get_event(record.event_id).model_dump() == before[record.event_id]
        assert store.get_revisions(record.event_id) == before_revisions[record.event_id]
