import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import ts from "typescript";
import { renderToStaticMarkup } from "react-dom/server";

// Execute the actual pure TSX renderer, not a source-text regex contract.
// Type-only API imports are erased; runtime imports are React's JSX runtime.
const require = createRequire(import.meta.url);
const source = readFileSync(new URL("../components/catalog/dynamic-form.tsx", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
}).outputText;
const compiledModule = { exports: {} };
new Function("require", "module", "exports", compiled)(require, compiledModule, compiledModule.exports);
const { DynamicForm } = compiledModule.exports;

function render(kind, value, extra = {}) {
  const changes = [];
  const element = DynamicForm({
    schema: { sections: [{ title: "Details", fields: [{ key: "value", label: "A field", type: kind, required: true, options: [], ...extra }] }] },
    values: { value }, lookups: { users: [{ id: 3, name: "Employee" }], departments: [{ id: 4, name: "IT" }] },
    errors: [], onChange: (key, next) => changes.push([key, next]),
  });
  return { element, changes, html: renderToStaticMarkup(element) };
}
function find(element, predicate) {
  if (Array.isArray(element)) {
    for (const item of element) { const match = find(item, predicate); if (match) return match; }
  } else if (element && typeof element === "object") {
    if (predicate(element)) return element;
    return find(element.props?.children, predicate);
  }
  return null;
}

test("required boolean false is selected and false/empty remain different values", () => {
  const { element, html, changes } = render("boolean", false);
  assert.match(html, /value="false" selected=""/);
  const control = find(element, (node) => node.type === "select");
  control.props.onChange({ target: { value: "false" } });
  control.props.onChange({ target: { value: "" } });
  assert.deepEqual(changes, [["value", false], ["value", null]]);
});

test("numeric zero is displayed and never treated as a missing value", () => {
  const { element, html, changes } = render("number", 0);
  assert.match(html, /value="0"/);
  find(element, (node) => node.type === "input").props.onChange({ target: { value: "0" } });
  assert.deepEqual(changes, [["value", 0]]);
});

test("currency inputs keep decimal strings instead of converting to floating point", () => {
  const { element, changes } = render("currency", "123456789012.10");
  const control = find(element, (node) => node.type === "input");
  assert.equal(control.props.type, "text");
  control.props.onChange({ currentTarget: { value: "123456789012.10" } });
  assert.deepEqual(changes, [["value", "123456789012.10"]]);
});

test("multi-select and person picker emit typed values", () => {
  const options = [{ value: "a", label: "A" }, { value: "b", label: "B" }];
  const multiple = render("multi_select", ["a"], { options });
  find(multiple.element, (node) => node.type === "select").props.onChange({ target: { selectedOptions: [{ value: "b" }] } });
  assert.deepEqual(multiple.changes, [["value", ["b"]]]);
  const picker = render("user_picker", null);
  find(picker.element, (node) => node.type === "select").props.onChange({ target: { value: "3" } });
  assert.deepEqual(picker.changes, [["value", 3]]);
});

test("date range updates preserve the other endpoint", () => {
  const result = render("date_range", { start: "2026-09-01", end: "2026-09-30" });
  find(result.element, (node) => node.props?.id === "field-value-end" && node.type === "input")
    .props.onChange({ target: { value: "2026-10-01" } });
  assert.deepEqual(result.changes, [["value", { start: "2026-09-01", end: "2026-10-01" }]]);
});

test("schema content is escaped and unsupported attachment upload is explicitly disabled", () => {
  const { html } = render("text", "<script>unsafe()</script>", { label: "<img src=x>" });
  assert.doesNotMatch(html, /<script>|<img src=x>/);
  assert.match(html, /&lt;img/);
  const attachment = render("attachment", null);
  assert.match(attachment.html, /Upload unavailable/);
  assert.equal(find(attachment.element, (node) => node.type === "button").props.disabled, true);
});
