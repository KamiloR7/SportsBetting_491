import { useState } from "react";

function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");

  function handleLogin(event) {
    event.preventDefault();
    setPassword("");
    setMessage(
      "Sign-in is unavailable in this prototype. The dashboard is public; your password was cleared and was not sent."
    );
  }

  return (
    <div className="login-page">

      <div className="login-card">

        <h1>Welcome Back</h1>

        <p>Sign in to view today's matches</p>

        <form onSubmit={handleLogin}>

          <label htmlFor="login-email">Email</label>

          <input
            id="login-email"
            type="email"
            placeholder="Enter email"
            autoComplete="username"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />

          <label htmlFor="login-password">Password</label>

          <input
            id="login-password"
            type="password"
            placeholder="Enter password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />

          <button type="submit">
            Login
          </button>

        </form>

        {message && <p role="status">{message}</p>}

      </div>

    </div>
  );
}

export default Login;
