import { apiRequest } from "./api";

export function getLeagues(options = {}) {
  return apiRequest("/leagues", options);
}

export function getMatches(leagueId, filters = {}, options = {}) {
  const params = new URLSearchParams({
    league_id: String(leagueId),
  });

  if (filters.status) {
    params.set("status", filters.status);
  }

  return apiRequest(`/matches?${params.toString()}`, options);
}

export function getMatchHistory(leagueId, limit = 100, options = {}) {
  return apiRequest(
    `/matches/history?league_id=${encodeURIComponent(leagueId)}&limit=${encodeURIComponent(limit)}`,
    options,
  );
}

export function runMatchPrediction(matchId, options = {}) {
  return apiRequest(`/predictions/matches/${encodeURIComponent(matchId)}`, {
    ...options,
    method: "POST",
  });
}

export async function getMatchById(id, options = {}) {
  if (!/^[1-9]\d*$/.test(String(id))) {
    throw new Error("This match ID is invalid.");
  }
  return apiRequest(`/matches/${encodeURIComponent(id)}`, options);
}
