import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiRequest } from './api';
import { getMatches } from './matches';

vi.mock('./api', () => ({ apiRequest: vi.fn() }));

function parameters(filters) {
  getMatches(3, filters);
  return new URL(apiRequest.mock.calls.at(-1)[0], 'http://localhost').searchParams;
}

beforeEach(() => vi.clearAllMocks());

describe('SCRUM-211 local calendar date filters', () => {
  it('sends the selected local day even when its UTC date differs', () => {
    const params = parameters({ date: '2026-11-19', teamId: 7, status: 'scheduled' });
    expect(params.get('date_start')).not.toBeNull();
    expect(params.get('date_end')).not.toBeNull();
    const start = new Date(params.get('date_start'));
    const end = new Date(params.get('date_end'));
    expect([start.getFullYear(), start.getMonth(), start.getDate(), start.getHours()]).toEqual([2026, 10, 19, 0]);
    expect([end.getFullYear(), end.getMonth(), end.getDate(), end.getHours()]).toEqual([2026, 10, 20, 0]);
    expect(params.get('team_id')).toBe('7');
    expect(params.get('status')).toBe('scheduled');
    expect(params.get('league_id')).toBe('3');
  });

  it.each(['2026-03-08', '2026-11-01'])('keeps local midnight boundaries across DST on %s', date => {
    const params = parameters({ date });
    expect(params.get('date_start')).not.toBeNull();
    expect(params.get('date_end')).not.toBeNull();
    const start = new Date(params.get('date_start'));
    const end = new Date(params.get('date_end'));
    expect(start.getHours()).toBe(0);
    expect(end.getHours()).toBe(0);
    expect(end.getDate()).toBe(start.getDate() + 1);
    const durationHours = (end - start) / 3_600_000;
    expect(durationHours).toBe(24 + (end.getTimezoneOffset() - start.getTimezoneOffset()) / 60);
  });

  it.each(['2026-02-30', '2026-13-01', 'not-a-date', '2026-1-2', '2026-11-19T00:00:00Z'])('omits invalid calendar date %s', date => {
    const params = parameters({ date });
    expect(params.has('date_start')).toBe(false);
    expect(params.has('date_end')).toBe(false);
  });

  it.each([undefined, null, 42, {}])('omits a non-string date %s', date => {
    const params = parameters({ date });
    expect(params.has('date_start')).toBe(false);
    expect(params.has('date_end')).toBe(false);
  });

  it('keeps the date independent from the browser today view and paging', () => {
    const params = parameters({ date: '2026-11-19', status: 'today_results', search: 'City', offset: 12, limit: 12 });
    expect(params.has('date_start')).toBe(true);
    expect(params.has('date_end')).toBe(true);
    expect(params.get('view')).toBe('today_results');
    expect(params.has('day_start')).toBe(true);
    expect(params.get('offset')).toBe('12');
    expect(params.get('search')).toBe('City');
  });
});
