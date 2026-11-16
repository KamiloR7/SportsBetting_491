import { apiRequest } from "./api";

export function getLeagues(options = {}) {
  return apiRequest("/leagues", options);
}

export function getMatches(leagueId, filters = {}, options = {}) {
  const params = new URLSearchParams({
    league_id: String(leagueId),
  });

  params.set("limit", String(filters.limit || 30));
  params.set("offset", String(filters.offset || 0));
  if (filters.search) params.set("search", filters.search);
  if (filters.status === "final") params.set("order", "desc");
  if (filters.status) {
    params.set("status", filters.status);
  }

  return apiRequest(`/matches?${params.toString()}`, options);
}

export function getMatchHistory(leagueId, teamId, limit = 3, options = {}, before = null) {
  return apiRequest(
    `/matches/history?league_id=${encodeURIComponent(leagueId)}&team_id=${encodeURIComponent(teamId)}&limit=${encodeURIComponent(limit)}${before ? `&before=${encodeURIComponent(before)}` : ""}`,
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
