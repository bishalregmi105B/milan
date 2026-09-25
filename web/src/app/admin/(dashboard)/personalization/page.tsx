"use client";

import { useCallback, useEffect, useState } from "react";
import { adminApi, type PresetRow } from "@/lib/admin-api";
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  Field,
  Input,
  Modal,
  PageHeader,
  Select,
  Table,
  TableSkeleton,
  THead,
  TD,
  useToast,
} from "@/components/ui";
import { IconPalette, IconPlus } from "@/components/icons";

const PACKS = ["brand", "festival", "nature", "minimal", "saathi"] as const;
const WALLPAPER_TYPES = ["preset", "solid", "gradient"] as const;

const emptyForm = {
  key: "",
  pack: "brand" as (typeof PACKS)[number],
  name: "",
  wallpaper_type: "solid" as (typeof WALLPAPER_TYPES)[number],
  wallpaper_value: "",
  bubble_color_sent: "#F5A623",
  bubble_color_received: "#F3DCE2",
};

// Catalog-only view (doc 6 §2): add/retire preset packs.
// Deliberately NO access to individual users' chosen themes (doc 2 §2.7.1).
export default function AdminPersonalizationPage() {
  const [presets, setPresets] = useState<PresetRow[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [retireTarget, setRetireTarget] = useState<PresetRow | null>(null);
  const [retiring, setRetiring] = useState(false);
  const { success, error: toastError } = useToast();

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      setPresets((await adminApi.presets()).presets);
    } catch (e) {
      // Keep load failures distinct from a genuinely empty catalog.
      setLoadError(e instanceof Error ? e.message : "Failed to load the catalog.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setCreateError(null);
    try {
      await adminApi.createPreset({ ...form, sort_order: presets?.length ?? 0 });
      success("Preset created", `“${form.name}” is now in the ${form.pack} pack.`);
      setCreating(false);
      setForm({ ...emptyForm });
      await load();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Please try again.";
      setCreateError(message);
      toastError("Couldn't create preset", message);
    } finally {
      setSubmitting(false);
    }
  }

  async function retire(preset: PresetRow) {
    setRetiring(true);
    try {
      await adminApi.retirePreset(preset.id);
      success("Preset retired", `“${preset.name}” is no longer offered. Existing chats keep it valid.`);
      setRetireTarget(null);
      await load();
    } catch (err) {
      toastError(
        "Couldn't retire preset",
        err instanceof Error ? err.message : "Please try again.",
      );
    } finally {
      setRetiring(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Theme catalog"
        description="Chat theme presets offered across Milan. Retiring a preset never hard-deletes it — existing references stay valid. Individual users' chosen themes are private-per-viewer."
        actions={
          <Button onClick={() => setCreating((v) => !v)} aria-expanded={creating}>
            <IconPlus size={16} />
            {creating ? "Close form" : "Add preset"}
          </Button>
        }
      />

      {loadError && (
        <ErrorState
          title="Couldn't load the catalog"
          message={loadError}
          onRetry={() => void load()}
        />
      )}

      {!loadError && !presets && <TableSkeleton rows={4} cols={5} />}

      {!loadError && presets && presets.length === 0 && (
        <EmptyState
          icon={<IconPalette size={24} />}
          title="The catalog is empty"
          description="Add the first theme preset so users can personalize their chats."
          action={
            <Button onClick={() => setCreating(true)}>
              <IconPlus size={16} />
              Add preset
            </Button>
          }
        />
      )}

      {!loadError && presets && presets.length > 0 && (
        <Table>
          <THead columns={["Pack", "Name", "Key", "Colors", "Status", "Actions"]} />
          <tbody>
            {presets.map((p) => (
              <tr key={p.id} className="transition-colors hover:bg-paper-100/60">
                <TD className="capitalize">{p.pack}</TD>
                <TD className="font-medium text-ink-900">{p.name}</TD>
                <TD className="whitespace-nowrap font-mono text-xs">{p.key}</TD>
                <TD>
                  <span className="inline-flex items-center gap-1.5" aria-label={`Sent ${p.bubble_color_sent}, received ${p.bubble_color_received}`}>
                    <span
                      className="inline-block h-4 w-4 rounded-full border border-line300"
                      style={{ background: p.bubble_color_sent }}
                    />
                    <span
                      className="inline-block h-4 w-4 rounded-full border border-line300"
                      style={{ background: p.bubble_color_received }}
                    />
                  </span>
                </TD>
                <TD>
                  {p.is_active ? (
                    <Badge variant="success">active</Badge>
                  ) : (
                    <Badge variant="outline">retired</Badge>
                  )}
                </TD>
                <TD className="text-right">
                  {p.is_active && (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={retiring}
                      onClick={() => setRetireTarget(p)}
                    >
                      Retire
                    </Button>
                  )}
                </TD>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal
        open={creating}
        onClose={() => setCreating(false)}
        title="Add a theme preset"
        description="Users will see this in their chat theme picker under the chosen pack."
        footer={
          <>
            <Button variant="ghost" onClick={() => setCreating(false)} disabled={submitting}>
              Cancel
            </Button>
            <Button
              type="submit"
              form="create-preset-form"
              loading={submitting}
              disabled={!form.key || !form.name || !form.wallpaper_value}
            >
              Create preset
            </Button>
          </>
        }
      >
        <form id="create-preset-form" onSubmit={create} className="grid grid-cols-2 gap-4">
          <div className="col-span-2">
            {createError && (
              <p role="alert" className="mb-3 rounded-sm border border-milanerror/30 bg-milanerror-100/60 px-3 py-2 text-xs font-medium text-milanerror">
                {createError}
              </p>
            )}
          </div>
          <Field label="Key" htmlFor="preset-key" hint="Unique, snake_case.">
            <Input
              id="preset-key"
              value={form.key}
              onChange={(e) => setForm({ ...form, key: e.target.value })}
              placeholder="festival_gai_jatra"
              required
            />
          </Field>
          <Field label="Name" htmlFor="preset-name">
            <Input
              id="preset-name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Gai Jatra"
              required
            />
          </Field>
          <Field label="Pack" htmlFor="preset-pack">
            <Select
              id="preset-pack"
              value={form.pack}
              onChange={(e) => setForm({ ...form, pack: e.target.value as (typeof PACKS)[number] })}
            >
              {PACKS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Wallpaper type" htmlFor="preset-wtype">
            <Select
              id="preset-wtype"
              value={form.wallpaper_type}
              onChange={(e) =>
                setForm({ ...form, wallpaper_type: e.target.value as (typeof WALLPAPER_TYPES)[number] })
              }
            >
              {WALLPAPER_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </Select>
          </Field>
          <div className="col-span-2">
            <Field
              label="Wallpaper value"
              htmlFor="preset-wvalue"
              hint="A hex color for solid, a CSS gradient for gradient, or a preset id."
            >
              <Input
                id="preset-wvalue"
                value={form.wallpaper_value}
                onChange={(e) => setForm({ ...form, wallpaper_value: e.target.value })}
                placeholder="#F5A623"
                required
              />
            </Field>
          </div>
          <div className="col-span-2 flex items-center gap-3">
            <label htmlFor="bubble-sent" className="text-xs font-semibold text-ink-600">
              Sent bubble
            </label>
            <input
              id="bubble-sent"
              type="color"
              value={form.bubble_color_sent}
              onChange={(e) => setForm({ ...form, bubble_color_sent: e.target.value })}
              className="h-9 w-14 cursor-pointer rounded-sm border border-line300 bg-paper-50 p-1"
            />
            <label htmlFor="bubble-received" className="ml-2 text-xs font-semibold text-ink-600">
              Received bubble
            </label>
            <input
              id="bubble-received"
              type="color"
              value={form.bubble_color_received}
              onChange={(e) => setForm({ ...form, bubble_color_received: e.target.value })}
              className="h-9 w-14 cursor-pointer rounded-sm border border-line300 bg-paper-50 p-1"
            />
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={retireTarget !== null}
        onClose={() => setRetireTarget(null)}
        onConfirm={() => retireTarget && void retire(retireTarget)}
        title={`Retire “${retireTarget?.name ?? ""}”?`}
        description="The preset disappears from the theme picker, but users who already chose it keep it. This can't be undone from this page."
        confirmLabel="Retire preset"
        destructive
        busy={retiring}
      />
    </div>
  );
}
