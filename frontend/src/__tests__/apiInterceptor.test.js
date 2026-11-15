/** A 401 from a data endpoint ends the session; a 401 from login does not. */
import { api, UNAUTHORIZED_EVENT } from "@/lib/api";

const respondWith = (status) => (config) =>
  Promise.reject(Object.assign(new Error(`HTTP ${status}`), { config, response: { status, config } }));

let fired;
const onEvt = () => { fired += 1; };
beforeEach(() => { fired = 0; localStorage.setItem("nugvio_token", "tok"); window.addEventListener(UNAUTHORIZED_EVENT, onEvt); });
afterEach(() => window.removeEventListener(UNAUTHORIZED_EVENT, onEvt));

test("attaches the Bearer token", async () => {
  let seen;
  await api.get("/expenses", { adapter: async (c) => { seen = c.headers.Authorization; return { data: {}, status: 200, headers: {}, config: c }; } });
  expect(seen).toBe("Bearer tok");
});

test("401 on a protected endpoint clears token and fires unauthorized", async () => {
  await expect(api.get("/expenses", { adapter: respondWith(401) })).rejects.toThrow();
  expect(localStorage.getItem("nugvio_token")).toBeNull();
  expect(fired).toBe(1);
});

test("401 on login (bad password) is left to the login form", async () => {
  await expect(api.post("/auth/login", {}, { adapter: respondWith(401) })).rejects.toThrow();
  expect(localStorage.getItem("nugvio_token")).toBe("tok");
  expect(fired).toBe(0);
});

test("500 does not log the user out", async () => {
  await expect(api.get("/expenses", { adapter: respondWith(500) })).rejects.toThrow();
  expect(localStorage.getItem("nugvio_token")).toBe("tok");
  expect(fired).toBe(0);
});

test("a late 401 for a request sent before login does not log the new session out", async () => {
  localStorage.removeItem("nugvio_token");
  let rejectLate;
  const pending = api.get("/auth/me", { adapter: (config) => new Promise((_, rej) => { rejectLate = () => rej(Object.assign(new Error("401"), { config, response: { status: 401, config } })); }) });
  await new Promise((r) => setTimeout(r, 0)); // request is in flight, sent with no token
  localStorage.setItem("nugvio_token", "fresh"); // user logs in meanwhile
  rejectLate();
  await expect(pending).rejects.toThrow();
  expect(localStorage.getItem("nugvio_token")).toBe("fresh");
  expect(fired).toBe(0);
});

test("401 with no token at all (cookie session ended) still fires unauthorized", async () => {
  localStorage.removeItem("nugvio_token");
  await expect(api.get("/expenses", { adapter: respondWith(401) })).rejects.toThrow();
  expect(fired).toBe(1);
});
