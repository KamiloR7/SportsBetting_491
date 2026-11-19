import { BrowserRouter, Routes, Route } from "react-router-dom";

import SplashScreen from "./pages/SplashScreen";
import Login from "./pages/Login";
import Dashboard from "./pages/DashBoard";
import MatchDetails from "./pages/MatchDetails";
import ModelInsightsPage from "./pages/ModelInsightsPage";
import AccountPage from "./pages/AccountPage";
import StandingsPage from "./pages/StandingsPage";
import ParlayBuilder from "./pages/ParlayBuilder";

import "./App.css";
import "./background.css";
import "./ml-insights.css";
import AppFrame from "./components/AppFrame";

function App() {
  return (
    <BrowserRouter>
      <AppFrame><Routes>
        <Route path="/" element={<SplashScreen />} />
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/matches/:id" element={<MatchDetails />} />
        <Route path="/standings" element={<StandingsPage />} />
        <Route path="/insights" element={<ModelInsightsPage />} />
        <Route path="/parlay" element={<ParlayBuilder />} />
        <Route path="/bets/active" element={<AccountPage key="active" tab="active" />} />
        <Route path="/bets/history" element={<AccountPage key="history" tab="history" />} />
        <Route path="/wallet" element={<AccountPage key="wallet" tab="wallet" />} />
      </Routes></AppFrame>
    </BrowserRouter>
  );
}

export default App;