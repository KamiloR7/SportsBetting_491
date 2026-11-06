const STORAGE_KEY = "sportsbetting.prediction-history.v1";
const MAX_HISTORY_ITEMS = 25;

function readStoredHistory() {
  try {
    const value = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

export function getPredictionHistory() {
  return readStoredHistory();
}

export function savePredictionToHistory(prediction) {
  const entry = {
    ...prediction,
    saved_at: new Date().toISOString(),
  };

  try {
    const history = [entry, ...readStoredHistory()].slice(0, MAX_HISTORY_ITEMS);
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
    return history;
  } catch {
    return null;
  }
}
