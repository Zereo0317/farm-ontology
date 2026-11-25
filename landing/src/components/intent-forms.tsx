import { useState } from "react";
import { Button } from "@/components/button";
import { useCopy, useLocale } from "@/components/locale-context";
import {
  downloadJson,
  saveAccessRequest,
  saveBriefing,
  transmitLead,
  withHash,
  type AccessRequestRecord,
  type BriefingRecord,
  type LeadTransmission,
} from "@/lib/records";

type Audience = "farmer" | "research" | "finance";
const emailOk = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());

function Field({
  id,
  label,
  value,
  onChange,
  type = "text",
  autoComplete,
  required = false,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  autoComplete?: string;
  required?: boolean;
}) {
  return (
    <label className="block" htmlFor={id}>
      <span className="text-sm text-muted">{label}</span>
      <input
        id={id}
        type={type}
        autoComplete={autoComplete}
        required={required}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 min-h-11 w-full rounded-control border border-line bg-paper px-3 text-ink"
      />
    </label>
  );
}

function SavedRequest({
  title,
  status,
  hash,
  onDownload,
}: {
  title: string;
  status: string;
  hash: string;
  onDownload: () => void;
}) {
  const copy = useCopy();
  return (
    <div className="border border-ink bg-paper p-4 sm:p-5" role="status" aria-live="polite">
      <h3 className="font-display text-2xl">{title}</h3>
      <p className="mt-3 text-sm leading-relaxed">{status}</p>
      <p className="mt-4 text-xs tracking-stamp text-muted uppercase">{copy.prov.hash}</p>
      <p className="mt-1 break-all font-mono text-xs">{hash}</p>
      <Button className="mt-5" onClick={onDownload}>{copy.forms.download}</Button>
    </div>
  );
}

export function AccessRequestForm() {
  const copy = useCopy();
  const locale = useLocale();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [farmName, setFarmName] = useState("");
  const [region, setRegion] = useState("");
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const [saved, setSaved] = useState<{ record: AccessRequestRecord; persisted: boolean; transmission: LeadTransmission } | null>(null);

  async function submit() {
    if (!name.trim()) return setError(copy.forms.nameRequired);
    if (!emailOk(email)) return setError(copy.forms.emailInvalid);
    if (!farmName.trim()) return setError(copy.forms.farmRequired);
    if (!region.trim()) return setError(copy.forms.regionRequired);
    if (!consent) return setError(copy.forms.consentRequired);
    setSending(true);
    try {
      const record = await withHash<AccessRequestRecord>({
        kind: "access-code-request",
        name: name.trim(),
        email: email.trim(),
        farmName: farmName.trim(),
        region: region.trim(),
        locale,
        audience: "farmer",
        consentedAt: new Date().toISOString(),
        statement: copy.forms.consentAccess,
        hash: "",
      });
      const persisted = saveAccessRequest(record);
      const transmission = await transmitLead(record);
      setSaved({ record, persisted, transmission });
      setError("");
    } finally {
      setSending(false);
    }
  }

  const status = saved?.transmission === "received"
    ? copy.forms.receivedStatus
    : saved?.persisted
      ? copy.forms.deviceOnlyStatus
      : copy.forms.notSavedStatus;

  return (
    <section id="farm-access" className="scroll-mt-nav border border-line bg-paper-2 p-4 sm:p-6">
      <h2 className="font-display text-2xl">{copy.forms.accessTitle}</h2>
      <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">{copy.forms.accessBody}</p>
      {saved ? (
        <div className="mt-5">
          <SavedRequest
            title={copy.forms.savedAccess}
            status={status}
            hash={saved.record.hash}
            onDownload={() => downloadJson("farm-access-request.json", saved.record)}
          />
        </div>
      ) : (
        <form noValidate className="mt-5 grid gap-4" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
          <Field id="access-name" label={copy.forms.name} value={name} onChange={setName} autoComplete="name" required />
          <Field id="access-email" label={copy.forms.email} value={email} onChange={setEmail} type="email" autoComplete="email" required />
          <Field id="access-farm" label={copy.forms.farmName} value={farmName} onChange={setFarmName} autoComplete="organization" required />
          <Field id="access-region" label={copy.forms.farmRegion} value={region} onChange={setRegion} autoComplete="address-level1" required />
          <label className="flex items-start gap-3 text-sm">
            <input type="checkbox" className="mt-1 size-4" checked={consent} onChange={(event) => setConsent(event.target.checked)} required />
            <span>{copy.forms.consentAccess}</span>
          </label>
          {error ? <p className="text-sm" role="alert">{error}</p> : null}
          <Button type="submit" disabled={sending}>{copy.forms.submitAccess}</Button>
        </form>
      )}
    </section>
  );
}

