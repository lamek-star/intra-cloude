"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import {
  api,
  ApiError,
  type AppDefinition,
  type AppFieldDataType,
  type AppRelationshipKind,
  type AppTemplate,
  type AppTemplateVersion,
  type DraftConstraint,
  type DraftField,
  type DraftModel,
  type DraftRelationship,
  type FieldDefaultValue,
  type Organization,
  type Paginated,
} from "@/lib/api";
import {
  Badge,
  Button,
  Card,
  Checkbox,
  ErrorBanner,
  Input,
  Label,
  Modal,
  PageHeader,
  PageLoading,
  Select,
  Textarea,
} from "@/components/ui";
import { useConfirm } from "@/components/ConfirmProvider";

const DATA_TYPES: AppFieldDataType[] = ["text", "integer", "decimal", "boolean", "date", "datetime"];
const KEY_PATTERN = "[a-z][a-z0-9_]*";

export default function AppTemplateClient({ templateId }: { templateId: string }) {
  const [template, setTemplate] = useState<AppTemplate | null>(null);
  const [org, setOrg] = useState<Organization | null>(null);
  const [versions, setVersions] = useState<AppTemplateVersion[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);
  const [renameTarget, setRenameTarget] = useState<
    { kind: "model" | "relationship" | "constraint"; id: string; label: string } | null
  >(null);
  const [editFieldTarget, setEditFieldTarget] = useState<{ modelId: string; field: DraftField } | null>(
    null,
  );
  const confirm = useConfirm();

  async function load() {
    try {
      const t = await api.get<AppTemplate>(`/app-templates/${templateId}/`);
      setTemplate(t);
      const v = await api.get<Paginated<AppTemplateVersion>>(
        `/app-templates/${templateId}/versions/?limit=100`,
      );
      setVersions(v.results);
      api.get<Organization>(`/organizations/${t.organization}/`).then(setOrg).catch(() => {});
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load this template.");
      setErrorDetail(err);
    }
  }

  useEffect(() => {
    // One-shot fetch-on-mount/param-change, not a state-sync loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [templateId]);

  async function saveDraft(draft: AppDefinition) {
    setSaveError(null);
    setSaving(true);
    try {
      const updated = await api.patch<AppTemplate>(`/app-templates/${templateId}/`, { draft });
      setTemplate(updated);
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Failed to save this change.");
    } finally {
      setSaving(false);
    }
  }

  async function handlePublish() {
    setSaveError(null);
    setPublishing(true);
    try {
      const version = await api.post<AppTemplateVersion>(`/app-templates/${templateId}/versions/`, {});
      setVersions((prev) => [...(prev ?? []), version]);
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Failed to publish a version.");
    } finally {
      setPublishing(false);
    }
  }

  if (!template && !error) return <PageLoading />;
  if (error && !template) return <ErrorBanner message={error} error={errorDetail} />;
  if (!template) return null;

  const draft = template.draft;

  function addModel(key: string, label: string) {
    saveDraft({ ...draft, models: [...draft.models, { key, label, fields: [] }] });
  }

  async function deleteModel(model: DraftModel) {
    if (!(await confirm({ title: `Delete model "${model.label}"?`, confirmLabel: "Delete", danger: true })))
      return;
    saveDraft({
      ...draft,
      models: draft.models.filter((m) => m.id !== model.id),
      relationships: draft.relationships.filter(
        (r) => r.source_model !== model.id && r.target_model !== model.id,
      ),
    });
  }

  function renameModel(modelId: string, label: string) {
    saveDraft({
      ...draft,
      models: draft.models.map((m) => (m.id === modelId ? { ...m, label } : m)),
    });
  }

  function moveModel(modelId: string, direction: -1 | 1) {
    const index = draft.models.findIndex((m) => m.id === modelId);
    const swapWith = index + direction;
    if (index < 0 || swapWith < 0 || swapWith >= draft.models.length) return;
    const models = [...draft.models];
    [models[index], models[swapWith]] = [models[swapWith], models[index]];
    saveDraft({ ...draft, models });
  }

  function addField(modelId: string, field: DraftField) {
    saveDraft({
      ...draft,
      models: draft.models.map((m) => (m.id === modelId ? { ...m, fields: [...m.fields, field] } : m)),
    });
  }

  async function deleteField(model: DraftModel, field: DraftField) {
    if (!(await confirm({ title: `Delete field "${field.label}"?`, confirmLabel: "Delete", danger: true })))
      return;
    saveDraft({
      ...draft,
      models: draft.models.map((m) =>
        m.id === model.id
          ? {
              ...m,
              fields: m.fields.filter((f) => f.id !== field.id),
              // A constraint referencing this field would otherwise leave
              // the draft permanently unsavable (DefinitionInput.validate
              // rejects a constraint whose field_ids aren't a subset of
              // the model's current fields) -- cascade the same way
              // deleteModel already cascades relationships above: drop
              // the dangling reference, and the whole constraint if that
              // leaves it under the 2-field minimum.
              constraints: (m.constraints ?? [])
                .map((c) => ({ ...c, field_ids: c.field_ids.filter((id) => id !== field.id) }))
                .filter((c) => c.field_ids.length >= 2),
            }
          : m,
      ),
    });
  }

  function updateField(modelId: string, fieldId: string, patch: Partial<DraftField>) {
    saveDraft({
      ...draft,
      models: draft.models.map((m) =>
        m.id === modelId
          ? { ...m, fields: m.fields.map((f) => (f.id === fieldId ? { ...f, ...patch } : f)) }
          : m,
      ),
    });
  }

  function moveField(modelId: string, fieldId: string, direction: -1 | 1) {
    const model = draft.models.find((m) => m.id === modelId);
    if (!model) return;
    const index = model.fields.findIndex((f) => f.id === fieldId);
    const swapWith = index + direction;
    if (index < 0 || swapWith < 0 || swapWith >= model.fields.length) return;
    const fields = [...model.fields];
    [fields[index], fields[swapWith]] = [fields[swapWith], fields[index]];
    saveDraft({ ...draft, models: draft.models.map((m) => (m.id === modelId ? { ...m, fields } : m)) });
  }

  function addConstraint(modelId: string, constraint: DraftConstraint) {
    saveDraft({
      ...draft,
      models: draft.models.map((m) =>
        m.id === modelId ? { ...m, constraints: [...(m.constraints ?? []), constraint] } : m,
      ),
    });
  }

  async function deleteConstraint(model: DraftModel, constraint: DraftConstraint) {
    if (!(await confirm({ title: `Delete constraint "${constraint.label}"?`, confirmLabel: "Delete", danger: true })))
      return;
    saveDraft({
      ...draft,
      models: draft.models.map((m) =>
        m.id === model.id
          ? { ...m, constraints: (m.constraints ?? []).filter((c) => c.id !== constraint.id) }
          : m,
      ),
    });
  }

  function renameConstraint(modelId: string, constraintId: string, label: string) {
    saveDraft({
      ...draft,
      models: draft.models.map((m) =>
        m.id === modelId
          ? {
              ...m,
              constraints: (m.constraints ?? []).map((c) => (c.id === constraintId ? { ...c, label } : c)),
            }
          : m,
      ),
    });
  }

  function addRelationship(rel: DraftRelationship) {
    saveDraft({ ...draft, relationships: [...draft.relationships, rel] });
  }

  async function deleteRelationship(rel: DraftRelationship) {
    if (!(await confirm({ title: `Delete relationship "${rel.label}"?`, confirmLabel: "Delete", danger: true })))
      return;
    saveDraft({ ...draft, relationships: draft.relationships.filter((r) => r.id !== rel.id) });
  }

  function renameRelationship(relId: string, label: string) {
    saveDraft({
      ...draft,
      relationships: draft.relationships.map((r) => (r.id === relId ? { ...r, label } : r)),
    });
  }

  function moveRelationship(relId: string, direction: -1 | 1) {
    const index = draft.relationships.findIndex((r) => r.id === relId);
    const swapWith = index + direction;
    if (index < 0 || swapWith < 0 || swapWith >= draft.relationships.length) return;
    const relationships = [...draft.relationships];
    [relationships[index], relationships[swapWith]] = [relationships[swapWith], relationships[index]];
    saveDraft({ ...draft, relationships });
  }

  function setRelationshipDeletionPolicy(relId: string, deletion_policy: "restrict" | "set_null") {
    saveDraft({
      ...draft,
      relationships: draft.relationships.map((r) => (r.id === relId ? { ...r, deletion_policy } : r)),
    });
  }

  const savedModels = draft.models.filter((m) => m.id);

  return (
    <div>
      <PageHeader
        title={template.label}
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          ...(org
            ? [
                { label: org.name, href: `/orgs/${org.id}` },
                { label: "App templates", href: `/orgs/${org.id}/app-templates` },
              ]
            : []),
          { label: template.label },
        ]}
        description={template.description || undefined}
        actions={
          <>
            <Button variant="secondary" onClick={() => setDetailsModalOpen(true)}>
              Edit details
            </Button>
            <Button onClick={handlePublish} disabled={publishing || draft.models.length === 0}>
              {publishing ? "..." : "Publish version"}
            </Button>
          </>
        }
      />

      {template.archived && (
        <div className="mb-4">
          <Badge tone="warning">Archived</Badge>
        </div>
      )}
      {(error || saveError) && (
        <div className="mb-4">
          <ErrorBanner message={saveError ?? error ?? ""} error={errorDetail} />
        </div>
      )}

      <div className="mb-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-600">Models</h2>
        </div>
        <div className="space-y-4">
          {draft.models.map((model, modelIndex) => (
            <Card key={model.id ?? model.key}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <p className="font-medium text-slate-900">{model.label}</p>
                  <Badge>{model.key}</Badge>
                </div>
                {model.id && (
                  <div className="flex items-center gap-3 text-xs">
                    <MoveButtons
                      disabled={saving}
                      canMoveUp={modelIndex > 0}
                      canMoveDown={modelIndex < draft.models.length - 1}
                      onMoveUp={() => moveModel(model.id!, -1)}
                      onMoveDown={() => moveModel(model.id!, 1)}
                    />
                    <button
                      onClick={() => setRenameTarget({ kind: "model", id: model.id!, label: model.label })}
                      className="text-brand-600 hover:text-brand-500"
                      disabled={saving}
                    >
                      Rename
                    </button>
                    <button
                      onClick={() => deleteModel(model)}
                      className="text-red-600 hover:text-red-500"
                      disabled={saving}
                    >
                      Delete
                    </button>
                  </div>
                )}
              </div>

              <div className="mt-3 space-y-1.5">
                {model.fields.map((field, fieldIndex) => (
                  <div
                    key={field.id ?? field.key}
                    className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-1.5 text-sm"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-800">{field.label}</span>
                      <Badge>{field.key}</Badge>
                      <Badge tone="info">{field.data_type}</Badge>
                      {field.default_value !== null && field.default_value !== undefined && (
                        <Badge>default: {String(field.default_value)}</Badge>
                      )}
                    </div>
                    {field.id && model.id && (
                      <div className="flex items-center gap-3 text-xs">
                        <MoveButtons
                          disabled={saving}
                          canMoveUp={fieldIndex > 0}
                          canMoveDown={fieldIndex < model.fields.length - 1}
                          onMoveUp={() => moveField(model.id!, field.id!, -1)}
                          onMoveDown={() => moveField(model.id!, field.id!, 1)}
                        />
                        <label className="flex items-center gap-1.5 text-slate-600">
                          <Checkbox
                            checked={!!field.required}
                            disabled={saving}
                            onChange={(e) =>
                              updateField(model.id!, field.id!, { required: e.target.checked })
                            }
                          />
                          Required
                        </label>
                        <button
                          onClick={() => setEditFieldTarget({ modelId: model.id!, field })}
                          className="text-brand-600 hover:text-brand-500"
                          disabled={saving}
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => deleteField(model, field)}
                          className="text-red-600 hover:text-red-500"
                          disabled={saving}
                        >
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {model.id && <AddFieldForm modelId={model.id} onAdd={addField} disabled={saving} />}

              {model.id && (model.constraints ?? []).length > 0 && (
                <div className="mt-3 space-y-1.5 border-t border-slate-100 pt-3">
                  {(model.constraints ?? []).map((constraint) => (
                    <div
                      key={constraint.id ?? constraint.key}
                      className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-1.5 text-sm"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-slate-800">{constraint.label}</span>
                        <Badge tone="info">unique</Badge>
                        {constraint.field_ids.map((fieldId) => (
                          <Badge key={fieldId}>{fieldLabel(model, fieldId)}</Badge>
                        ))}
                      </div>
                      {constraint.id && (
                        <div className="flex items-center gap-3 text-xs">
                          <button
                            onClick={() =>
                              setRenameTarget({ kind: "constraint", id: constraint.id!, label: constraint.label })
                            }
                            className="text-brand-600 hover:text-brand-500"
                            disabled={saving}
                          >
                            Rename
                          </button>
                          <button
                            onClick={() => deleteConstraint(model, constraint)}
                            className="text-red-600 hover:text-red-500"
                            disabled={saving}
                          >
                            Delete
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {model.id && model.fields.filter((f) => f.id).length >= 2 && (
                <AddConstraintForm model={model} onAdd={addConstraint} disabled={saving} />
              )}
            </Card>
          ))}
        </div>

        <div className="mt-4">
          <AddModelForm onAdd={addModel} disabled={saving} />
        </div>
      </div>

      <div className="mb-8">
        <h2 className="mb-3 text-sm font-semibold text-slate-600">Relationships</h2>
        {draft.relationships.length === 0 ? (
          <p className="text-sm text-slate-500">No relationships yet.</p>
        ) : (
          <div className="space-y-1.5">
            {draft.relationships.map((rel, relIndex) => (
              <div
                key={rel.id ?? rel.key}
                className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-1.5 text-sm"
              >
                <div className="flex items-center gap-2">
                  <span className="font-medium text-slate-800">{rel.label}</span>
                  <span className="text-xs text-slate-500">
                    {modelLabel(draft, rel.source_model)} → {modelLabel(draft, rel.target_model)}
                  </span>
                  {rel.kind === "many_to_many" && <Badge tone="info">many-to-many</Badge>}
                </div>
                {rel.id && (
                  <div className="flex items-center gap-3 text-xs">
                    <MoveButtons
                      disabled={saving}
                      canMoveUp={relIndex > 0}
                      canMoveDown={relIndex < draft.relationships.length - 1}
                      onMoveUp={() => moveRelationship(rel.id!, -1)}
                      onMoveDown={() => moveRelationship(rel.id!, 1)}
                    />
                    {rel.kind !== "many_to_many" && (
                      <Select
                        value={rel.deletion_policy ?? "restrict"}
                        disabled={saving}
                        onChange={(e) =>
                          setRelationshipDeletionPolicy(
                            rel.id!,
                            e.target.value as "restrict" | "set_null",
                          )
                        }
                        className="!w-auto py-1 text-xs"
                      >
                        <option value="restrict">Restrict delete</option>
                        <option value="set_null">Set null on delete</option>
                      </Select>
                    )}
                    <button
                      onClick={() =>
                        setRenameTarget({ kind: "relationship", id: rel.id!, label: rel.label })
                      }
                      className="text-brand-600 hover:text-brand-500"
                      disabled={saving}
                    >
                      Rename
                    </button>
                    <button
                      onClick={() => deleteRelationship(rel)}
                      className="text-red-600 hover:text-red-500"
                      disabled={saving}
                    >
                      Delete
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {savedModels.length >= 1 && (
          <div className="mt-4">
            <AddRelationshipForm models={savedModels} onAdd={addRelationship} disabled={saving} />
          </div>
        )}
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-slate-600">Published versions</h2>
        {versions && versions.length === 0 ? (
          <p className="text-sm text-slate-500">
            Not published yet -- add at least one model, then publish a version to install this app.
          </p>
        ) : (
          <div className="space-y-1.5">
            {versions?.map((v) => (
              <Link
                key={v.id}
                href={`/app-template-versions/${v.id}`}
                className="block rounded-md bg-slate-50 px-3 py-1.5 text-sm text-brand-600 hover:bg-slate-100"
              >
                Version {v.number} · {new Date(v.created_at).toLocaleString()}
              </Link>
            ))}
          </div>
        )}
      </div>

      <EditDetailsModal
        open={detailsModalOpen}
        template={template}
        onClose={() => setDetailsModalOpen(false)}
        onSaved={(t) => {
          setTemplate(t);
          setDetailsModalOpen(false);
        }}
      />
      <RenameModal
        target={renameTarget}
        saving={saving}
        onClose={() => setRenameTarget(null)}
        onSave={(label) => {
          if (!renameTarget) return;
          if (renameTarget.kind === "model") renameModel(renameTarget.id, label);
          else if (renameTarget.kind === "relationship") renameRelationship(renameTarget.id, label);
          else {
            const model = draft.models.find((m) => (m.constraints ?? []).some((c) => c.id === renameTarget.id));
            if (model?.id) renameConstraint(model.id, renameTarget.id, label);
          }
          setRenameTarget(null);
        }}
      />
      <EditFieldModal
        target={editFieldTarget}
        saving={saving}
        onClose={() => setEditFieldTarget(null)}
        onSave={(patch) => {
          if (!editFieldTarget) return;
          updateField(editFieldTarget.modelId, editFieldTarget.field.id!, patch);
          setEditFieldTarget(null);
        }}
      />
    </div>
  );
}

function modelLabel(draft: AppDefinition, modelId: string): string {
  return draft.models.find((m) => m.id === modelId)?.label ?? modelId.slice(0, 8);
}

function fieldLabel(model: DraftModel, fieldId: string): string {
  return model.fields.find((f) => f.id === fieldId)?.label ?? fieldId.slice(0, 8);
}

function AddModelForm({
  onAdd,
  disabled,
}: {
  onAdd: (key: string, label: string) => void;
  disabled: boolean;
}) {
  const [key, setKey] = useState("");
  const [label, setLabel] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!key || !label) return;
    onAdd(key, label);
    setKey("");
    setLabel("");
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-2">
      <div>
        <Label htmlFor="new-model-label">New model name</Label>
        <Input
          id="new-model-label"
          value={label}
          onChange={(e) => {
            setLabel(e.target.value);
            if (!key) setKey(slugify(e.target.value));
          }}
          placeholder="Item"
        />
      </div>
      <div>
        <Label htmlFor="new-model-key">Key</Label>
        <Input
          id="new-model-key"
          pattern={KEY_PATTERN}
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="item"
        />
      </div>
      <Button type="submit" size="sm" disabled={disabled || !key || !label}>
        Add model
      </Button>
    </form>
  );
}

function AddFieldForm({
  modelId,
  onAdd,
  disabled,
}: {
  modelId: string;
  onAdd: (modelId: string, field: DraftField) => void;
  disabled: boolean;
}) {
  const [key, setKey] = useState("");
  const [label, setLabel] = useState("");
  const [dataType, setDataType] = useState<AppFieldDataType>("text");
  const [required, setRequired] = useState(false);
  const [defaultValue, setDefaultValue] = useState<FieldDefaultValue>(null);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!key || !label) return;
    onAdd(modelId, { key, label, data_type: dataType, required, default_value: defaultValue });
    setKey("");
    setLabel("");
    setDataType("text");
    setRequired(false);
    setDefaultValue(null);
  }

  return (
    <form onSubmit={handleSubmit} className="mt-3 flex flex-wrap items-end gap-2 border-t border-slate-100 pt-3">
      <div>
        <Label htmlFor={`new-field-label-${modelId}`}>New field name</Label>
        <Input
          id={`new-field-label-${modelId}`}
          value={label}
          onChange={(e) => {
            setLabel(e.target.value);
            if (!key) setKey(slugify(e.target.value));
          }}
          placeholder="Name"
        />
      </div>
      <div>
        <Label htmlFor={`new-field-key-${modelId}`}>Key</Label>
        <Input
          id={`new-field-key-${modelId}`}
          pattern={KEY_PATTERN}
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="name"
        />
      </div>
      <div>
        <Label htmlFor={`new-field-type-${modelId}`}>Type</Label>
        <Select
          id={`new-field-type-${modelId}`}
          value={dataType}
          onChange={(e) => {
            setDataType(e.target.value as AppFieldDataType);
            setDefaultValue(null);
          }}
        >
          {DATA_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </Select>
      </div>
      <div>
        <Label htmlFor={`new-field-default-${modelId}`}>Default</Label>
        <DefaultValueInput dataType={dataType} value={defaultValue} onChange={setDefaultValue} />
      </div>
      <label className="flex items-center gap-1.5 pb-2 text-sm text-slate-600">
        <Checkbox checked={required} onChange={(e) => setRequired(e.target.checked)} />
        Required
      </label>
      <Button type="submit" size="sm" variant="secondary" disabled={disabled || !key || !label}>
        Add field
      </Button>
    </form>
  );
}

// Model Settings -> Constraints -> Add Unique Constraint: select 2+ of
// this model's own already-saved fields (a field with no id yet hasn't
// round-tripped through the server, matching the same restriction
// AddRelationshipForm already applies to models via `savedModels`) plus
// an optional human-readable label. Physical constraint/index names are
// never surfaced here -- see AppConstraintDefinition's own comment.
function AddConstraintForm({
  model,
  onAdd,
  disabled,
}: {
  model: DraftModel;
  onAdd: (modelId: string, constraint: DraftConstraint) => void;
  disabled: boolean;
}) {
  const [label, setLabel] = useState("");
  const [key, setKey] = useState("");
  const [fieldIds, setFieldIds] = useState<string[]>([]);
  const savedFields = model.fields.filter((f) => f.id);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!key || !label || fieldIds.length < 2 || !model.id) return;
    onAdd(model.id, { key, label, field_ids: fieldIds });
    setLabel("");
    setKey("");
    setFieldIds([]);
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mt-3 flex flex-wrap items-end gap-3 border-t border-slate-100 pt-3"
    >
      <div>
        <Label htmlFor={`new-constraint-label-${model.id}`}>Unique constraint name</Label>
        <Input
          id={`new-constraint-label-${model.id}`}
          value={label}
          onChange={(e) => {
            setLabel(e.target.value);
            if (!key) setKey(slugify(e.target.value));
          }}
          placeholder="Unique combination"
        />
      </div>
      <div>
        <Label htmlFor={`new-constraint-key-${model.id}`}>Key</Label>
        <Input
          id={`new-constraint-key-${model.id}`}
          pattern={KEY_PATTERN}
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="unique_combination"
        />
      </div>
      <div>
        <Label htmlFor={`new-constraint-fields-${model.id}`}>Fields (select 2 or more)</Label>
        <div
          id={`new-constraint-fields-${model.id}`}
          className="flex max-h-24 flex-col gap-1 overflow-y-auto rounded-lg border border-slate-200 p-2"
        >
          {savedFields.map((f) => (
            <label key={f.id} className="flex items-center gap-1.5 text-sm text-slate-700">
              <Checkbox
                checked={fieldIds.includes(f.id!)}
                onChange={(e) =>
                  setFieldIds((prev) =>
                    e.target.checked ? [...prev, f.id!] : prev.filter((id) => id !== f.id),
                  )
                }
              />
              {f.label}
            </label>
          ))}
        </div>
      </div>
      <Button
        type="submit"
        size="sm"
        variant="secondary"
        disabled={disabled || !key || !label || fieldIds.length < 2}
      >
        Add unique constraint
      </Button>
    </form>
  );
}

function AddRelationshipForm({
  models,
  onAdd,
  disabled,
}: {
  models: DraftModel[];
  onAdd: (rel: DraftRelationship) => void;
  disabled: boolean;
}) {
  const [key, setKey] = useState("");
  const [label, setLabel] = useState("");
  const [sourceModel, setSourceModel] = useState(models[0]?.id ?? "");
  const [targetModel, setTargetModel] = useState(models[0]?.id ?? "");
  const [kind, setKind] = useState<AppRelationshipKind>("many_to_one");
  const [deletionPolicy, setDeletionPolicy] = useState<"restrict" | "set_null">("restrict");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!key || !label || !sourceModel || !targetModel) return;
    onAdd({
      key,
      label,
      source_model: sourceModel,
      target_model: targetModel,
      kind,
      // Meaningless for many_to_many (a join table's FKs are always
      // ON DELETE CASCADE regardless) -- sent as the fixed default
      // rather than whatever the (hidden) selector last held.
      deletion_policy: kind === "many_to_many" ? "restrict" : deletionPolicy,
    });
    setKey("");
    setLabel("");
    setKind("many_to_one");
    setDeletionPolicy("restrict");
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-2">
      <div>
        <Label htmlFor="new-rel-label">New relationship name</Label>
        <Input
          id="new-rel-label"
          value={label}
          onChange={(e) => {
            setLabel(e.target.value);
            if (!key) setKey(slugify(e.target.value));
          }}
          placeholder="Group"
        />
      </div>
      <div>
        <Label htmlFor="new-rel-key">Key</Label>
        <Input
          id="new-rel-key"
          pattern={KEY_PATTERN}
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="group"
        />
      </div>
      <div>
        <Label htmlFor="new-rel-source">From</Label>
        <Select id="new-rel-source" value={sourceModel} onChange={(e) => setSourceModel(e.target.value)}>
          {models.map((m) => (
            <option key={m.id} value={m.id}>
              {m.label}
            </option>
          ))}
        </Select>
      </div>
      <div>
        <Label htmlFor="new-rel-target">References</Label>
        <Select id="new-rel-target" value={targetModel} onChange={(e) => setTargetModel(e.target.value)}>
          {models.map((m) => (
            <option key={m.id} value={m.id}>
              {m.label}
            </option>
          ))}
        </Select>
      </div>
      <div>
        <Label htmlFor="new-rel-kind">Type</Label>
        <Select
          id="new-rel-kind"
          value={kind}
          onChange={(e) => setKind(e.target.value as AppRelationshipKind)}
        >
          <option value="many_to_one">Many-to-one (reference)</option>
          <option value="many_to_many">Many-to-many</option>
        </Select>
      </div>
      {kind !== "many_to_many" && (
        <div>
          <Label htmlFor="new-rel-policy">On delete</Label>
          <Select
            id="new-rel-policy"
            value={deletionPolicy}
            onChange={(e) => setDeletionPolicy(e.target.value as "restrict" | "set_null")}
          >
            <option value="restrict">Restrict</option>
            <option value="set_null">Set null</option>
          </Select>
        </div>
      )}
      <Button type="submit" size="sm" disabled={disabled || !key || !label}>
        Add relationship
      </Button>
    </form>
  );
}

function MoveButtons({
  disabled,
  canMoveUp,
  canMoveDown,
  onMoveUp,
  onMoveDown,
}: {
  disabled: boolean;
  canMoveUp: boolean;
  canMoveDown: boolean;
  onMoveUp: () => void;
  onMoveDown: () => void;
}) {
  return (
    <span className="flex items-center gap-1 text-slate-400">
      <button
        type="button"
        aria-label="Move up"
        onClick={onMoveUp}
        disabled={disabled || !canMoveUp}
        className="disabled:opacity-30"
      >
        ▲
      </button>
      <button
        type="button"
        aria-label="Move down"
        onClick={onMoveDown}
        disabled={disabled || !canMoveDown}
        className="disabled:opacity-30"
      >
        ▼
      </button>
    </span>
  );
}

function DefaultValueInput({
  dataType,
  value,
  onChange,
}: {
  dataType: AppFieldDataType;
  value: FieldDefaultValue | undefined;
  onChange: (v: FieldDefaultValue) => void;
}) {
  if (dataType === "boolean") {
    return (
      <Select
        value={value === true ? "true" : value === false ? "false" : ""}
        onChange={(e) => onChange(e.target.value === "" ? null : e.target.value === "true")}
      >
        <option value="">No default</option>
        <option value="true">true</option>
        <option value="false">false</option>
      </Select>
    );
  }
  if (dataType === "datetime") {
    return (
      <label className="flex items-center gap-1.5 text-sm text-slate-600">
        <Checkbox
          checked={value === "now()"}
          onChange={(e) => onChange(e.target.checked ? "now()" : null)}
        />
        Default to current time
      </label>
    );
  }
  if (dataType === "date") {
    return (
      <Input
        type="date"
        value={typeof value === "string" ? value : ""}
        onChange={(e) => onChange(e.target.value || null)}
      />
    );
  }
  if (dataType === "integer") {
    return (
      <Input
        type="number"
        step={1}
        value={typeof value === "number" ? String(value) : ""}
        onChange={(e) => onChange(e.target.value === "" ? null : parseInt(e.target.value, 10))}
      />
    );
  }
  if (dataType === "decimal") {
    return (
      <Input
        type="number"
        step="any"
        value={value === null || value === undefined ? "" : String(value)}
        onChange={(e) => onChange(e.target.value === "" ? null : e.target.value)}
      />
    );
  }
  return (
    <Input
      value={typeof value === "string" ? value : ""}
      onChange={(e) => onChange(e.target.value === "" ? null : e.target.value)}
    />
  );
}

function RenameModal({
  target,
  saving,
  onClose,
  onSave,
}: {
  target: { kind: "model" | "relationship" | "constraint"; id: string; label: string } | null;
  saving: boolean;
  onClose: () => void;
  onSave: (label: string) => void;
}) {
  const [label, setLabel] = useState("");

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (target) setLabel(target.label);
  }, [target]);

  return (
    <Modal open={!!target} onClose={onClose} title="Rename">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (label) onSave(label);
        }}
        className="space-y-4"
      >
        <div>
          <Label htmlFor="rename-input">Label</Label>
          <Input id="rename-input" autoFocus value={label} onChange={(e) => setLabel(e.target.value)} />
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving || !label}>
            Save
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function EditFieldModal({
  target,
  saving,
  onClose,
  onSave,
}: {
  target: { modelId: string; field: DraftField } | null;
  saving: boolean;
  onClose: () => void;
  onSave: (patch: Partial<DraftField>) => void;
}) {
  const [label, setLabel] = useState("");
  const [defaultValue, setDefaultValue] = useState<FieldDefaultValue>(null);

  useEffect(() => {
    if (!target) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLabel(target.field.label);
    setDefaultValue(target.field.default_value ?? null);
  }, [target]);

  return (
    <Modal open={!!target} onClose={onClose} title="Edit field">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (label) onSave({ label, default_value: defaultValue });
        }}
        className="space-y-4"
      >
        <div>
          <Label htmlFor="edit-field-label">Label</Label>
          <Input
            id="edit-field-label"
            autoFocus
            value={label}
            onChange={(e) => setLabel(e.target.value)}
          />
        </div>
        {target && (
          <div>
            <Label htmlFor="edit-field-default">Default value</Label>
            <DefaultValueInput
              dataType={target.field.data_type}
              value={defaultValue}
              onChange={setDefaultValue}
            />
            <p className="mt-1.5 text-xs text-slate-500">
              Used when a new record leaves this field blank.
            </p>
          </div>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving || !label}>
            Save
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function EditDetailsModal({
  open,
  template,
  onClose,
  onSaved,
}: {
  open: boolean;
  template: AppTemplate;
  onClose: () => void;
  onSaved: (t: AppTemplate) => void;
}) {
  const [label, setLabel] = useState(template.label);
  const [description, setDescription] = useState(template.description);
  const [archived, setArchived] = useState(template.archived);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLabel(template.label);
    setDescription(template.description);
    setArchived(template.archived);
    setError(null);
  }, [open, template]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const t = await api.patch<AppTemplate>(`/app-templates/${template.id}/`, {
        label,
        description,
        archived,
      });
      onSaved(t);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Edit template details">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <div>
          <Label htmlFor="edit-template-label">Name</Label>
          <Input id="edit-template-label" required value={label} onChange={(e) => setLabel(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="edit-template-description">Description</Label>
          <Textarea
            id="edit-template-description"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <Checkbox checked={archived} onChange={(e) => setArchived(e.target.checked)} />
          Archived
        </label>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "..." : "Save"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function slugify(value: string): string {
  const slug = value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return /^[a-z]/.test(slug) ? slug : `f_${slug}`;
}
