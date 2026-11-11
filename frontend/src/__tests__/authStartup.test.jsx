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
  if (user === false) return <Navigate to="/login" replace />;
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
            <Route path="/login" element={<div>LOGIN PAGE</div>} />
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
  api.get.mockResolvedValueOnce({ data: { id: "1", name: "R", email: "r@x.in" } });
  await renderApp();
  expect(text()).toContain("DASHBOARD");
});

test("401 (missing/expired token) redirects to login and clears the stale token", async () => {
  localStorage.setItem("nugvio_token", "stale");
  api.get.mockRejectedValueOnce(httpErr(401));
  await renderApp();
  expect(text()).toContain("LOGIN PAGE");
  expect(localStorage.getItem("nugvio_token")).toBeNull();
});

test("network error shows a message and Retry, and Retry recovers", async () => {
  api.get.mockRejectedValueOnce(new Error("Network Error"));
  await renderApp();
  expect(text()).toContain("Couldn't reach the NugVio server");
  expect(text()).not.toContain("Loading…");
  api.get.mockResolvedValueOnce({ data: { id: "1", name: "R" } });
  await act(async () => { container.querySelector("button").click(); });
  expect(text()).toContain("DASHBOARD");
});

test("5xx shows an error, not the login page", async () => {
  api.get.mockRejectedValueOnce(httpErr(503));
  await renderApp();
  expect(text()).toContain("(503)");
});

test("timeout is classified as a retryable error", () => {
  expect(classifyAuthError({ code: "ECONNABORTED" }).kind).toBe("error");
  expect(classifyAuthError(httpErr(403)).kind).toBe("unauthenticated");
});

test("/auth/me is called with a finite timeout", async () => {
  api.get.mockResolvedValueOnce({ data: { id: "1" } });
  await renderApp();
  expect(api.get).toHaveBeenCalledWith("/auth/me", expect.objectContaining({ timeout: expect.any(Number) }));
});

test("401 during the session (unauthorized event) logs the user out to /login", async () => {
  api.get.mockResolvedValueOnce({ data: { id: "1" } });
  await renderApp();
  expect(text()).toContain("DASHBOARD");
  await act(async () => { window.dispatchEvent(new Event("nugvio:unauthorized")); });
  expect(text()).toContain("LOGIN PAGE");
});
