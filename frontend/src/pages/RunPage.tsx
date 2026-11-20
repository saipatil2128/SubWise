import { useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useMemo, useState } from "react";
import { Link, useParams } from "react-router";

import { api } from "../api/client";
import type { ClarifyQuestion, Report, ReportFacts, Run } from "../api/types";
import { ReportView } from "../components/ReportView";
import { RunStatusBadge } from "../components/StatusBadge";
import { Timeline } from "../components/Timeline";
import { Button, Card, ErrorNote, Field, Input, Loading, Notice, PageHeader } from "../components/ui";
import { keys, useFeatures, useRun, useRunReports } from "../hooks/queries";
import { useRunEvents } from "../hooks/useRunEvents";
import { formatDateTime } from "../lib/format";

const ACTIVE = new Set(["queued", "running"]);

function ClarifyForm({ run, onSent }: { run: Run; onSent: () => void }) {
  const questions = ((run.pending_interrupt as { questions?: ClarifyQuestion[] } | null)?.questions ?? []) as ClarifyQuestion[];
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.clarify(run.run_id, answers);
      onSent();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="SubWise needs a little more information">
      <form onSubmit={submit} className="space-y-4">
        {questions.map((q) => (
          <Field key={q.field} label={q.question} htmlFor={`q-${q.field}`}>
            <Input id={`q-${q.field}`} value={answers[q.field] ?? ""} onChange={(e) => setAnswers({ ...answers, [q.field]: e.target.value })} />
          </Field>
        ))}
        <ErrorNote error={error} />
        <div className="flex justify-end gap-2">
          <Button type="submit" busy={busy}>Continue</Button>
        </div>
      </form>
    </Card>
  );
}

function ApprovalPanel({ run, report, onSent }: { run: Run; report: Report; onSent: () => void }) {
  const facts = report.facts as unknown as ReportFacts;
  const features = useFeatures();
  const [reason, setReason] = useState("");
  const [remember, setRemember] = useState<string[]>([]);
  const [mode, setMode] = useState<"idle" | "reject">("idle");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const pendingReport = (run.pending_interrupt as { report_id?: string } | null)?.report_id;

  // Covered feature labels -> codes, so the user can mark them as priorities to remember.
  const coveredCodes = useMemo(() => {
    const byLabel = new Map((features.data ?? []).map((f) => [f.label, f.code]));
    return facts.features_covered.map((label) => ({ label, code: byLabel.get(label) })).filter((x): x is { label: string; code: string } => !!x.code);
  }, [features.data, facts.features_covered]);

  if (pendingReport !== report.id) return null;

  const send = async (decision: "approved" | "rejected") => {
    setBusy(true);
    setError(null);
    try {
      await api.approve(run.run_id, { report_id: report.id, decision, reason: reason.trim() || undefined, remember: decision === "approved" ? remember : [] });
      onSent();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="Your decision" className="border-indigo-200 ring-1 ring-indigo-100">
      <p className="text-sm text-slate-600">
        Approving records this recommendation as your plan — SubWise does not subscribe or cancel anything for you. Rejecting with a reason makes it revise the recommendation{report.version > 1 ? ` (this is version ${report.version})` : ""}.
      </p>
      {mode === "idle" && coveredCodes.length > 0 && facts.status === "optimal" && (
        <div className="mt-4">
          <p className="text-sm font-medium text-slate-700">Remember these as priorities for next time (optional)</p>
          <div className="mt-2 flex flex-wrap gap-3">
            {coveredCodes.map((c) => (
              <label key={c.code} className="flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" className="h-4 w-4 rounded border-slate-300 text-indigo-600" checked={remember.includes(c.code)} onChange={(e) => setRemember(e.target.checked ? [...remember, c.code] : remember.filter((x) => x !== c.code))} />
                {c.label}
              </label>
            ))}
          </div>
        </div>
      )}
      {mode === "reject" && (
        <div className="mt-4">
          <Field label="What's wrong with it?" htmlFor="reason" hint="e.g. “I need 4K”, “keep Spotify”, “too expensive”. SubWise uses this to revise.">
            <textarea id="reason" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} className="block w-full rounded-lg border-0 px-3 py-2 text-sm ring-1 ring-inset ring-slate-300 focus:ring-2 focus:ring-indigo-500" />
          </Field>
        </div>
      )}
      <div className="mt-4"><ErrorNote error={error} /></div>
      <div className="mt-4 flex flex-wrap justify-end gap-2">
        {mode === "idle" ? (
          <>
            <Button variant="secondary" onClick={() => setMode("reject")}>Reject…</Button>
            <Button busy={busy} onClick={() => send("approved")} disabled={facts.status !== "optimal"} title={facts.status !== "optimal" ? "Nothing to approve — reject with a reason to revise" : undefined}>Approve</Button>
          </>
        ) : (
          <>
            <Button variant="ghost" onClick={() => setMode("idle")}>Back</Button>
            <Button variant="danger" busy={busy} onClick={() => send("rejected")}>{reason.trim() ? "Reject and revise" : "Reject"}</Button>
          </>
        )}
      </div>
    </Card>
  );
}

