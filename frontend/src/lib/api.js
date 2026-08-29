import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: false,
});

// Attach token from localStorage as fallback
api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem("nugvio_token");
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

export const LOGO_URL =
  "https://customer-assets.emergentagent.com/job_finpilot-preview-7/artifacts/fhhbnuvo_Screenshot%202026-07-15%20164528.png";
