import { describe, expect, it, vi } from 'vitest';
import { apiRequest, mutation } from './api';
import { createPrediction } from './predictions';
import { response } from '../test/fixtures';

describe('SCRUM-227 service integration with mocked fetch', () => {
  it('sends pre-login CSRF and same-origin credentials before a mutation', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(response({ csrf_token: 'synthetic-csrf' })).mockResolvedValueOnce(response({ id: 1 }));
    vi.stubGlobal('fetch', fetch);
    await mutation('/auth/login', { email: 'synthetic@example.com', password: 'SyntheticOnly!' });
    expect(fetch.mock.calls[0][0]).toBe('/api/auth/csrf');
    expect(fetch.mock.calls[1]).toEqual(['/api/auth/login', expect.objectContaining({ method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': 'synthetic-csrf' } })]);
  });
  it('stops before mutation if CSRF fails', async () => {
    const fetch = vi.fn().mockResolvedValue(response({ detail: 'Invalid CSRF token.' }, 403)); vi.stubGlobal('fetch', fetch);
    await expect(mutation('/bets', {})).rejects.toMatchObject({ status: 403 });
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it.each([401, 409, 422, 429, 503])('preserves a %s service status and useful message', async status => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ detail: 'Synthetic failure.' }, status)));
    await expect(apiRequest('/test')).rejects.toMatchObject({ message: 'Synthetic failure.', status });
  });
  it('handles malformed error payloads without crashing the UI', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('not JSON', { status: 500 })));
    await expect(apiRequest('/test')).rejects.toMatchObject({ status: 500, message: 'Request failed. Check your input and try again.' });
  });
  it('handles no-content logout', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    await expect(apiRequest('/auth/logout')).resolves.toBeNull();
  });
  it('distinguishes a network failure from a request cancellation', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValueOnce(new TypeError('offline')).mockRejectedValueOnce(new DOMException('cancelled', 'AbortError')));
    await expect(apiRequest('/test')).rejects.toThrow('Cannot reach the backend.');
    await expect(apiRequest('/test')).rejects.toMatchObject({ name: 'AbortError' });
  });
  it.each([0, -1, 'invalid'])('rejects invalid match ID %s without fetching', async id => {
    const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
    await expect(createPrediction(id)).rejects.toThrow('match ID is invalid');
    expect(fetch).not.toHaveBeenCalled();
  });
});
