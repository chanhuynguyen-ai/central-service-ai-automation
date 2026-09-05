import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

function compile(file, requireValue) {
  const output = ts.transpileModule(readFileSync(new URL(file, import.meta.url), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const compiledModule = { exports: {} };
  new Function("require", "module", "exports", output)(requireValue, compiledModule, compiledModule.exports);
  return compiledModule.exports;
}
const api = (handler) => compile("../lib/activity-api.ts", (name) => { assert.equal(name, "./api"); return { apiRequest: handler }; });
const ui = () => compile("../components/activity/request-activity.tsx", (name) => {
  if (name === "react") return React;
  if (name === "react/jsx-runtime") return { jsx: (type, props, key) => React.createElement(type, { ...props, key }), jsxs: (type, props, key) => React.createElement(type, { ...props, key }) };
  assert.equal(name, "../../lib/activity-api"); return {};
});

test("public and internal comments use explicit audience and keyset pagination", async () => {
  const calls = [];
  const client = api(async (...args) => calls.push(args));
  await client.getActivityPermissions("token", 8);
  await client.getRequestComments("token", 8, "REQUESTER_VISIBLE");
  await client.getRequestComments("token", 8, "INTERNAL", 42);
  await client.getRequestTimeline("token", 8, 20);
  assert.deepEqual(calls.map((call) => call[0]), [
    "/activity/requests/8/permissions",
    "/activity/requests/8/comments?visibility=REQUESTER_VISIBLE&limit=30",
    "/activity/requests/8/comments?visibility=INTERNAL&limit=30&before_id=42",
    "/activity/requests/8/timeline?limit=30&before_id=20",
  ]);
  assert.ok(calls.every((call) => call[2] === "token"));
});

test("comment writes send an idempotency key but no actor or status", async () => {
  const calls = [];
  const client = api(async (...args) => calls.push(args));
  await client.postRequestComment("token", 8, "A comment", "INTERNAL", "idempotency-key");
  assert.deepEqual(calls, [["/activity/requests/8/comments", { method: "POST", body: JSON.stringify({ body: "A comment", visibility: "INTERNAL", client_token: "idempotency-key" }) }, "token"]]);
});

test("audit filter arguments are encoded and cursor is retained", async () => {
  const calls = [];
  const client = api(async (path) => calls.push(path));
  await client.getAuditEvents("token", { eventType: "approval_decided", requestId: 8 }, 30);
  const url = new URL(calls[0], "http://localhost");
  assert.equal(url.pathname, "/audit/events");
  assert.equal(url.searchParams.get("event_type"), "approval_decided");
  assert.equal(url.searchParams.get("request_id"), "8");
  assert.equal(url.searchParams.get("before_id"), "30");
  assert.equal(url.searchParams.get("limit"), "30");
});

test("authorization and conflict failures are propagated without synthetic success", async () => {
  const denied = new Error("403 Forbidden");
  const client = api(async () => { throw denied; });
  await assert.rejects(client.postRequestComment("token", 8, "note", "INTERNAL", "key"), denied);
  await assert.rejects(client.getAuditEvents("token"), denied);
});

test("actual comment renderer escapes HTML and preserves whitespace as plain text", () => {
  const { CommentList } = ui();
  const html = renderToStaticMarkup(React.createElement(CommentList, { items: [{
    id: 1, request_id: 8, author_user_id: 2, author_name: "<script>author()</script>",
    body: '<img src=x onerror="alert(1)">\nNext line', visibility: "REQUESTER_VISIBLE", created_at: "2026-01-01T00:00:00Z",
  }] }));
  assert.doesNotMatch(html, /<img|<script/);
  assert.match(html, /&lt;img/);
  assert.match(html, /&lt;script/);
  assert.match(html, /whitespace-pre-wrap/);
  assert.match(html, /Next line/);
});

test("timeline uses explicit event labels without rendering arbitrary payload values", () => {
  const { ActivityTimeline } = ui();
  const html = renderToStaticMarkup(React.createElement(ActivityTimeline, { items: [{
    id: 1, request_id: 8, actor_id: 2, actor_name: "Manager", event_type: "INTERNAL_NOTE_ADDED",
    visibility: "INTERNAL", payload: { attempt: 2, backfilled: true, unsafe: "SECRET" }, created_at: "2026-01-01T00:00:00Z",
  }] }));
  assert.match(html, /Internal note added/);
  assert.match(html, /Imported from an existing audit record/);
  assert.match(html, /Attempt 2/);
  assert.doesNotMatch(html, /SECRET/);
});
