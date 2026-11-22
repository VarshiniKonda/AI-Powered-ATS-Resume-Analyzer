import { useState, type FormEvent } from "react";
import { ArrowLeft, BriefcaseBusiness, CheckCircle2 } from "lucide-react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { getApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";

interface AuthPageProps {
  mode: "login" | "register";
}

export function AuthPage({ mode }: AuthPageProps) {
  const isRegister = mode === "register";
  const { isLoading, login, register, user } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (!isLoading && user) return <Navigate to="/app" replace />;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      if (isRegister) await register(fullName, email, password);
      else await login(email, password);
      navigate("/app", { replace: true });
    } catch (requestError) {
      setError(getApiError(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen bg-white lg:grid-cols-[1fr_0.85fr]">
      <section className="flex flex-col px-6 py-7 sm:px-12 lg:px-20">
        <Link className="flex items-center gap-3" to="/">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand text-white">
            <BriefcaseBusiness size={20} />
          </span>
          <span className="text-lg font-bold tracking-tight">matchwise</span>
        </Link>
        <div className="mx-auto my-auto w-full max-w-md py-12">
          <Link className="mb-8 inline-flex items-center gap-2 text-sm text-muted hover:text-ink" to="/">
            <ArrowLeft size={16} /> Back to home
          </Link>
          <p className="text-sm font-semibold text-brand">
            {isRegister ? "START WITH A CLEARER MATCH" : "WELCOME BACK"}
          </p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight">
            {isRegister ? "Create your account" : "Sign in to your workspace"}
          </h1>
          <p className="mt-3 leading-6 text-muted">
            {isRegister
              ? "Save your resumes, compare opportunities, and keep your search organized."
              : "Pick up where you left off with your resume and job matches."}
          </p>

          <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
            {isRegister && (
              <label className="block text-sm font-medium">
                Full name
                <input
                  autoComplete="name"
                  className="field-control mt-2"
                  maxLength={120}
                  onChange={(event) => setFullName(event.target.value)}
                  required
                  value={fullName}
                />
              </label>
            )}
            <label className="block text-sm font-medium">
              Email address
              <input
                autoComplete="email"
                className="field-control mt-2"
                onChange={(event) => setEmail(event.target.value)}
                required
                type="email"
                value={email}
              />
            </label>
            <label className="block text-sm font-medium">
              Password
              <input
                autoComplete={isRegister ? "new-password" : "current-password"}
                className="field-control mt-2"
                minLength={isRegister ? 8 : 1}
                onChange={(event) => setPassword(event.target.value)}
                required
                type="password"
                value={password}
              />
              {isRegister && (
                <span className="mt-2 block text-xs text-muted">Use at least 8 characters.</span>
              )}
            </label>
            {error && (
              <p className="rounded-xl border border-rose-100 bg-rose-50 px-4 py-3 text-sm text-rose-700" role="alert">
                {error}
              </p>
            )}
            <button className="btn-primary w-full" disabled={submitting || isLoading} type="submit">
              {submitting ? "Please wait…" : isRegister ? "Create account" : "Sign in"}
            </button>
          </form>

          <p className="mt-6 text-sm text-muted">
            {isRegister ? "Already have an account?" : "New to Matchwise?"}{" "}
            <Link
              className="font-semibold text-brand hover:underline"
              to={isRegister ? "/login" : "/register"}
            >
              {isRegister ? "Sign in" : "Create an account"}
            </Link>
          </p>
        </div>
        <p className="text-xs text-muted">
          Your resume text is private to your account. Scores are estimates, not employer ATS results.
        </p>
      </section>

      <aside className="relative hidden overflow-hidden bg-ink px-14 py-16 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -right-32 -top-32 h-96 w-96 rounded-full bg-blue-500/20 blur-3xl" />
        <div className="relative">
          <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-2 text-sm text-blue-100">
            <CheckCircle2 size={16} /> Built for honest, evidence-based applications
          </span>
        </div>
        <div className="relative max-w-xl">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-200">
            Your next step, made clearer
          </p>
          <h2 className="mt-5 text-4xl font-bold leading-tight">
            Understand the fit. Strengthen the story.
          </h2>
          <p className="mt-5 max-w-lg text-lg leading-8 text-slate-300">
            See matching evidence, identify gaps, and get practical suggestions without inventing skills or experience.
          </p>
        </div>
        <p className="relative text-sm text-slate-400">A thoughtful toolkit for your job search.</p>
      </aside>
    </main>
  );
}