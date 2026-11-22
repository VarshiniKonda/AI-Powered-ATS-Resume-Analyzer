import { lazy, Suspense, useEffect, useState } from "react";
import { ArrowRight, BriefcaseBusiness, CheckCircle2, CircleHelp } from "lucide-react";
import { Link, Navigate, Outlet, Route, Routes } from "react-router-dom";
import { api } from "./api/client";
import { AuthProvider, useAuth } from "./context/AuthContext";

const AppShell = lazy(() =>
  import("./components/AppShell").then((module) => ({ default: module.AppShell })),
);
const AuthPage = lazy(() =>
  import("./pages/AuthPage").then((module) => ({ default: module.AuthPage })),
);
const DashboardPage = lazy(() =>
  import("./pages/DashboardPage").then((module) => ({ default: module.DashboardPage })),
);
const ResumeManagementPage = lazy(() =>
  import("./pages/ResumeJobsPages").then((module) => ({ default: module.ResumeManagementPage })),
);
const JobsPage = lazy(() =>
  import("./pages/ResumeJobsPages").then((module) => ({ default: module.JobsPage })),
);
const AnalyzePage = lazy(() =>
  import("./pages/AnalysisPages").then((module) => ({ default: module.AnalyzePage })),
);
const AnalysisResultsPage = lazy(() =>
  import("./pages/AnalysisPages").then((module) => ({ default: module.AnalysisResultsPage })),
);
const HistoryPage = lazy(() =>
  import("./pages/AnalysisPages").then((module) => ({ default: module.HistoryPage })),
);
const TrackerPage = lazy(() =>
  import("./pages/AnalysisPages").then((module) => ({ default: module.TrackerPage })),
);
const SettingsPage = lazy(() =>
  import("./pages/AnalysisPages").then((module) => ({ default: module.SettingsPage })),
);

type ApiStatus = "checking" | "online" | "offline";

function LandingPage() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    let active = true;

    api
      .get<{ status: string }>("/health")
      .then(({ data }) => {
        if (active) setApiStatus(data.status === "ok" ? "online" : "offline");
      })
      .catch(() => {
        if (active) setApiStatus("offline");
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="min-h-screen bg-canvas text-ink">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-6 py-6 lg:px-10">
        <Link aria-label="Matchwise home" className="flex items-center gap-3" to="/">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand text-white">
            <BriefcaseBusiness size={20} />
          </span>
          <span className="text-lg font-bold tracking-tight">matchwise</span>
        </Link>
        <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-muted">
          {apiStatus === "online" ? (
            <CheckCircle2 aria-hidden="true" className="text-emerald-600" size={15} />
          ) : (
            <CircleHelp aria-hidden="true" className="text-amber-600" size={15} />
          )}
          <span role="status">
            {apiStatus === "checking"
              ? "Connecting to API"
              : apiStatus === "online"
                ? "API connected"
                : "API unavailable"}
          </span>
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl gap-12 px-6 pb-20 pt-16 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:px-10 lg:pb-28 lg:pt-20">
        <div>
          <p className="mb-6 inline-flex rounded-full border border-blue-100 bg-blue-50 px-4 py-2 text-sm font-semibold text-brand">
            A clearer path from application to opportunity
          </p>
          <h1 className="max-w-3xl text-5xl font-bold leading-[1.08] tracking-tight sm:text-6xl">
            Make every application
            <span className="text-brand"> more intentional.</span>
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-8 text-muted">
            Compare your resume with a job description, see where the fit is
            strong, and get practical guidance grounded in what you have actually
            done.
          </p>
          <div className="mt-9 flex flex-wrap items-center gap-4">
            <Link className="inline-flex items-center gap-2 rounded-xl bg-brand px-5 py-3.5 text-sm font-semibold text-white shadow-lg shadow-blue-200 hover:bg-blue-700" to="/register">
              Create a free account <ArrowRight size={17} />
            </Link>
            <span className="text-sm text-muted">
              Estimated insights, never an employer ATS score
            </span>
          </div>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/60 sm:p-8">
          <div className="flex items-center justify-between border-b border-slate-100 pb-5">
            <div>
              <p className="text-sm font-semibold text-muted">MATCH OVERVIEW</p>
              <p className="mt-1 text-xl font-bold">Your next role, in focus</p>
            </div>
            <span className="rounded-xl bg-blue-50 p-3 text-brand">
              <BriefcaseBusiness size={21} />
            </span>
          </div>
          <div className="space-y-5 pt-6">
            {[
              ["Required skills", "Evidence-based comparison"],
              ["Experience", "Relevant context, not just keywords"],
              ["Next steps", "Honest, actionable improvements"],
            ].map(([heading, detail], index) => (
              <div className="flex items-start gap-4" key={heading}>
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-blue-50 text-sm font-bold text-brand">
                  0{index + 1}
                </span>
                <div>
                  <p className="font-semibold">{heading}</p>
                  <p className="mt-1 text-sm leading-6 text-muted">{detail}</p>
                </div>
              </div>
            ))}
          </div>
          <p className="mt-7 rounded-xl bg-slate-50 p-4 text-xs leading-5 text-muted">
            Compatibility estimates are decision-support signals only. They do
            not predict or reproduce any employer&apos;s applicant tracking
            system.
          </p>
        </div>
      </section>
    </main>
  );
}

function ProtectedRoute() {
  const { isLoading, user } = useAuth();
  if (isLoading) return <div aria-label="Checking your session" className="loading-panel min-h-screen" />;
  return user ? <Outlet /> : <Navigate replace to="/login" />;
}

function AppRoutes() {
  return (
    <Suspense fallback={<div aria-label="Loading page" className="loading-panel min-h-screen" />}>
      <Routes>
        <Route element={<LandingPage />} path="/" />
        <Route element={<AuthPage mode="login" />} path="/login" />
        <Route element={<AuthPage mode="register" />} path="/register" />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />} path="/app">
            <Route element={<DashboardPage />} index />
            <Route element={<ResumeManagementPage />} path="resumes" />
            <Route element={<JobsPage />} path="jobs" />
            <Route element={<AnalyzePage />} path="analyze" />
            <Route element={<AnalysisResultsPage />} path="analysis/:analysisId" />
            <Route element={<HistoryPage />} path="history" />
            <Route element={<TrackerPage />} path="tracker" />
            <Route element={<SettingsPage />} path="settings" />
          </Route>
        </Route>
        <Route element={<Navigate replace to="/" />} path="*" />
      </Routes>
    </Suspense>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}