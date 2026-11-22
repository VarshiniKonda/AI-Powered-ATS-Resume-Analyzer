import { useEffect, useState } from "react";
import {
  ArrowUpRight,
  BriefcaseBusiness,
  FileText,
  SearchCheck,
  Sparkles,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Link } from "react-router-dom";
import { api, getApiError } from "../api/client";

interface AnalysisSummary {
  id: number;
  job_title: string;
  company: string | null;
  resume_filename: string;
  overall_score: number;
  created_at: string;
}

interface DashboardData {
  total_resumes: number;
  total_jobs: number;
  total_analyses: number;
  average_score: number | null;
  best_match: AnalysisSummary | null;
  recent_analyses: AnalysisSummary[];
  score_history: Array<{ date: string; score: number; job_title: string }>;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(
    new Date(value),
  );
}

export function DashboardPage() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get<DashboardData>("/dashboard")
      .then(({ data }) => setDashboard(data))
      .catch((requestError: unknown) => setError(getApiError(requestError)));
  }, []);

  if (error) return <p className="notice-error" role="alert">{error}</p>;
  if (!dashboard) return <div aria-label="Loading dashboard" className="loading-panel" />;

  const cards = [
    { label: "Resumes saved", value: dashboard.total_resumes, icon: FileText, color: "blue" },
    { label: "Jobs collected", value: dashboard.total_jobs, icon: BriefcaseBusiness, color: "violet" },
    { label: "Analyses run", value: dashboard.total_analyses, icon: SearchCheck, color: "teal" },
    {
      label: "Average match",
      value: dashboard.average_score === null ? "—" : `${dashboard.average_score}%`,
      icon: Sparkles,
      color: "amber",
    },
  ];

  return (
    <div className="space-y-7">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="eyebrow">YOUR JOB SEARCH, IN FOCUS</p>
          <h1 className="page-title mt-2">Good to see you</h1>
          <p className="mt-2 text-sm text-muted">
            Real comparisons, clear gaps, and progress you can track.
          </p>
        </div>
        <Link className="btn-primary inline-flex items-center gap-2" to="/app/analyze">
          Resume Analyzer <ArrowUpRight size={17} />
        </Link>
      </div>

      <section aria-label="Dashboard summary" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map(({ label, value, icon: Icon, color }) => (
          <article className="stat-card" key={label}>
            <div className={`stat-icon stat-icon-${color}`}><Icon size={20} /></div>
            <p className="mt-5 text-sm font-medium text-muted">{label}</p>
            <p className="mt-1 text-3xl font-bold tracking-tight">{value}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.55fr_1fr]">
        <article className="panel">
          <div className="mb-5 flex items-start justify-between">
            <div>
              <h2 className="section-title">Score history</h2>
              <p className="mt-1 text-sm text-muted">Scores from your saved analyses</p>
            </div>
            <span className="rounded-lg bg-blue-50 px-3 py-1.5 text-xs font-semibold text-brand">
              {dashboard.score_history.length} recent
            </span>
          </div>
          {dashboard.score_history.length ? (
            <div aria-label="Compatibility score history chart" className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={dashboard.score_history} margin={{ top: 8, right: 12, left: -18, bottom: 0 }}>
                  <CartesianGrid stroke="#eef1f6" strokeDasharray="4 4" vertical={false} />
                  <XAxis dataKey="date" tickFormatter={formatDate} tickLine={false} axisLine={false} tick={{ fill: "#8290a4", fontSize: 12 }} />
                  <YAxis domain={[0, 100]} tickLine={false} axisLine={false} tick={{ fill: "#8290a4", fontSize: 12 }} />
                  <Tooltip
                    formatter={(value) => [`${value}%`, "Estimated match"]}
                    labelFormatter={(label) => formatDate(String(label))}
                    contentStyle={{ borderRadius: 12, border: "1px solid #e6eaf0" }}
                  />
                  <Line dataKey="score" stroke="#3767e8" strokeWidth={3} dot={{ r: 4, fill: "#3767e8" }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyPanel
              description="Run your first comparison to start a real score history."
              link="/app/analyze"
              linkLabel="Analyze a resume"
            />
          )}
        </article>

        <article className="panel">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <h2 className="section-title">Best match</h2>
              <p className="mt-1 text-sm text-muted">Your highest saved compatibility estimate</p>
            </div>
            <Sparkles className="text-amber-500" size={20} />
          </div>
          {dashboard.best_match ? (
            <div className="rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-50 p-5">
              <p className="text-sm font-semibold text-brand">{dashboard.best_match.company || "Saved opportunity"}</p>
              <h3 className="mt-2 text-lg font-bold">{dashboard.best_match.job_title}</h3>
              <p className="mt-1 truncate text-sm text-muted">{dashboard.best_match.resume_filename}</p>
              <p className="mt-5 text-4xl font-bold text-ink">
                {dashboard.best_match.overall_score}
                <span className="ml-1 text-base font-semibold text-muted">/ 100</span>
              </p>
              <Link className="mt-5 inline-flex items-center gap-1 text-sm font-semibold text-brand" to={`/app/analysis/${dashboard.best_match.id}`}>
                View analysis <ArrowUpRight size={15} />
              </Link>
            </div>
          ) : (
            <EmptyPanel
              description="Your best match will appear after you save an analysis."
              link="/app/analyze"
              linkLabel="Start an analysis"
            />
          )}
        </article>
      </section>

      <section className="panel">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h2 className="section-title">Recent analyses</h2>
            <p className="mt-1 text-sm text-muted">A quick view of your latest comparisons</p>
          </div>
          <Link className="text-sm font-semibold text-brand hover:underline" to="/app/history">View history</Link>
        </div>
        {dashboard.recent_analyses.length ? (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr><th>Role</th><th>Resume</th><th>Date</th><th>Estimate</th><th /></tr>
              </thead>
              <tbody>
                {dashboard.recent_analyses.map((analysis) => (
                  <tr key={analysis.id}>
                    <td><span className="font-semibold">{analysis.job_title}</span><span className="block text-xs text-muted">{analysis.company || "Company not specified"}</span></td>
                    <td>{analysis.resume_filename}</td>
                    <td>{formatDate(analysis.created_at)}</td>
                    <td><span className="score-pill">{analysis.overall_score}%</span></td>
                    <td><Link aria-label={`View ${analysis.job_title} analysis`} className="text-brand" to={`/app/analysis/${analysis.id}`}><ArrowUpRight size={17} /></Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyPanel
            description="Saved analyses appear here. Your results are calculated from the resume and job description you select."
            link="/app/analyze"
            linkLabel="Create your first analysis"
          />
        )}
      </section>
    </div>
  );
}

function EmptyPanel({ description, link, linkLabel }: { description: string; link: string; linkLabel: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/70 px-5 py-9 text-center">
      <p className="mx-auto max-w-md text-sm leading-6 text-muted">{description}</p>
      <Link className="mt-4 inline-flex text-sm font-semibold text-brand hover:underline" to={link}>{linkLabel}</Link>
    </div>
  );
}