import { useEffect, useState } from "react";
import { apiRequest } from "../services/api";

function DemoNotice() {
  const [isDemo, setIsDemo] = useState(false);

  useEffect(() => {
    let active = true;
    apiRequest("/health")
      .then((health) => {
        if (active) setIsDemo(health.data_mode === "synthetic_demo");
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  if (!isDemo) return null;
  return <p className="demo-notice">Synthetic demo: sample matches and predictions</p>;
}

export default DemoNotice;
