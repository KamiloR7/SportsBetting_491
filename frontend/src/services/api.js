const BASE_URL = (import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");

export async function apiRequest(endpoint, options = {}) {
  let response;
  try {
    response = await fetch(`${BASE_URL}${endpoint}`, options);
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error("Unable to connect to the server. Please try again later.", { cause: error });
  }

  if (!response.ok) {
    if (response.status === 404) throw new Error("The requested item was not found.");
    throw new Error("The server could not load this data. Please try again later.");
  }

  try {
    return await response.json();
  } catch {
    throw new Error("The server returned an unexpected response. Please try again later.");
  }
}
