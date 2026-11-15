/**
 * Startup auth behaviour: /app must always resolve — dashboard, login redirect,
 * or an error with Retry — never an endless "Loading…".
 */
import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Routes, Route, Navigate } from "react-router-dom";

jest.mock("@/lib/api", () => {
  const api = { get: jest.fn(), post: jest.fn() };
  return { api, TOKEN_KEY: "nugvio_token", UNAUTHORIZED_EVENT: "nugvio:unauthorized" };
});

const { api } = require("@/lib/api");
const { AuthProvider, useAuth, classifyAuthError } = require("@/lib/auth");

// Mirrors App.js Protected (kept in sync with the real component's three states).
function Protected({ children }) {
  const { user, authError, refresh } = useAuth();
  if (user === null && authError) return <div><p>{authError}</p><button onClick={refresh}>Retry</button></div>;
  if (user === null) return <div>Loading…</div>;
  if (user === false) return <Navigate to="/" replace />;
  return children;
}

let container, root;
beforeEach(() => {
  container = document.createElement("div"); document.body.appendChild(container);
  root = createRoot(container); localStorage.clear(); jest.clearAllMocks();
  global.IS_REACT_ACT_ENVIRONMENT = true;
});
afterEach(() => { act(() => root.unmount()); container.remove(); });

async function renderApp() {
  await act(async () => {
    root.render(
      <AuthProvider>
        <MemoryRouter initialEntries={["/app"]}>
          <Routes>
            <Route path="/" element={<div>HOME PAGE</div>} />
            <Route path="/app" element={<Protected><div>DASHBOARD</div></Protected>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );
  });
}
const text = () => container.textContent;
const httpErr = (status) => Object.assign(new Error("x"), { response: { status } });

test("valid session loads the dashboard", async () => {
  localStorage.setItem("nugvio_token", "tok");
  api.get.mockResolvedValueOnce({ data: { id: "1", name: "R", email: "r@x.in" } });
  await renderApp();
  expect(text()).toContain("DASHBOARD");
});

test("401 (missing/expired token) redirects to home and clears the stale token", async () => {
  localStorage.setItem("nugvio_token", "stale");
  api.get.mockRejectedValueOnce(httpErr(401));
  await renderApp();
  expect(text()).toContain("HOME PAGE");
  expect(localStorage.getItem("nugvio_token")).toBeNull();
});

test("network error shows a message and Retry, and Retry recovers", async () => {
  localStorage.setItem("nugvio_token", "tok");
  api.get.mockRejectedValueOnce(new Error("Network Error"));
  await renderApp();
  expect(text()).toContain("Couldn't reach the NugVio server");
  expect(text()).not.toContain("Loading…");
  api.get.mockResolvedValueOnce({ data: { id: "1", name: "R" } });
  await act(async () => { container.querySelector("button").click(); });
  expect(text()).toContain("DASHBOARD");
});

test("5xx shows an error, not the login page", async () => {
  localStorage.setItem("nugvio_token", "tok");
  api.get.mockRejectedValueOnce(httpErr(503));
  await renderApp();
  expect(text()).toContain("(503)");
});

test("timeout is classified as a retryable error", () => {
  expect(classifyAuthError({ code: "ECONNABORTED" }).kind).toBe("error");
  expect(classifyAuthError(httpErr(403)).kind).toBe("unauthenticated");
});

test("/auth/me is called with a finite timeout", async () => {
  localStorage.setItem("nugvio_token", "tok");
  api.get.mockResolvedValueOnce({ data: { id: "1" } });
  await renderApp();
  expect(api.get).toHaveBeenCalledWith("/auth/me", expect.objectContaining({ timeout: expect.any(Number) }));
});

test("401 during the session (unauthorized event) logs the user out to the home page", async () => {
  localStorage.setItem("nugvio_token", "tok");
  api.get.mockResolvedValueOnce({ data: { id: "1" } });
  await renderApp();
  expect(text()).toContain("DASHBOARD");
  await act(async () => { window.dispatchEvent(new Event("nugvio:unauthorized")); });
  expect(text()).toContain("HOME PAGE");
});

test("no saved session: home page shows instantly, without waiting for the server", async () => {
  api.get.mockReturnValueOnce(new Promise(() => {})); // sleeping backend: never answers
  await renderApp();
  expect(text()).toContain("HOME PAGE");
  expect(text()).not.toContain("Loading…");
});

test("no saved session: a failed background check shows no error", async () => {
  api.get.mockRejectedValueOnce(new Error("Network Error"));
  await renderApp();
  expect(text()).toContain("HOME PAGE");
});

test("cookie-only session (Google sign-in hint) still waits and loads the dashboard", async () => {
  localStorage.setItem("nugvio_has_session", "1");
  api.get.mockResolvedValueOnce({ data: { id: "1", name: "G" } });
  await renderApp();
  expect(text()).toContain("DASHBOARD");
});

test("background 401 cannot undo a login made while it was in flight", async () => {
  let rejectMe; api.get.mockReturnValueOnce(new Promise((_, rej) => { rejectMe = rej; }));
  let auth; const Grab = () => { auth = useAuth(); return null; };
  await act(async () => { root.render(<AuthProvider><Grab /></AuthProvider>); });
  api.post.mockResolvedValueOnce({ data: { id: "1", token: "newtok" } });
  await act(async () => { await auth.login("a@b.in", "pw"); });
  await act(async () => { rejectMe(httpErr(401)); });
  expect(auth.user).toEqual({ id: "1", token: "newtok" });
  expect(localStorage.getItem("nugvio_token")).toBe("newtok");
});

test("logout clears the session hint", async () => {
  localStorage.setItem("nugvio_token", "tok");
  api.get.mockResolvedValueOnce({ data: { id: "1" } });
  let auth; const Grab = () => { auth = useAuth(); return null; };
  await act(async () => { root.render(<AuthProvider><Grab /></AuthProvider>); });
  expect(localStorage.getItem("nugvio_has_session")).toBe("1");
  api.post.mockResolvedValueOnce({});
  await act(async () => { await auth.logout(); });
  expect(localStorage.getItem("nugvio_has_session")).toBeNull();
  expect(auth.user).toBe(false);
});
