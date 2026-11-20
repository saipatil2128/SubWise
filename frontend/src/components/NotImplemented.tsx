/** Placeholder for Phase 1 pages; names the roadmap module that builds the page. */
export function NotImplemented({ title, module, summary }: { title: string; module: string; summary: string }) {
  return (
    <section className="space-y-2">
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="text-slate-600">{summary}</p>
      <p className="inline-block rounded bg-slate-200 px-2 py-1 text-sm text-slate-700">
        Not implemented yet — roadmap module {module}
      </p>
    </section>
  );
}