export function RunPage() {
  const { runId } = useParams();
  const qc = useQueryClient();
  const run = useRun(runId);
  const status = run.data?.status ?? "queued";
  const live = ACTIVE.has(status);
  const reports = useRunReports(runId);
  const [actionError, setActionError] = useState<unknown>(null);
  const [busy, setBusy] = useState<"cancel" | "resume" | null>(null);

  const refresh = () => {
    void qc.invalidateQueries({ queryKey: keys.run(runId ?? "") });
    void qc.invalidateQueries({ queryKey: keys.runReports(runId ?? "") });
    void qc.invalidateQueries({ queryKey: keys.runs });
    void qc.invalidateQueries({ queryKey: keys.dashboard });
  };
  const events = useRunEvents(runId, run.data?.status, refresh);

  const latest = reports.data?.length ? reports.data[reports.data.length - 1] : undefined;
  const [shownVersion, setShownVersion] = useState<number | null>(null);
  const shown = reports.data?.find((r) => r.version === shownVersion) ?? latest;

  if (run.isLoading) return <Loading />;
  if (run.error || !run.data) return <ErrorNote error={run.error} title="Could not load this run" />;
  const r = run.data;

  const act = async (kind: "cancel" | "resume") => {
    setBusy(kind);
    setActionError(null);
    try {
      await (kind === "cancel" ? api.cancelRun(r.run_id) : api.resumeRun(r.run_id));
      refresh();
    } catch (err) {
      setActionError(err);
    } finally {
      setBusy(null);
    }
  };

  const afterAction = () => {
    setShownVersion(null);
    // Status flips to queued immediately; refetch so the event stream reconnects.
    refresh();
  };

  return (
    <>
      <PageHeader
        title="Optimization"
        subtitle={<span>“{r.request_message}” · started {formatDateTime(r.created_at)}{r.llm_model && ` · ${r.llm_model}`}</span>}
        actions={
          <>
            <RunStatusBadge status={r.status} />
            {r.status.startsWith("waiting") && <Button variant="secondary" busy={busy === "cancel"} onClick={() => act("cancel")}>Cancel run</Button>}
            {r.resumable && <Button busy={busy === "resume"} onClick={() => act("resume")}>Resume from checkpoint</Button>}
          </>
        }
      />
      <ErrorNote error={actionError} />
      {r.status === "failed" && (
        <div className="mb-6">
          <Notice tone="warn">
            <p className="font-medium">This run stopped: {r.error_message ?? r.error_code}</p>
            {r.resumable && <p className="mt-1">The server restarted while it was working. Its progress was checkpointed — use “Resume from checkpoint”.</p>}
          </Notice>
        </div>
      )}
      {r.status === "cancelled" && <div className="mb-6"><Notice>This run was cancelled.</Notice></div>}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          {r.status === "waiting_clarification" && <ClarifyForm run={r} onSent={afterAction} />}
          {r.status === "waiting_approval" && latest && <ApprovalPanel key={latest.id} run={r} report={latest} onSent={afterAction} />}
          {reports.data && reports.data.length > 1 && (
            <div className="flex items-center gap-2 text-sm">
              <span className="text-slate-500">Version:</span>
              {reports.data.map((rep) => (
                <button key={rep.id} type="button" onClick={() => setShownVersion(rep.version)} className={`rounded-md px-2.5 py-1 text-xs font-medium ${shown?.id === rep.id ? "bg-indigo-600 text-white" : "bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"}`}>
                  v{rep.version} · {rep.status}
                </button>
              ))}
            </div>
          )}
          {shown ? <ReportView report={shown} /> : live ? <Card><Loading label="The agent is working — the report appears here when it is ready." /></Card> : !r.status.startsWith("waiting_clar") && <Card><p className="text-sm text-slate-500">No report was produced for this run.</p></Card>}
          {r.status === "completed" && latest && (
            <Notice tone={latest.status === "approved" ? "success" : "info"}>
              {latest.status === "approved" ? "You approved this recommendation. Make the changes with each provider, then update your subscriptions here." : "This run finished."}{" "}
              <Link to="/app/subscriptions" className="font-medium underline">Update subscriptions</Link>
            </Notice>
          )}
        </div>
        <div>
          <Card title="Agent timeline" className="lg:sticky lg:top-6">
            <div className="max-h-[70vh] overflow-y-auto pr-1">
              <Timeline events={events} live={live} />
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
