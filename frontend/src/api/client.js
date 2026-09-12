const BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

async function request(path, { method = "GET", body, signal } = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    signal,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const data = await response.json();
      if (typeof data.detail === "string") detail = data.detail;
      else if (Array.isArray(data.detail)) detail = data.detail.map((d) => d.msg).join("; ");
    } catch {
      // non-JSON error body (e.g. proxy error when the API is down)
    }
    throw new Error(detail);
  }
  return response.json();
}

export const api = {
  health: () => request("/api/health"),
  searchPlayers: (q = "", limit = 20, signal) =>
    request(`/api/players?${new URLSearchParams({ q, limit })}`, { signal }),
  getPlayer: (id) => request(`/api/players/${id}`),
  predict: (payload, signal) => request("/api/predict", { method: "POST", body: payload, signal }),
  metrics: () => request("/api/metrics"),
  evaluation: () => request("/api/evaluation"),
  plotUrl: (file, version) => `${BASE_URL}/plots/${file}${version ? `?v=${encodeURIComponent(version)}` : ""}`,
};
