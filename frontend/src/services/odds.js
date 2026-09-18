import testMatches
  from "../data/testMatches";

export async function getOddsByMatchId(
  matchId
) {
  const match = testMatches.find(
    (match) =>
      match.id === Number(matchId)
  );

  if (!match) {
    throw new Error(
      "Odds unavailable"
    );
  }

  return match.odds;
}