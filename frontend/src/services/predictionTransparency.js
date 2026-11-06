const UNSUPPORTED = "Unsupported or undisclosed probability configuration.";

export function predictionDisplay(result) {
  if (!result || !["NFL", "MLB", "EPL"].includes(result.sport)
      || result.probability_calibration !== "uncalibrated"
      || !Array.isArray(result.estimated_outcomes)) throw new Error(UNSUPPORTED);
  const estimated = [...result.estimated_outcomes].sort();
  const method = result.probability_method;
  let message;
  let probabilities;
  if (method === "direct_binary" && estimated.length === 0) {
    const source = result.probabilities;
    if (source && Object.hasOwn(source, "not_home_win")) {
      probabilities = { home_win: source.home_win, not_home_win: source.not_home_win };
      if (Object.keys(source).length !== 2) throw new Error(UNSUPPORTED);
      message = "Direct binary home-win versus not-home-win model. Draw and away-win probabilities are not separately modeled.";
    } else if (result.sport !== "EPL") {
      probabilities = source || { home_win: result.home_win_probability, away_win: result.away_win_probability };
      message = "Direct binary home-win versus away-win model.";
    } else throw new Error(UNSUPPORTED);
  } else if (method === "direct_multiclass" && result.sport === "EPL" && estimated.length === 0) {
    probabilities = result.probabilities;
    message = "Direct three-class model probabilities: home win, draw, and away win.";
  } else if (method === "estimated_epl_split" && result.sport === "EPL"
      && JSON.stringify(estimated) === JSON.stringify(["away_win", "draw"])) {
    probabilities = result.probabilities || { home_win: result.home_win_probability,
      draw: result.draw_probability, away_win: result.away_win_probability };
    message = "Draw and away-win probabilities are estimates derived from a binary home/not-home model and historical draw frequency.";
  } else throw new Error(UNSUPPORTED);
  const expected = method === "direct_binary"
    ? (Object.hasOwn(probabilities || {}, "not_home_win") ? ["home_win", "not_home_win"] : ["home_win", "away_win"])
    : ["home_win", "draw", "away_win"];
  if (!probabilities || Object.keys(probabilities).length !== expected.length
      || expected.some((key) => typeof probabilities[key] !== "number" || !Number.isFinite(probabilities[key])
        || probabilities[key] < 0 || probabilities[key] > 1)
      || Math.abs(expected.reduce((sum, key) => sum + probabilities[key], 0) - 1) > 0.000001) throw new Error(UNSUPPORTED);
  const ordered = expected.map((key) => [key, probabilities[key]]);
  let winner = ordered.reduce((best, entry) => entry[1] > best[1] ? entry : best)[0];
  if (result.predicted_outcome) {
    const declared = { HOME_WIN: "home_win", NOT_HOME_WIN: "not_home_win" }[result.predicted_outcome] || result.predicted_outcome;
    if (!expected.includes(declared) || Math.abs(probabilities[declared] - Math.max(...ordered.map((entry) => entry[1]))) > 0.000001) throw new Error(UNSUPPORTED);
    winner = declared;
  }
  const home = result.home_team_name || "Home team";
  const away = result.away_team_name || "Away team";
  const headline = winner === "draw" ? "Draw predicted" : winner === "home_win"
    ? `${home} predicted to win` : winner === "not_home_win" ? `${home} predicted not to win` : `${away} predicted to win`;
  const labels = { home_win: "Home win", not_home_win: "Not home win", draw: "Draw", away_win: "Away win" };
  return { message, headline, confidence: Math.max(...ordered.map((entry) => entry[1])),
    probabilities: ordered.map(([key, value]) => ({ key, label: labels[key], value })),
    calibrationNote: "Probabilities are uncalibrated experimental outputs, not guaranteed results." };
}
