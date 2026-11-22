import { useEffect, useRef, useState, type DragEvent, type FormEvent } from "react";
import { BriefcaseBusiness, FileText, LoaderCircle, Search, Trash2, UploadCloud } from "lucide-react";
import { api, getApiError } from "../api/client";

interface ResumeRecord {
  id: number;
  filename: string;
  parsed_data: {
    name?: string | null;
    email?: string | null;
    phone?: string | null;
    skills?: string[];
    education_level?: string | null;
    experience_years?: number | null;
    extraction_notes?: string[];
  };
  created_at: string;
}

interface JobRecord {
  id: number;
  title: string;
  company: string | null;
  content_text: string;
  parsed_data: {
    required_skills: string[];
    preferred_skills: string[];
    experience_years: number | null;
    education_level: string | null;
  };
  created_at: string;
}

function useRecords<T>(url: string) {
  const [records, setRecords] = useState<T[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const refresh = async (search?: string) => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get<T[]>(url, { params: search ? { search } : undefined });
      setRecords(data);
    } catch (requestError) {
      setError(getApiError(requestError));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, [url]);

  return { records, setRecords, error, setError, loading, refresh };
}

export function ResumeManagementPage() {
  const { records, setRecords, error, setError, loading, refresh } = useRecords<ResumeRecord>("/resumes");
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [success, setSuccess] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const selectFile = (selected?: File) => {
    setSuccess("");
    setError("");
    if (!selected) return;
    if (!/\.(pdf|docx)$/i.test(selected.name)) {
      setFile(null);
      setError("Choose a PDF or DOCX resume.");
      return;
    }
    if (selected.size > 10 * 1024 * 1024) {
      setFile(null);
      setError("The maximum resume size is 10 MB.");
      return;
    }
    setFile(selected);
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    selectFile(event.dataTransfer.files[0]);
  };

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    setUploading(true);
    setError("");
    setSuccess("");
    try {
      const { data } = await api.post<ResumeRecord>("/resumes", formData);
      setRecords((current) => [data, ...current]);
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
      setSuccess("Resume extracted and saved. Review the detected details below.");
    } catch (requestError) {
      setError(getApiError(requestError));
    } finally {
      setUploading(false);
    }
  }

  async function removeResume(id: number) {
    if (!window.confirm("Delete this resume and its associated analysis history?")) return;
    try {
      await api.delete(`/resumes/${id}`);
      setRecords((current) => current.filter((resume) => resume.id !== id));
      setSuccess("Resume and associated analysis data deleted.");
    } catch (requestError) {
      setError(getApiError(requestError));
    }
  }

  return (
    <div className="space-y-7">
      <div>
        <p className="eyebrow">RESUME LIBRARY</p>
        <h1 className="page-title mt-2">Your resumes</h1>
        <p className="mt-2 text-sm text-muted">Upload a PDF or DOCX to extract real text and review the detected details.</p>
      </div>
      <section className="panel">
        <form onSubmit={handleUpload}>
          <div
            className={`upload-zone ${dragging ? "upload-zone-active" : ""}`}
            onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
            onDragLeave={(event) => { event.preventDefault(); setDragging(false); }}
            onDragOver={(event) => event.preventDefault()}
            onDrop={handleDrop}
          >
            <span className="grid h-14 w-14 place-items-center rounded-2xl bg-blue-50 text-brand"><UploadCloud size={26} /></span>
            <h2 className="mt-4 text-lg font-semibold">Drop your resume here</h2>
            <p className="mt-1 text-sm text-muted">PDF or DOCX · 10 MB maximum · uploaded file is processed and not retained</p>
            <input
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              className="sr-only"
              onChange={(event) => selectFile(event.target.files?.[0])}
              ref={inputRef}
              type="file"
            />
            <button className="btn-secondary mt-5" onClick={() => inputRef.current?.click()} type="button">Browse files</button>
            {file && <p className="mt-4 text-sm font-semibold text-ink">{file.name}</p>}
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-muted">Only extracted text and parsed fields are saved to your account.</p>
            <button className="btn-primary" disabled={!file || uploading} type="submit">
              {uploading ? <><LoaderCircle className="animate-spin" size={16} /> Extracting…</> : "Upload and extract"}
            </button>
          </div>
        </form>
        {error && <p className="notice-error mt-4" role="alert">{error}</p>}
        {success && <p className="notice-success mt-4" role="status">{success}</p>}
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="section-title">Saved resumes <span className="ml-2 text-sm font-medium text-muted">({records.length})</span></h2>
          <button className="text-sm font-semibold text-brand" onClick={() => void refresh()} type="button">Refresh</button>
        </div>
        {loading ? <div className="loading-panel" /> : records.length === 0 ? (
          <div className="empty-card"><FileText className="mx-auto text-slate-300" size={28} /><p className="mt-3 font-semibold">No resumes yet</p><p className="mt-1 text-sm text-muted">Add your first resume to compare it with a real job description.</p></div>
        ) : (
          <div className="grid gap-4 xl:grid-cols-2">
            {records.map((resume) => (
              <article className="panel" key={resume.id}>
                <div className="flex items-start gap-4">
                  <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-slate-100 text-slate-600"><FileText size={20} /></span>
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate font-semibold">{resume.filename}</h3>
                    <p className="mt-1 text-xs text-muted">Added {new Date(resume.created_at).toLocaleDateString()}</p>
                  </div>
                  <button aria-label={`Delete ${resume.filename}`} className="icon-button text-muted hover:text-rose-600" onClick={() => void removeResume(resume.id)} type="button"><Trash2 size={17} /></button>
                </div>
                <div className="mt-5 grid gap-2 text-sm sm:grid-cols-2">
                  <p><span className="text-muted">Name:</span> {resume.parsed_data.name || "Not detected"}</p>
                  <p><span className="text-muted">Email:</span> {resume.parsed_data.email || "Not detected"}</p>
                  <p><span className="text-muted">Education:</span> {resume.parsed_data.education_level || "Not detected"}</p>
                  <p><span className="text-muted">Experience:</span> {resume.parsed_data.experience_years == null ? "Not reliably detected" : `${resume.parsed_data.experience_years} years`}</p>
                </div>
                <div className="mt-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted">Detected skills</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {(resume.parsed_data.skills || []).length ? resume.parsed_data.skills?.map((skill) => <span className="skill-tag" key={skill}>{skill}</span>) : <span className="text-sm text-muted">No catalogued skills detected.</span>}
                  </div>
                </div>
                {resume.parsed_data.extraction_notes?.map((note) => <p className="mt-4 text-xs leading-5 text-muted" key={note}>{note}</p>)}
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export function JobsPage() {
  const { records, setRecords, error, setError, loading, refresh } = useRecords<JobRecord>("/jobs");
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [content, setContent] = useState("");
  const [requiredSkills, setRequiredSkills] = useState("");
  const [preferredSkills, setPreferredSkills] = useState("");
  const [search, setSearch] = useState("");
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState("");

  async function saveJob(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const { data } = await api.post<JobRecord>("/jobs", {
        title: title || null,
        company: company || null,
        content_text: content,
        required_skills: requiredSkills.split(",").map((item) => item.trim()).filter(Boolean),
        preferred_skills: preferredSkills.split(",").map((item) => item.trim()).filter(Boolean),
      });
      setRecords((current) => [data, ...current]);
      setTitle("");
      setCompany("");
      setContent("");
      setRequiredSkills("");
      setPreferredSkills("");
      setSuccess("Job description saved and its requirements extracted.");
    } catch (requestError) {
      setError(getApiError(requestError));
    } finally {
      setSaving(false);
    }
  }

  async function searchJobs(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await refresh(search);
  }

  async function removeJob(job: JobRecord) {
    if (!window.confirm(`Delete ${job.title} and its analysis/application data?`)) return;
    try {
      await api.delete(`/jobs/${job.id}`);
      setRecords((current) => current.filter((record) => record.id !== job.id));
    } catch (requestError) {
      setError(getApiError(requestError));
    }
  }

  return (
    <div className="space-y-7">
      <div>
        <p className="eyebrow">OPPORTUNITY LIBRARY</p>
        <h1 className="page-title mt-2">Job descriptions</h1>
        <p className="mt-2 text-sm text-muted">Save real role descriptions and extract requirements for later comparison.</p>
      </div>
      <section className="panel">
        <h2 className="section-title">Add a job description</h2>
        <form className="mt-5 space-y-4" onSubmit={saveJob}>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="field-label">Job title (optional)<input className="field-control mt-2" maxLength={255} onChange={(e) => setTitle(e.target.value)} value={title} /></label>
            <label className="field-label">Company (optional)<input className="field-control mt-2" maxLength={255} onChange={(e) => setCompany(e.target.value)} value={company} /></label>
          </div>
          <label className="field-label">Job description<textarea className="field-control mt-2 min-h-44" maxLength={50000} minLength={30} onChange={(e) => setContent(e.target.value)} placeholder="Paste the complete job description. Requirements and preferred skills are extracted from its actual text." required value={content} /></label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="field-label">Required skills (optional, comma-separated)<input className="field-control mt-2" onChange={(e) => setRequiredSkills(e.target.value)} placeholder="Python, SQL, React" value={requiredSkills} /></label>
            <label className="field-label">Preferred skills (optional, comma-separated)<input className="field-control mt-2" onChange={(e) => setPreferredSkills(e.target.value)} placeholder="AWS, Kubernetes" value={preferredSkills} /></label>
          </div>
          {error && <p className="notice-error" role="alert">{error}</p>}
          {success && <p className="notice-success" role="status">{success}</p>}
          <button className="btn-primary" disabled={saving || content.trim().length < 30} type="submit">{saving ? "Saving…" : "Save job description"}</button>
        </form>
      </section>

      <section className="space-y-4">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <h2 className="section-title">Saved opportunities <span className="ml-2 text-sm font-medium text-muted">({records.length})</span></h2>
          <form className="flex gap-2" onSubmit={searchJobs}>
            <label className="sr-only" htmlFor="job-search">Search saved jobs</label>
            <input className="field-control min-w-0 sm:w-64" id="job-search" onChange={(e) => setSearch(e.target.value)} placeholder="Search title, company, text" value={search} />
            <button aria-label="Search jobs" className="btn-secondary px-3" type="submit"><Search size={17} /></button>
          </form>
        </div>
        {loading ? <div className="loading-panel" /> : records.length === 0 ? (
          <div className="empty-card"><BriefcaseBusiness className="mx-auto text-slate-300" size={28} /><p className="mt-3 font-semibold">No saved job descriptions</p><p className="mt-1 text-sm text-muted">Add the full text of a role to begin matching.</p></div>
        ) : records.map((job) => (
          <article className="panel" key={job.id}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div><p className="text-sm font-semibold text-brand">{job.company || "Company not specified"}</p><h3 className="mt-1 text-lg font-bold">{job.title}</h3></div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted">{new Date(job.created_at).toLocaleDateString()}</span>
                <button aria-label={`Delete ${job.title}`} className="icon-button text-muted hover:text-rose-600" onClick={() => void removeJob(job)} type="button"><Trash2 size={17} /></button>
              </div>
            </div>
            <p className="mt-4 line-clamp-3 text-sm leading-6 text-muted">{job.content_text}</p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div><p className="text-xs font-semibold uppercase tracking-wide text-muted">Required skills</p><SkillList skills={job.parsed_data.required_skills} /></div>
              <div><p className="text-xs font-semibold uppercase tracking-wide text-muted">Preferred skills</p><SkillList skills={job.parsed_data.preferred_skills} /></div>
            </div>
            <p className="mt-4 text-xs text-muted">
              {job.parsed_data.experience_years == null ? "Experience requirement not reliably extracted" : `${job.parsed_data.experience_years}+ years requested`}
              {" · "}
              {job.parsed_data.education_level || "Education requirement not detected"}
            </p>
          </article>
        ))}
      </section>
    </div>
  );
}

function SkillList({ skills }: { skills?: string[] }) {
  return <div className="mt-2 flex flex-wrap gap-2">{skills?.length ? skills.map((skill) => <span className="skill-tag" key={skill}>{skill}</span>) : <span className="text-sm text-muted">None detected</span>}</div>;
}