import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function source(path) {
  return readFile(new URL(`../${path}`, import.meta.url), "utf8");
}

test("frontend API exposes the complete auth lifecycle", async () => {
  const api = await source("lib/api.ts");
  assert.match(api, /refresh_token:\s*string/);
  assert.match(api, /function refreshSession/);
  assert.match(api, /function logoutSession/);
  assert.match(api, /function getCurrentUser/);
});

test("session helper stores normalized user roles", async () => {
  const auth = await source("lib/auth.ts");
  assert.match(auth, /centralops_access_token/);
  assert.match(auth, /centralops_refresh_token/);
  assert.match(auth, /userHasAnyRole/);
  assert.match(auth, /normalizeRole/);
});

test("workspace uses role-aware navigation and logout", async () => {
  const workspace = await source("app/workspace.tsx");
  assert.match(workspace, /visibleNav/);
  assert.match(workspace, /currentUser/);
  assert.match(workspace, /handleLogout/);
  assert.match(workspace, /userHasAnyRole/);
  assert.doesNotMatch(workspace, /Automation admin<\/p>/);
});
