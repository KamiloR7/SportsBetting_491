import { useState } from "react";

function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");

  function handleLogin(event) {
    event.preventDefault();
    setPassword("");
    setMessage("Login is not available yet. This prototype does not verify credentials or protect access to the dashboard.");
  }

  return (
    <div className="login-page">

      <div className="login-card">

        <h1>Welcome Back</h1>

        <p>Login prototype</p>

        <p role="status" aria-live="polite">{message}</p>

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

          <button type="submit">Continue</button>

        </form>

      </div>

    </div>
  );
}

export default Login;
