import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const source = (file) => readFile(path.join(root, file), "utf8");

test("notification API exposes list and read operations", async () => {
  const api = await source("lib/notification-api.ts");
  assert.match(api, /\/notifications\?unread_only=/);
  assert.match(api, /\/notifications\/\$\{notificationId\}\/read/);
  assert.match(api, /\/notifications\/read-all/);
});

test("notification center polls without making business actions", async () => {
  const center = await source("components/notifications/notification-center.tsx");
  assert.match(center, /setInterval/);
  assert.match(center, /30000/);
  assert.match(center, /markNotificationRead/);
  assert.match(center, /Mark all read/);
  assert.doesNotMatch(center, /approval-tasks|fulfillment\/work-items/);
});

test("workspace replaces the static notification placeholder", async () => {
  const workspace = await source("app/workspace.tsx");
  assert.match(workspace, /NotificationCenter/);
  assert.match(workspace, /request=\{withSessionRefresh\}/);
});
