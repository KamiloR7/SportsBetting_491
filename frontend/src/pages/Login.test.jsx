import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import Login from './Login';
import { response } from '../test/fixtures';

const credentials = { email: 'synthetic@example.com', password: 'SyntheticOnly123!' };
function showLogin() {
  render(<MemoryRouter initialEntries={['/login']}><Routes><Route path="/login" element={<Login />} /><Route path="/dashboard" element={<h1>Test dashboard</h1>} /></Routes></MemoryRouter>);
}
async function fillForm() {
  await userEvent.type(screen.getByLabelText('Email address'), credentials.email);
  await userEvent.type(screen.getByLabelText('Password', { exact: true }), credentials.password);
}
describe('SCRUM-227 desktop login form with mocked API', () => {
  it('gets CSRF before login and navigates only after success', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(response({ csrf_token: 'synthetic-csrf' })).mockResolvedValueOnce(response({ id: 1, email: credentials.email }));
    vi.stubGlobal('fetch', fetch); showLogin(); await fillForm();
    await userEvent.click(screen.getByRole('button', { name: 'Sign in →' }));
    expect(await screen.findByRole('heading', { name: 'Test dashboard' })).toBeVisible();
    expect(fetch.mock.calls[0][0]).toBe('/api/auth/csrf');
    expect(fetch.mock.calls[1]).toEqual(['/api/auth/login', expect.objectContaining({ method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': 'synthetic-csrf' }, body: JSON.stringify(credentials) })]);
  });
  it('keeps an invalid login on the form with a useful error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(response({ csrf_token: 'synthetic-csrf' })).mockResolvedValueOnce(response({ detail: 'Invalid email or password.' }, 401)));
    showLogin(); await fillForm(); await userEvent.click(screen.getByRole('button', { name: 'Sign in →' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid email or password.');
    expect(screen.queryByRole('heading', { name: 'Test dashboard' })).toBeNull();
    expect(screen.getByRole('button', { name: 'Sign in →' })).toBeEnabled();
  });
  it('does not send credentials when the CSRF challenge fails', async () => {
    const fetch = vi.fn().mockResolvedValue(response({ detail: 'CSRF challenge rejected.' }, 403));
    vi.stubGlobal('fetch', fetch); showLogin(); await fillForm();
    await userEvent.click(screen.getByRole('button', { name: 'Sign in →' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('CSRF challenge rejected.');
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it('disables submission and fields while authentication is pending', async () => {
    let finish;
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(response({ csrf_token: 'synthetic-csrf' })).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; })));
    showLogin(); await fillForm(); await userEvent.click(screen.getByRole('button', { name: 'Sign in →' }));
    expect(screen.getByRole('button', { name: 'Connecting…' })).toBeDisabled();
    expect(screen.getByLabelText('Email address')).toBeDisabled();
    expect(screen.getByLabelText('Password', { exact: true })).toBeDisabled();
    await act(async () => finish(response({ detail: 'Try again later.' }, 429)));
    expect(await screen.findByRole('alert')).toHaveTextContent('Try again later.');
    expect(screen.getByRole('button', { name: 'Sign in →' })).toBeEnabled();
  });
  it('reports a registration 500 without claiming an account or login succeeded', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response('Internal Server Error', { status: 500 }));
    vi.stubGlobal('fetch', fetch); showLogin();
    await userEvent.click(screen.getByRole('button', { name: 'Create account', exact: true }));
    await fillForm(); await userEvent.click(screen.getByRole('button', { name: 'Create account & start playing →' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Request failed. Check your input and try again.');
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][0]).toBe('/api/auth/register');
    expect(screen.queryByRole('heading', { name: 'Test dashboard' })).toBeNull();
  });
  it('keeps passwords masked until Show is selected', async () => {
    showLogin();
    expect(screen.getByLabelText('Password', { exact: true })).toHaveAttribute('type', 'password');
    await userEvent.click(screen.getByRole('button', { name: 'Show', exact: true }));
    expect(screen.getByLabelText('Password', { exact: true })).toHaveAttribute('type', 'text');
    await userEvent.click(screen.getByRole('button', { name: 'Hide', exact: true }));
    expect(screen.getByLabelText('Password', { exact: true })).toHaveAttribute('type', 'password');
  });
});
