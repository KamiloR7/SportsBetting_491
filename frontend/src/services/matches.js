import { apiRequest } from "./api";

export function getLeagues(options = {}) {
  return apiRequest("/leagues", options);
}

export function getTeams(options = {}) {
  return apiRequest("/teams", options);
}

export function getMatches(leagueId, filters = {}, options = {}) {
  const params = new URLSearchParams({
    league_id: String(leagueId),
  });

  params.set("limit", String(filters.limit || 30));
  params.set("offset", String(filters.offset || 0));
  if (filters.search) params.set("search", filters.search);
  if (filters.teamId) params.set("team_id", String(filters.teamId));
  if (filters.date) {
    const start = new Date(`${filters.date}T00:00:00`);
    if (!Number.isNaN(start.getTime()) && start.toISOString().slice(0, 10) === filters.date) {
      const end = new Date(start);
      end.setDate(end.getDate() + 1);
      params.set("date_start", start.toISOString());
      params.set("date_end", end.toISOString());
    }
  }
  if (filters.status === "final") params.set("order", "desc");
  if (["matchday", "today_results"].includes(filters.status)) {
    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const end = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
    params.set("view", filters.status);
    if (filters.status === "today_results") params.set("order", "desc");
    params.set("day_start", start.toISOString());
    params.set("day_end", end.toISOString());
  } else if (filters.status) {
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
