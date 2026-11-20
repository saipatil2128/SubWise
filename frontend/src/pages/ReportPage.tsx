import { Link, useParams } from "react-router";

import { ReportView } from "../components/ReportView";
import { ErrorNote, Loading, PageHeader } from "../components/ui";
import { useReport } from "../hooks/queries";
import { formatDateTime } from "../lib/format";

export function ReportPage() {
  const { reportId } = useParams();
  const report = useReport(reportId);
  if (report.isLoading) return <Loading />;
  if (report.error || !report.data) return <ErrorNote error={report.error} title="Could not load this report" />;
  return (
    <>
      <PageHeader
        title="Recommendation report"
        subtitle={`Version ${report.data.version} · ${formatDateTime(report.data.created_at)}`}
        actions={<Link to={`/app/runs/${report.data.run_id}`} className="text-sm font-medium text-indigo-600 hover:underline">Open the run & timeline →</Link>}
      />
      <ReportView report={report.data} />
    </>
  );
}
