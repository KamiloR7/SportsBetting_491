const BASE_URL =
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000";

export async function apiRequest(
  endpoint,
  options = {}
) {
  const response = await fetch(
    `${BASE_URL}${endpoint}`,
    {
      headers: {
        "Content-Type":
          "application/json",

        ...options.headers,
      },

      ...options,
    }
  );

  if (!response.ok) {
    throw new Error(
      `Request failed: ${response.status}`
    );
  }

  return response.json();
}