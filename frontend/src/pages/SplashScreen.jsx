import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

function SplashScreen() {
  const navigate = useNavigate();

  useEffect(() => {
    const timer = setTimeout(() => {
      navigate("/login");
    }, 2500);

    return () => clearTimeout(timer);
  }, [navigate]);

  return (
    <div className="splash-screen">
      <div className="logo-container">

        <h1>Vigor</h1>
        <img src="/your-logo.png" alt="Vigor Logo" />

        <p>Bet Smarter. Play the Odds.</p>

      </div>
    </div>
  );
}

export default SplashScreen;