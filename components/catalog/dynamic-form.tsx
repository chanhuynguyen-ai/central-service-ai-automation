"use client";

import type { FormEvent } from "react";
import type { DraftLookups, FieldIssue, FormData, FormField, FormSchema, FormValue } from "../../lib/catalog-api";

const control = "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 disabled:bg-slate-100";

export function DynamicForm({ schema, values, errors = [], lookups, disabled = false, onChange }: {
  schema: FormSchema; values: FormData; errors?: FieldIssue[]; lookups: DraftLookups;
  disabled?: boolean; onChange: (key: string, value: FormValue) => void;
}) {
  function renderField(field: FormField) {
    const value = values[field.key];
    const id = `field-${field.key}`;
    const issue = errors.find((item) => item.field === field.key);
    const common = { id, name: field.key, disabled, className: control,
      "aria-required": field.required, "aria-invalid": Boolean(issue),
      "aria-describedby": `${id}-hint${issue ? ` ${id}-error` : ""}` };
    const text = typeof value === "string" || typeof value === "number" ? String(value) : "";
    const changeText = (event: FormEvent<HTMLInputElement | HTMLTextAreaElement>) => onChange(field.key, event.currentTarget.value);
    let input;
    switch (field.type) {
      case "textarea":
        input = <textarea {...common} rows={4} maxLength={5000} value={text} placeholder={field.placeholder ?? ""} onChange={changeText} />;
        break;
      case "boolean":
        input = <select {...common} value={typeof value === "boolean" ? String(value) : ""} onChange={(event) => onChange(field.key, event.target.value === "" ? null : event.target.value === "true")}>
          <option value="">Choose an answer</option><option value="true">Yes</option><option value="false">No</option>
        </select>;
        break;
      case "select":
        input = <select {...common} value={text} onChange={(event) => onChange(field.key, event.target.value)}>
          <option value="">Choose an option</option>{field.options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>;
        break;
      case "multi_select":
        input = <select {...common} multiple size={Math.min(Math.max(field.options.length, 2), 6)} value={Array.isArray(value) ? value : []} onChange={(event) => onChange(field.key, Array.from(event.target.selectedOptions, (option) => option.value))}>
          {field.options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>;
        break;
      case "user_picker":
      case "department_picker": {
        const options = field.type === "user_picker" ? lookups.users : lookups.departments;
        input = <select {...common} value={text} onChange={(event) => onChange(field.key, event.target.value === "" ? null : Number(event.target.value))}>
          <option value="">Choose {field.type === "user_picker" ? "a person" : "a department"}</option>
          {options.map((option) => <option key={option.id} value={option.id}>{option.name}</option>)}
        </select>;
        break;
      }
      case "date_range": {
        const range = typeof value === "object" && value !== null && !Array.isArray(value) ? value : { start: "", end: "" };
        input = <div className="grid gap-3 sm:grid-cols-2">
          <label className="grid gap-1 text-xs" htmlFor={id}>Start date<input {...common} type="date" value={range.start} onChange={(event) => onChange(field.key, { ...range, start: event.target.value })} /></label>
          <label className="grid gap-1 text-xs" htmlFor={`${id}-end`}>End date<input {...common} id={`${id}-end`} type="date" value={range.end} onChange={(event) => onChange(field.key, { ...range, end: event.target.value })} /></label>
        </div>;
        break;
      }
      case "number":
        input = <input {...common} type="number" step="any" value={text} onChange={(event) => onChange(field.key, event.target.value === "" ? null : Number(event.target.value))} />;
        break;
      case "currency":
        input = <input {...common} type="text" inputMode="decimal" maxLength={16} value={text} placeholder="0.00" onChange={changeText} />;
        break;
      case "text":
      case "url":
      case "date":
        input = <input {...common} type={field.type === "date" ? "date" : field.type === "url" ? "url" : "text"} maxLength={field.type === "url" ? 2048 : 500} value={text} placeholder={field.placeholder ?? ""} onChange={changeText} />;
        break;
      case "attachment":
        input = <div id={id} className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-600"><button type="button" disabled className="font-medium">Upload unavailable</button><p className="mt-1">Secure attachments are planned in Phase 8. Do not paste private file links here.</p></div>;
        break;
      default:
        input = <p id={id} role="alert" className="text-sm text-rose-700">This field type is not supported. Ask an administrator to update the form.</p>;
    }
    return <div key={field.key} className="grid gap-2">
      <label htmlFor={id} className="text-sm font-medium text-slate-800">{field.label}{field.required ? <span className="ml-1 text-rose-600" aria-label="required">*</span> : null}</label>
      {input}
      <p id={`${id}-hint`} className="text-xs text-slate-500">{field.helper_text ?? (field.type === "currency" ? "Enter a decimal amount without grouping separators; stored without floating-point rounding." : field.type === "multi_select" ? "Hold Ctrl or Command to select multiple options." : "")}</p>
      {issue ? <p id={`${id}-error`} role="alert" className="text-xs text-rose-700">{issue.message}</p> : null}
    </div>;
  }
  return <div className="space-y-6">{schema.sections.map((section, index) => <fieldset key={index} disabled={disabled} className="space-y-4 rounded-xl border border-slate-200 p-4">
    <legend className="px-1 text-base font-semibold text-slate-900">{section.title}</legend>
    {section.description ? <p className="text-sm text-slate-500">{section.description}</p> : null}
    {section.fields.map(renderField)}
  </fieldset>)}</div>;
}
