import testMatches
  from "../data/testMatches";

export async function getMatches() {
  return testMatches;
}

export async function getMatchById(id) {
  const match = testMatches.find(
    (match) =>
      match.id === Number(id)
  );

  if (!match) {
    throw new Error(
      "Match not found"
    );
  }

  return match;
}