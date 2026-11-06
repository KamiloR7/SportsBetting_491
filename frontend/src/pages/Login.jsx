
import { useState } from "react";

function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");

  function handleLogin(event) {
    event.preventDefault();

    // Sprint 4: Frontend login is still a prototype.
    // Real backend authentication integration will be added later.
    // Never log or store the user's password.

    setPassword("");
    setMessage(
      "Login is not available yet. This prototype does not verify credentials or protect access to the dashboard."
    );
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

        <p role="status" aria-live="polite">
          {message}
        </p>

        <form onSubmit={handleLogin}>
          <label htmlFor="login-email">Email</label>
          <input
            id="login-email"
            type="email"
            placeholder="Enter email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />

          <label htmlFor="login-password">Password</label>
          <input
            id="login-password"
            type="password"
            placeholder="Enter password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />

          <button type="submit">Continue</button>

        </form>
      </div>
    </div>
  );
}

export default Login;
