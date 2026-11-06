import test from "node:test";
import assert from "node:assert/strict";
import { predictionDisplay } from "./predictionTransparency.js";

function response(method, estimated, probabilities) {
  return { sport: "EPL", probability_method: method, estimated_outcomes: estimated,
    probability_calibration: "uncalibrated", probabilities };
}

test("estimated EPL draw and away probabilities are disclosed", () => {
  const display = predictionDisplay(response("estimated_epl_split", ["draw", "away_win"],
    { home_win: 0.4, draw: 0.2, away_win: 0.4 }));
  assert.match(display.message, /Draw and away-win probabilities are estimates/);
  assert.match(display.calibrationNote, /uncalibrated/);
  assert.deepEqual(display.probabilities.map((entry) => entry.key), ["home_win", "draw", "away_win"]);
});

test("direct EPL outputs are not labeled heuristic estimates", () => {
  const display = predictionDisplay(response("direct_multiclass", [], { home_win: 0.3, draw: 0.5, away_win: 0.2 }));
  assert.match(display.message, /Direct three-class/);
  assert.doesNotMatch(display.message, /estimate|heuristic/);
  assert.equal(display.headline, "Draw predicted");
});

test("binary EPL does not invent separate draw and away probabilities", () => {
  const display = predictionDisplay(response("direct_binary", [], { home_win: 0.4, not_home_win: 0.6 }));
  assert.match(display.message, /not separately modeled/);
});

test("legacy flattened estimated output is disclosed", () => {
  const data = response("estimated_epl_split", ["draw", "away_win"]);
  Object.assign(data, { home_win_probability: 0.4, draw_probability: 0.3, away_win_probability: 0.3 });
  assert.match(predictionDisplay(data).message, /estimates/);
});

test("binary NFL and MLB are supported", () => {
  for (const sport of ["NFL", "MLB"]) {
    const data = { ...response("direct_binary", [], { home_win: 0.4, away_win: 0.6 }), sport };
    assert.match(predictionDisplay(data).headline, /Away team/);
  }
});

test("unsupported or inconsistent disclosures fail clearly", () => {
  for (const data of [response("unknown", [], { home_win: 0.5, away_win: 0.5 }),
    response("direct_multiclass", ["draw"], { home_win: 0.3, draw: 0.4, away_win: 0.3 }),
    response("estimated_epl_split", [], { home_win: 0.3, draw: 0.4, away_win: 0.3 }),
    { ...response("direct_multiclass", [], { home_win: 0.3, draw: 0.4, away_win: 0.3 }), sport: "NFL" },
    { ...response("direct_binary", [], { home_win: 0.3, not_home_win: 0.7 }), probability_calibration: "calibrated" },
    { sport: "EPL", probabilities: { home_win: 0.3, not_home_win: 0.7 } },
  ]) assert.throws(() => predictionDisplay(data), /Unsupported or undisclosed/);
});

test("invalid probability distributions are never displayed", () => {
  for (const probabilities of [{ home_win: 0.5, draw: 0.5, away_win: 0.5 },
    { home_win: NaN, draw: 0.5, away_win: 0.5 }, { home_win: Infinity, draw: 0, away_win: 0 },
    { home_win: -0.2, draw: 0.6, away_win: 0.6 }, { home_win: 0.5, draw: 0.5 },
    { home_win: "0.4", draw: 0.2, away_win: 0.4 },
  ]) assert.throws(() => predictionDisplay(response("direct_multiclass", [], probabilities)), /Unsupported or undisclosed/);
});

test("backend outcome is honored on probability ties and contradictions fail", () => {
  const data = response("direct_binary", [], { home_win: 0.5, not_home_win: 0.5 });
  data.predicted_outcome = "NOT_HOME_WIN";
  assert.match(predictionDisplay(data).headline, /not to win/);
  data.probabilities = { home_win: 0.9, not_home_win: 0.1 };
  assert.throws(() => predictionDisplay(data), /Unsupported or undisclosed/);
});
