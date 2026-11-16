const BASE_URL = (import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");
export async function apiRequest(endpoint, options = {}) {
  let response;
  try { response = await fetch(`${BASE_URL}${endpoint}`, { credentials: "same-origin", ...options }); }
  catch (error) { if (error.name === "AbortError") throw error; throw new Error("Cannot reach the backend.", {cause:error}); }
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const message = typeof payload?.detail === "string" ? payload.detail : "Request failed. Check your input and try again.";
    const error = new Error(message); error.status = response.status; throw error;
  }
  if (response.status === 204) return null;
  return response.json();
}
export async function mutation(endpoint, body) {
  const { csrf_token } = await apiRequest("/auth/csrf");
  return apiRequest(endpoint, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf_token }, body: JSON.stringify(body) });
}
