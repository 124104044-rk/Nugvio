import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const TOKEN_KEY = "nugvio_token";
// Fired when the backend rejects our credentials (expired/invalid/missing token).
export const UNAUTHORIZED_EVENT = "nugvio:unauthorized";

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

// Attach token from localStorage as fallback
api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem(TOKEN_KEY);
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

// Endpoints where a 401 means "wrong credentials / failed exchange", which the
// calling screen already handles itself — these must not trigger a global logout.
const CREDENTIAL_ENDPOINTS = ["/auth/login", "/auth/register", "/auth/google/session", "/auth/logout"];

// A 401 on any other call means the session is gone (e.g. token expired mid-use):
// drop the stale token and tell AuthProvider so the user is sent to /login.
api.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error?.response?.status;
    const url = error?.config?.url || "";
    // Ignore a 401 for a request that was sent with different credentials than the
    // ones stored now (e.g. a logged-out startup check that returns after the user
    // has just logged in on a slow, waking server). It says nothing about this session.
    const current = localStorage.getItem(TOKEN_KEY);
    const sent = String(error?.config?.headers?.Authorization || "");
    const stale = !!current && sent !== `Bearer ${current}`;
    if (status === 401 && !stale && !CREDENTIAL_ENDPOINTS.some((p) => url.includes(p))) {
      localStorage.removeItem(TOKEN_KEY);
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    }
    return Promise.reject(error);
  }
);

export const LOGO_URL =
  "https://customer-assets.emergentagent.com/job_finpilot-preview-7/artifacts/fhhbnuvo_Screenshot%202026-07-15%20164528.png";
