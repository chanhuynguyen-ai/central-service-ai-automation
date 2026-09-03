import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));

async function renderHome() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  const response = await worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
  return { response, html: await response.text() };
}

async function readCssTree(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const values = await Promise.all(entries.map(async (entry) => {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) return readCssTree(entryPath);
    return entry.name.endsWith(".css") ? readFile(entryPath, "utf8") : "";
  }));
  return values.join("\n");
}

test("renders the CentralOps product workspace", async () => {
  const { response, html } = await renderHome();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  assert.match(html, /<title>CentralOps AI \| Service Automation<\/title>/);
  assert.match(html, /Service operations overview/);
  assert.match(html, /Responsible AI/);
  assert.match(html, /New request/);
  assert.doesNotMatch(html, /Starter Project/);
});

test("emits the product theme and reduced-motion support", async () => {
  const css = await readCssTree(path.join(root, "dist"));
  assert.match(css, /--background:\s*#f4f7fb/);
  assert.match(css, /--sidebar:\s*#071426/);
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
});
