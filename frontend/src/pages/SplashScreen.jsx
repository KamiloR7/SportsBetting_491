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

        <h1>ParIAI</h1>

        <p>AI Sports Match Predictions</p>

      </div>
    </div>
  );
}

export default SplashScreen;