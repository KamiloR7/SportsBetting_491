import { apiRequest } from "./api";

export function addBet(bet) {
  return apiRequest("/bets", {
    method: "POST",
    body: JSON.stringify(bet),
  });
}