import { useState } from "react";

function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");

  function handleLogin(event) {
    event.preventDefault();

    // No authenticated login endpoint is available yet. Do not log credentials
    // or imply that this form established an authenticated session.
    setEmail("");
    setPassword("");
    setMessage(
      "Sign-in is unavailable. This prototype does not authenticate accounts. Your credentials were not sent or saved."
    );
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>Welcome Back</h1>
        <p>Login prototype</p>

        <form onSubmit={handleLogin}>
          <label htmlFor="login-email">Email</label>
          <input
            id="login-email"
            type="email"
            placeholder="Enter email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />

          <label htmlFor="login-password">Password</label>
          <input
            id="login-password"
            type="password"
            placeholder="Enter password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />

          <button type="submit">Continue</button>
          <p role="status" aria-live="polite">{message}</p>
        </form>
      </div>
    </div>
  );
}

export default Login;
