import { useState } from "react";
import { useNavigate } from "react-router-dom";

function Login() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function handleLogin(event) {
    event.preventDefault();

    // Temporary Sprint 1 behavior
    // Later this will call the real backend

    console.log("Login:", email, password);

    navigate("/dashboard");
  }

  return (
    <div className="login-page">

      <div className="login-card">

        <h1>Welcome Back</h1>

        <p>Sign in to view today's matches</p>

        <form onSubmit={handleLogin}>

          <label>Email</label>

          <input
            type="email"
            placeholder="Enter email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />

          <label>Password</label>

          <input
            type="password"
            placeholder="Enter password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />

          <button type="submit">
            Login
          </button>

        </form>

      </div>

    </div>
  );
}

export default Login;