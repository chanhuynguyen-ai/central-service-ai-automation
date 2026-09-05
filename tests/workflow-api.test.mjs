import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import ts from "typescript";

function loadApi(handler) {
  const source = readFileSync(new URL("../lib/workflow-api.ts", import.meta.url), "utf8");
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const compiledModule = { exports: {} };
  const requireApi = (name) => {
    assert.equal(name, "./api");
    return { apiRequest: handler };
  };
  new Function("require", "module", "exports", compiled)(requireApi, compiledModule, compiledModule.exports);
  return compiledModule.exports;
}

test("submission sends only the saved draft revision and access credential", async () => {
  const calls = [];
  const api = loadApi(async (...args) => { calls.push(args); return { id: 42 }; });
  assert.deepEqual(await api.submitDraft("test-access", 42, 7), { id: 42 });
  assert.deepEqual(calls, [["/workflows/requests/42/submit", {
    method: "POST", body: JSON.stringify({ revision: 7 }),
  }, "test-access"]]);
});

test("approval decisions carry task concurrency version, never a client approver ID", async () => {
  const calls = [];
  const api = loadApi(async (...args) => calls.push(args));
  await api.decideApprovalTask("test-access", { id: 17, version: 3 }, "request_changes", "Specify the cost center.");
  assert.equal(calls[0][0], "/workflows/approval-tasks/17/decisions");
  assert.deepEqual(JSON.parse(calls[0][1].body), {
    version: 3, decision: "request_changes", comment: "Specify the cost center.",
  });
  assert.equal(calls[0][2], "test-access");
});

test("pending/history inbox and submitted list use explicit pagination", async () => {
  const paths = [];
  const api = loadApi(async (path) => paths.push(path));
  await api.listSubmissions("token", 50);
  await api.listApprovalTasks("token", "history", 100);
  await api.getSubmission("token", 4);
  assert.deepEqual(paths, [
    "/workflows/requests?limit=50&offset=50",
    "/workflows/approval-tasks?status=history&limit=50&offset=100",
    "/workflows/requests/4",
  ]);
});

test("a failed or conflicting decision propagates rather than fabricating success", async () => {
  const error = new Error("409: task was already decided");
  const api = loadApi(async () => { throw error; });
  await assert.rejects(api.decideApprovalTask("token", { id: 17, version: 1 }, "approve", ""), error);
});
