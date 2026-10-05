import { apiRequest } from "./api";

export function getLeagues(options = {}) {
  return apiRequest("/leagues", options);
}

export function getMatches(leagueId, options = {}) {
  return apiRequest(`/matches?league_id=${encodeURIComponent(leagueId)}`, options);
}

export async function getMatchById(id, options = {}) {
  if (!/^[1-9]\d*$/.test(String(id))) {
    throw new Error("This match ID is invalid.");
  }
  return apiRequest(`/matches/${encodeURIComponent(id)}`, options);
}
