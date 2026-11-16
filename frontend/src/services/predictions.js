import { apiRequest } from "./api";

export function createPrediction(matchId, options = {}, replay = false) {
  if (!Number.isInteger(Number(matchId)) || Number(matchId) < 1) {
    return Promise.reject(new Error("This match ID is invalid."));
  }
  return apiRequest(replay ? "/predictions/replay" : "/predictions", {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json", ...options.headers },
    body: JSON.stringify({ match_id: Number(matchId) }),
  });
}
