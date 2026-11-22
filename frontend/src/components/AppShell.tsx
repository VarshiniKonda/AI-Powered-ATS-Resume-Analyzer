import { useState } from "react";
import {
  BriefcaseBusiness,
  ChartNoAxesCombined,
  FileSearch,
  FileText,
  History,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings,
  X,
} from "lucide-react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const navigation = [
  { to: "/app", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/app/resumes", label: "My resumes", icon: FileText },
  { to: "/app/jobs", label: "Job descriptions", icon: BriefcaseBusiness },
  { to: "/app/analyze", label: "Resume Analyzer", icon: FileSearch },
  { to: "/app/history", label: "Analysis history", icon: History },
  { to: "/app/tracker", label: "Job tracker", icon: ChartNoAxesCombined },
  { to: "/app/settings", label: "Profile & settings", icon: Settings },
];

export function AppShell() {
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const closeMenu = () => setMobileOpen(false);

  return (
    <div className="min-h-screen bg-canvas text-ink">
      {mobileOpen && (
        <button
          aria-label="Close navigation"
          className="fixed inset-0 z-30 bg-slate-950/40 lg:hidden"
          onClick={closeMenu}
          type="button"
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-200 bg-white transition-transform lg:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-20 items-center gap-3 px-6">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand text-white">
            <BriefcaseBusiness size={20} />
          </span>
          <span className="text-lg font-bold tracking-tight">matchwise</span>
          <button
            aria-label="Close navigation"
            className="ml-auto rounded-lg p-2 text-muted hover:bg-slate-100 lg:hidden"
            onClick={closeMenu}
            type="button"
          >
            <X size={18} />
          </button>
        </div>
        <p className="px-6 pb-3 pt-5 text-[11px] font-bold uppercase tracking-[0.14em] text-slate-400">
          Workspace
        </p>
        <nav aria-label="Main navigation" className="flex-1 space-y-1 px-3">
          {navigation.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              end={end}
              key={to}
              onClick={closeMenu}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                  isActive
                    ? "bg-blue-50 text-brand"
                    : "text-slate-600 hover:bg-slate-50 hover:text-ink"
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-100 p-4">
          <div className="flex items-center gap-3 rounded-xl bg-slate-50 p-3">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-blue-100 text-sm font-bold text-brand">
              {user?.full_name.slice(0, 1).toUpperCase()}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold">{user?.full_name}</p>
              <p className="truncate text-xs text-muted">{user?.email}</p>
            </div>
            <button
              aria-label="Sign out"
              className="rounded-lg p-2 text-muted hover:bg-white hover:text-rose-600"
              onClick={handleLogout}
              title="Sign out"
              type="button"
            >
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur sm:px-7">
          <div className="flex items-center gap-3">
            <button
              aria-label="Open navigation"
              className="rounded-lg p-2 text-muted hover:bg-slate-100 lg:hidden"
              onClick={() => setMobileOpen(true)}
              type="button"
            >
              <Menu size={20} />
            </button>
            <span className="text-sm font-medium text-muted">
              {navigation.find((item) => item.to === location.pathname)?.label ?? "Workspace"}
            </span>
          </div>
          <span className="hidden text-xs text-muted sm:inline">
            Estimated insights, not an employer ATS score
          </span>
        </header>
        <main className="mx-auto max-w-7xl p-4 sm:p-7 lg:p-9">
          <Outlet />
        </main>
      </div>
    </div>
  );
}