export function BriefingForm({ audience }: { audience: Exclude<Audience, "farmer"> }) {
  const copy = useCopy();
  const locale = useLocale();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [org, setOrg] = useState("");
  const [role, setRole] = useState("");
  const [needs, setNeeds] = useState<string[]>([]);
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const [saved, setSaved] = useState<{ record: BriefingRecord; persisted: boolean; transmission: LeadTransmission } | null>(null);
  const finance = audience === "finance";
  const options = [
    { id: "lineage", label: copy.forms.needLineage },
    { id: "licence", label: copy.forms.needLicence },
    { id: "hash", label: copy.forms.needHash },
    ...(finance ? [{ id: "finance", label: copy.forms.needFinance }] : []),
  ];
  const title = finance ? copy.forms.financeTitle : copy.forms.briefTitle;
  const body = finance ? copy.forms.financeBody : copy.forms.briefBody;

  function toggle(id: string) {
    setNeeds((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  }

  async function submit() {
    if (!name.trim()) return setError(copy.forms.nameRequired);
    if (!emailOk(email)) return setError(copy.forms.emailInvalid);
    if (!org.trim()) return setError(copy.forms.orgRequired);
    if (needs.length === 0) return setError(copy.forms.needRequired);
    if (!consent) return setError(copy.forms.consentRequired);
    setSending(true);
    try {
      const record = await withHash<BriefingRecord>({
        kind: "governance-briefing",
        name: name.trim(),
        email: email.trim(),
        org: org.trim(),
        role: role.trim(),
        needs,
        locale,
        audience,
        consentedAt: new Date().toISOString(),
        statement: copy.forms.consentBrief,
        hash: "",
      });
      const persisted = saveBriefing(record);
      const transmission = await transmitLead(record);
      setSaved({ record, persisted, transmission });
      setError("");
    } finally {
      setSending(false);
    }
  }

  const status = saved?.transmission === "received"
    ? copy.forms.receivedStatus
    : saved?.persisted
      ? copy.forms.deviceOnlyStatus
      : copy.forms.notSavedStatus;

  return (
    <section id="briefing" className="scroll-mt-nav border border-line p-4 sm:p-6">
      <h2 className="font-display text-2xl">{title}</h2>
      <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">{body}</p>
      {saved ? (
        <div className="mt-5">
          <SavedRequest
            title={copy.forms.savedBrief}
            status={status}
            hash={saved.record.hash}
            onDownload={() => downloadJson("farm-briefing-request.json", saved.record)}
          />
        </div>
      ) : (
        <form noValidate className="mt-5 grid gap-4" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
          <Field id="brief-name" label={copy.forms.name} value={name} onChange={setName} autoComplete="name" required />
          <Field id="brief-email" label={copy.forms.email} value={email} onChange={setEmail} type="email" autoComplete="email" required />
          <Field id="brief-org" label={copy.forms.org} value={org} onChange={setOrg} autoComplete="organization" required />
          <Field id="brief-role" label={copy.forms.role} value={role} onChange={setRole} autoComplete="organization-title" />
          <fieldset>
            <legend className="text-sm text-muted">{copy.forms.needs}</legend>
            <div className="mt-2 grid gap-2">
              {options.map((option) => (
                <label key={option.id} className="flex min-h-11 items-center gap-3 text-sm">
                  <input type="checkbox" className="size-4" checked={needs.includes(option.id)} onChange={() => toggle(option.id)} />
                  {option.label}
                </label>
              ))}
            </div>
          </fieldset>
          <label className="flex items-start gap-3 text-sm">
            <input type="checkbox" className="mt-1 size-4" checked={consent} onChange={(event) => setConsent(event.target.checked)} required />
            <span>{copy.forms.consentBrief}</span>
          </label>
          {error ? <p className="text-sm" role="alert">{error}</p> : null}
          <Button type="submit" variant="secondary" disabled={sending}>{copy.forms.submitBrief}</Button>
        </form>
      )}
    </section>
  );
}
