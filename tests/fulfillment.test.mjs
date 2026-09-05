import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import ts from "typescript";

function api(handler) {
  const source = readFileSync(new URL("../lib/fulfillment-api.ts", import.meta.url), "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const compiledModule = { exports: {} };
  new Function("require", "module", "exports", output)(
    (name) => {
      assert.equal(name, "./api");
      return { apiRequest: handler };
    },
    compiledModule,
    compiledModule.exports,
  );
  return compiledModule.exports;
}

test("fulfillment queue sends explicit server-side scope and filters", async () => {
  const calls = [];
  const client = api(async (...args) => calls.push(args));
  await client.listWorkItems("token", "mine", "IN_PROGRESS", 50);
  const [path, options, token] = calls[0];
  const url = new URL(path, "http://localhost");
  assert.equal(url.pathname, "/fulfillment/work-items");
  assert.equal(url.searchParams.get("scope"), "mine");
  assert.equal(url.searchParams.get("status"), "IN_PROGRESS");
  assert.equal(url.searchParams.get("offset"), "50");
  assert.deepEqual(options, {});
  assert.equal(token, "token");
});

test("work actions send only optimistic version and permitted action data", async () => {
  const calls = [];
  const client = api(async (...args) => calls.push(args));
  await client.actOnWorkItem("token", { id: 7, version: 4 }, "resolve", { note: "Laptop replaced" });
  assert.equal(calls[0][0], "/fulfillment/work-items/7/actions");
  assert.equal(calls[0][2], "token");
  const payload = JSON.parse(calls[0][1].body);
  assert.deepEqual(payload, {
    action: "resolve",
    version: 4,
    assignee_user_id: undefined,
    note: "Laptop replaced",
  });
  assert.equal(calls[0][1].method, "POST");
  assert.equal("status" in payload, false);
  assert.equal("request_id" in payload, false);
  assert.equal("actor_user_id" in payload, false);
});

test("API authorization/conflict errors remain failures", async () => {
  const denied = new Error("403 Forbidden");
  const client = api(async () => { throw denied; });
  await assert.rejects(client.listWorkItems("token", "team"), denied);
  await assert.rejects(client.actOnWorkItem("token", { id: 2, version: 1 }, "start"), denied);
});

test("service queue UI exposes governed lifecycle labels and no approval action", () => {
  const source = readFileSync(new URL("../components/fulfillment/service-queue.tsx", import.meta.url), "utf8");
  for (const expected of ["Claim work", "Wait for requester", "resolve", "close", "Assigned to me"]) {
    assert.match(source, new RegExp(expected, "i"));
  }
  assert.doesNotMatch(source, /approve request/i);
});
