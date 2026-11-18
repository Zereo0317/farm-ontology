import { useState } from "react";
import { Button } from "@/components/button";
import { useCopy, useLocale } from "@/components/locale-context";
import {
  downloadJson,
  saveBriefing,
  saveWaitlist,
  transmitLead,
  withHash,
  type BriefingRecord,
  type LeadTransmission,
  type WaitlistRecord,
} from "@/lib/records";

const emailOk = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());

function Field({
  id,
  label,
  value,
  onChange,
  type = "text",
  autoComplete,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  autoComplete?: string;
}) {
  return (
    <label className="block" htmlFor={id}>
      <span className="text-sm text-muted">{label}</span>
      <input
        id={id}
        type={type}
        autoComplete={autoComplete}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 min-h-11 w-full rounded-control border border-line bg-paper px-3 text-ink"
      />
    </label>
  );
}

function Issued({
  title,
  note,
  hash,
  onDownload,
}: {
  title: string;
  note: string;
  hash: string;
  onDownload: () => void;
}) {
  const copy = useCopy();
  return (
    <div className="border border-ink bg-paper p-4 sm:p-5">
      <h3 className="font-display text-2xl">{title}</h3>
      <p className="mt-3 text-sm leading-relaxed">{note}</p>
      <p className="mt-4 text-xs tracking-stamp text-muted uppercase">{copy.prov.hash}</p>
      <p className="mt-1 font-mono text-xs break-all">{hash}</p>
      <Button className="mt-5" onClick={onDownload}>
        {copy.forms.download}
      </Button>
    </div>
  );
}

export function WaitlistForm() {
  const copy = useCopy();
  const locale = useLocale();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState<{ record: WaitlistRecord; transmission: LeadTransmission } | null>(null);

  async function submit() {
    if (!name.trim()) return setError(copy.forms.nameRequired);
    if (!emailOk(email)) return setError(copy.forms.emailInvalid);
    if (!consent) return setError(copy.forms.consentRequired);
    const record = await withHash<WaitlistRecord>({
      kind: "pro-waitlist",
      name: name.trim(),
      email: email.trim(),
      locale,
      consentedAt: new Date().toISOString(),
      statement: copy.forms.consentWait,
      hash: "",
    });
    saveWaitlist(record);
    const transmission = await transmitLead(record);
    setSaved({ record, transmission });
    setError("");
  }

  return (
    <section id="waitlist" className="scroll-mt-nav border border-line bg-paper-2 p-4 sm:p-6">
      <h3 className="font-display text-2xl">{copy.forms.waitTitle}</h3>
      <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">{copy.forms.waitBody}</p>
      {saved ? (
        <div className="mt-5">
          <Issued
            title={copy.forms.savedWait}
            note={
              saved.transmission === "landed"
                ? copy.forms.notTransmitted
                : `${copy.forms.notTransmitted}（現在只存在這台裝置；稍後自動重試或寄回名片。）`
            }
            hash={saved.record.hash}
            onDownload={() => downloadJson("farm-ontology-pro-waitlist.json", saved.record)}
          />
          <p className="mt-2 text-xs text-muted">
            {saved.transmission === "landed" ? "✔ 已收進田間帳本（GCS）" : "⚠ 帳本連線未成——記錄已存此機"}
          </p>
        </div>
      ) : (
        <form
          className="mt-5 grid gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          <Field id="wait-name" label={copy.forms.name} value={name} onChange={setName} autoComplete="name" />
          <Field id="wait-email" label={copy.forms.email} value={email} onChange={setEmail} type="email" autoComplete="email" />
          <label className="flex items-start gap-3 text-sm">
            <input
              type="checkbox"
              className="mt-1 size-4"
              checked={consent}
              onChange={(event) => setConsent(event.target.checked)}
            />
            <span>{copy.forms.consentWait}</span>
          </label>
          {error ? (
            <p className="text-sm" role="alert">
              {error}
            </p>
          ) : null}
          <Button type="submit">{copy.forms.submitWait}</Button>
        </form>
      )}
    </section>
  );
}

export function BriefingForm() {
  const copy = useCopy();
  const locale = useLocale();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [org, setOrg] = useState("");
  const [role, setRole] = useState("");
  const [needs, setNeeds] = useState<string[]>([]);
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState<{ record: BriefingRecord; transmission: LeadTransmission } | null>(null);

  const options = [
    { id: "lineage", label: copy.forms.needLineage },
    { id: "licence", label: copy.forms.needLicence },
    { id: "hash", label: copy.forms.needHash },
  ];

  function toggle(id: string) {
    setNeeds((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
  }

  async function submit() {
    if (!name.trim()) return setError(copy.forms.nameRequired);
    if (!emailOk(email)) return setError(copy.forms.emailInvalid);
    if (!org.trim()) return setError(copy.forms.orgRequired);
    if (needs.length === 0) return setError(copy.forms.needRequired);
    if (!consent) return setError(copy.forms.consentRequired);
    const record = await withHash<BriefingRecord>({
      kind: "governance-briefing",
      name: name.trim(),
      email: email.trim(),
      org: org.trim(),
      role: role.trim(),
      needs,
      locale,
      consentedAt: new Date().toISOString(),
      statement: copy.forms.consentBrief,
      hash: "",
    });
    saveBriefing(record);
    const transmission = await transmitLead(record);
    setSaved({ record, transmission });
    setError("");
  }

  return (
    <section id="briefing" className="scroll-mt-nav border border-line p-4 sm:p-6">
      <h3 className="font-display text-2xl">{copy.forms.briefTitle}</h3>
      <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">{copy.forms.briefBody}</p>
      {saved ? (
        <div className="mt-5">
          <Issued
            title={copy.forms.savedBrief}
            note={copy.forms.notTransmitted}
            hash={saved.record.hash}
            onDownload={() => downloadJson("farm-ontology-briefing.json", saved.record)}
          />
          <p className="mt-2 text-xs text-muted">
            {saved.transmission === "landed" ? "✔ Received into the field ledger (GCS)" : "⚠ Ledger unreachable — the record stays on this device"}
          </p>
        </div>
      ) : (
        <form
          className="mt-5 grid gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          <Field id="brief-name" label={copy.forms.name} value={name} onChange={setName} autoComplete="name" />
          <Field id="brief-email" label={copy.forms.email} value={email} onChange={setEmail} type="email" autoComplete="email" />
          <Field id="brief-org" label={copy.forms.org} value={org} onChange={setOrg} autoComplete="organization" />
          <Field id="brief-role" label={copy.forms.role} value={role} onChange={setRole} autoComplete="organization-title" />
          <fieldset>
            <legend className="text-sm text-muted">{copy.forms.needs}</legend>
            <div className="mt-2 grid gap-2">
              {options.map((option) => (
                <label key={option.id} className="flex min-h-11 items-center gap-3 text-sm">
                  <input
                    type="checkbox"
                    className="size-4"
                    checked={needs.includes(option.id)}
                    onChange={() => toggle(option.id)}
                  />
                  {option.label}
                </label>
              ))}
            </div>
          </fieldset>
          <label className="flex items-start gap-3 text-sm">
            <input
              type="checkbox"
              className="mt-1 size-4"
              checked={consent}
              onChange={(event) => setConsent(event.target.checked)}
            />
            <span>{copy.forms.consentBrief}</span>
          </label>
          {error ? (
            <p className="text-sm" role="alert">
              {error}
            </p>
          ) : null}
          <Button type="submit" variant="secondary">
            {copy.forms.submitBrief}
          </Button>
        </form>
      )}
    </section>
  );
}
