import { useEffect, useMemo, useRef, useState, type DragEvent, type FormEvent } from "react";
import {
  ArrowDownToLine,
  ArrowUpRight,
  BriefcaseBusiness,
  Check,
  CircleHelp,
  FileSearch,
  Lightbulb,
  LoaderCircle,
  Search,
  Sparkles,
  Target,
  UploadCloud,
  X,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, getApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";

const ANALYSIS_REQUEST_TIMEOUT_MS = 300_000;
const MAX_RESUME_SIZE_BYTES = 10 * 1024 * 1024;
const MIN_JOB_DESCRIPTION_LENGTH = 30;
const MAX_JOB_DESCRIPTION_LENGTH = 50_000;

interface ResumeRecord {
  id: number;
  filename: string;
  parsed_data: { skills?: string[] };
}

interface JobRecord {
  id: number;
  title: string;
  company: string | null;
  parsed_data: { required_skills: string[]; preferred_skills: string[] };
}

interface AnalysisSummary {
  id: number;
  resume_id: number;
  resume_filename: string;
  job_description_id: number;
  job_title: string;
  company: string | null;
  overall_score: number;
  created_at: string;
}

interface SkillFinding {
  skill: string;
  category: string;
  match_type?: "matched" | "partial";
  evidence?: string;
  explanation?: string;
}

interface AnalysisDetails {
  required_skills_match_percentage: number | null;
  keyword_match_percentage: number;
  experience_relevance_percentage: number | null;
  education_relevance_percentage: number | null;
  project_relevance_percentage: number | null;
  semantic_similarity_percentage: number;
  matched_skills: SkillFinding[];
  partially_matched_skills: SkillFinding[];
  matched_keywords?: string[];
  missing_required_skills: SkillFinding[];
  missing_preferred_skills: SkillFinding[];
  missing_skills: SkillFinding[];
  important_missing_keywords: string[];
  resume_strengths?: string[];
  areas_to_improve?: string[];
  relevant_sections: Array<{ section: string; tfidf_similarity: number; semantic_similarity: number }>;
  improvement_suggestions: string[];
  skills_to_learn: string[];
  section_feedback: Record<string, string>;
  scoring_note: string;
}

interface BreakdownPart {
  score: number | null;
  available: boolean;
  configured_weight: number;
  effective_weight_percent: number;
}

interface AnalysisRecord extends AnalysisSummary {
  breakdown: Record<string, BreakdownPart>;
  details: AnalysisDetails;
}

const STATUS_OPTIONS = ["Applied", "In Progress", "Interview", "Rejected", "Selected"] as const;
type ApplicationStatus = (typeof STATUS_OPTIONS)[number];

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB"];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(value < 10 ? 1 : 0)} ${units[unitIndex]}`;
}

export function AnalyzePage() {
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [dragging, setDragging] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);

  function selectFile(selected?: File) {
    if (!selected) return;
    setError("");
    if (!/\.(pdf|docx)$/i.test(selected.name)) {
      setError("Choose a PDF or DOCX resume.");
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    if (selected.size > MAX_RESUME_SIZE_BYTES) {
      setError("The maximum resume size is 10 MB.");
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    setFile(selected);
    setUploadProgress(null);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    if (event.dataTransfer.files.length > 1) {
      setError("Choose one resume file at a time.");
      return;
    }
    selectFile(event.dataTransfer.files[0]);
  }

  function removeFile() {
    setFile(null);
    setUploadProgress(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (!file) {
      setError("Upload a PDF or DOCX resume before analyzing.");
      return;
    }
    const jobText = jobDescription.trim();
    if (jobText.length < MIN_JOB_DESCRIPTION_LENGTH) {
      setError(`Paste a job description with at least ${MIN_JOB_DESCRIPTION_LENGTH} characters.`);
      return;
    }

    setAnalyzing(true);
    setUploadProgress(0);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("job_description", jobText);
      const { data } = await api.post<AnalysisRecord>("/analyses/upload", formData, {
        timeout: ANALYSIS_REQUEST_TIMEOUT_MS,
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            setUploadProgress(
              Math.min(100, Math.round((progressEvent.loaded / progressEvent.total) * 100)),
            );
          }
        },
      });
      navigate(`/app/analysis/${data.id}`);
    } catch (requestError) {
      setError(getApiError(requestError));
    } finally {
      setAnalyzing(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-7">
      <div>
        <p className="eyebrow">EVIDENCE-BASED COMPARISON</p>
        <h1 className="page-title mt-2">Resume Analyzer</h1>
        <p className="mt-2 text-sm leading-6 text-muted">
          Upload your resume and paste the complete job description. The analysis uses only the text you provide.
        </p>
      </div>
      <form className="space-y-6" noValidate onSubmit={submit}>
        <section aria-labelledby="resume-upload-heading" className="panel">
          <h2 className="section-title" id="resume-upload-heading">Upload Resume</h2>
          <p className="mt-2 text-sm text-muted">Select a PDF or DOCX file from your computer, or drag it into the area below. Maximum size: 10 MB.</p>
          <div
            className={`upload-zone mt-5 ${dragging ? "upload-zone-active" : ""}`}
            onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
            onDragLeave={(event) => { event.preventDefault(); setDragging(false); }}
            onDragOver={(event) => event.preventDefault()}
            onDrop={handleDrop}
          >
            <span className="grid h-14 w-14 place-items-center rounded-2xl bg-blue-50 text-brand"><UploadCloud size={26} /></span>
            <p className="mt-4 font-semibold">{file ? "Resume selected" : "Drop your resume here"}</p>
            <input
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              aria-label="Choose a PDF or DOCX resume"
              className="sr-only"
              onChange={(event) => selectFile(event.target.files?.[0])}
              ref={inputRef}
              type="file"
            />
            <button
              className="btn-secondary mt-4"
              disabled={analyzing}
              onClick={() => inputRef.current?.click()}
              type="button"
            >
              {file ? "Replace resume" : "Choose resume"}
            </button>
            {file && (
              <div className="mt-4 flex flex-wrap items-center justify-center gap-3" role="status">
                <span className="text-sm font-semibold text-ink">{file.name}</span>
                <span className="text-sm text-muted">{formatFileSize(file.size)}</span>
                <button
                  aria-label="Remove selected resume"
                  className="inline-flex items-center gap-1 text-sm font-medium text-rose-700 hover:underline"
                  disabled={analyzing}
                  onClick={removeFile}
                  type="button"
                >
                  <X size={15} /> Remove
                </button>
              </div>
            )}
          </div>
        </section>

        <section aria-labelledby="job-description-heading" className="panel">
          <h2 className="section-title" id="job-description-heading">Paste Job Description</h2>
          <p className="mt-2 text-sm text-muted">Paste the complete role description, including requirements, responsibilities, and qualifications.</p>
          <label className="field-label mt-5">
            Job description text
            <textarea
              aria-describedby="job-description-help"
              className="field-control mt-2 min-h-56"
              maxLength={MAX_JOB_DESCRIPTION_LENGTH}
              minLength={MIN_JOB_DESCRIPTION_LENGTH}
              onChange={(event) => setJobDescription(event.target.value)}
              placeholder="Paste the full job description here. Include required and preferred skills, experience, education, responsibilities, and qualifications."
              required
              value={jobDescription}
            />
          </label>
          <div className="mt-2 flex justify-between gap-3 text-xs text-muted">
            <span id="job-description-help">At least {MIN_JOB_DESCRIPTION_LENGTH} non-whitespace characters.</span>
            <span>{jobDescription.length.toLocaleString()} / {MAX_JOB_DESCRIPTION_LENGTH.toLocaleString()}</span>
          </div>
        </section>

        {error && <p className="notice-error" role="alert">{error}</p>}
        {analyzing && (
          <section aria-live="polite" className="panel" role="status">
            <div className="flex items-center gap-3">
              <LoaderCircle aria-hidden="true" className="animate-spin text-brand" size={20} />
              <div>
                <p className="font-semibold">
                  {uploadProgress !== null && uploadProgress < 100
                    ? `Uploading resume… ${uploadProgress}%`
                    : "Resume uploaded. Analyzing your documents…"}
                </p>
                <p className="mt-1 text-sm text-muted">The first analysis may take longer while the semantic model loads.</p>
              </div>
            </div>
            {uploadProgress !== null && (
              <progress
                aria-label="Resume upload progress"
                className="mt-4 h-2 w-full accent-brand"
                max={100}
                value={uploadProgress}
              />
            )}
          </section>
        )}
        <button className="btn-primary w-full justify-center" disabled={analyzing} type="submit">
          {analyzing ? <><LoaderCircle className="animate-spin" size={17} /> Analyzing Resume…</> : <><Sparkles size={17} /> Analyze Resume</>}
        </button>
        <p className="text-center text-xs leading-5 text-muted">
          Your original file is processed and discarded; extracted text and analysis are saved to your account. Scores are estimates, not an employer ATS score or guarantee of selection.
        </p>
      </form>
    </div>
  );
}

export function AnalysisResultsPage() {
  const { analysisId } = useParams();
  const [analysis, setAnalysis] = useState<AnalysisRecord | null>(null);
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [tracking, setTracking] = useState(false);
  const [success, setSuccess] = useState("");

  useEffect(() => {
    api
      .get<AnalysisRecord>(`/analyses/${analysisId}`)
      .then(({ data }) => setAnalysis(data))
      .catch((requestError: unknown) => setError(getApiError(requestError)));
  }, [analysisId]);

  async function downloadReport() {
    if (!analysis) return;
    setDownloading(true);
    setError("");
    try {
      const response = await api.get(`/analyses/${analysis.id}/report`, { responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `analysis-${analysis.id}.pdf`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(getApiError(requestError));
    } finally {
      setDownloading(false);
    }
  }

  async function trackApplication() {
    if (!analysis) return;
    setTracking(true);
    setError("");
    setSuccess("");
    try {
      await api.post("/applications", { job_description_id: analysis.job_description_id });
      setSuccess("This job is now in your tracker.");
    } catch (requestError) {
      setError(getApiError(requestError));
    } finally {
      setTracking(false);
    }
  }

  if (error && !analysis) return <p className="notice-error" role="alert">{error}</p>;
  if (!analysis) return <div aria-label="Loading analysis" className="loading-panel" />;

  const details = analysis.details;
  const scoreColor = analysis.overall_score >= 75 ? "text-emerald-600" : analysis.overall_score >= 50 ? "text-amber-600" : "text-rose-600";
  const fullyMatchedSkills = details.matched_skills.filter((item) => item.match_type !== "partial");
  const partiallyMatchedSkills = details.partially_matched_skills;
  const resumeStrengths = details.resume_strengths?.length
    ? details.resume_strengths
    : fullyMatchedSkills.map((item) => `Extracted resume text matches ${item.skill}.`);
  const areasToImprove = details.areas_to_improve?.length
    ? details.areas_to_improve
    : details.improvement_suggestions;
  const breakdownLabels: Record<string, string> = {
    required_skills: "Required skills",
    keyword_match: "TF-IDF keyword match",
    experience: "Experience relevance",
    education: "Education relevance",
    project_relevance: "Project relevance",
  };

  return (
    <div className="space-y-7">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="eyebrow">ESTIMATED COMPATIBILITY</p>
          <h1 className="page-title mt-2">{analysis.job_title}</h1>
          <p className="mt-2 text-sm text-muted">{analysis.company || "Company not specified"} · Compared with {analysis.resume_filename}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn-secondary" disabled={downloading} onClick={() => void downloadReport()} type="button">
            <ArrowDownToLine size={16} /> {downloading ? "Preparing…" : "Download PDF"}
          </button>
          <button className="btn-primary" disabled={tracking} onClick={() => void trackApplication()} type="button">
            {tracking ? "Saving…" : "Track this job"}
          </button>
        </div>
      </div>

      {error && <p className="notice-error" role="alert">{error}</p>}
      {success && <p className="notice-success" role="status">{success}</p>}

      <section className="grid gap-5 lg:grid-cols-[0.8fr_1.2fr]">
        <article className="panel flex flex-col items-center justify-center text-center">
          <div aria-label={`Estimated compatibility ${analysis.overall_score} out of 100`} className="score-ring" style={{ background: `conic-gradient(#3767e8 ${analysis.overall_score}%, #e8edf5 0)` }}>
            <div className="score-ring-inner">
              <strong className={scoreColor}>{analysis.overall_score}</strong>
              <span>out of 100</span>
            </div>
          </div>
          <p className="mt-4 text-sm font-semibold">Estimated compatibility</p>
          <p className="mt-2 max-w-xs text-xs leading-5 text-muted">This explainable estimate does not represent or predict any employer&apos;s internal ATS score.</p>
        </article>
        <article className="panel">
          <div className="flex items-start gap-3">
            <span className="rounded-xl bg-blue-50 p-2.5 text-brand"><Target size={19} /></span>
            <div><h2 className="section-title">Score breakdown</h2><p className="mt-1 text-sm text-muted">Unavailable evidence is excluded and remaining configured weights are normalized.</p></div>
          </div>
          <div className="mt-6 space-y-5">
            {Object.entries(analysis.breakdown).map(([key, item]) => (
              <div key={key}>
                <div className="mb-2 flex items-center justify-between gap-4 text-sm">
                  <span className="font-medium">{breakdownLabels[key] || key}</span>
                  <span className="text-muted">{item.score === null ? "Not assessed" : `${item.score}%`} <span className="text-xs">· {item.effective_weight_percent}% weight</span></span>
                </div>
                <div aria-label={`${breakdownLabels[key] || key} score`} className="h-2 overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-brand" style={{ width: `${item.score ?? 0}%` }} />
                </div>
              </div>
            ))}
          </div>
          <p className="mt-5 rounded-xl bg-slate-50 p-3 text-xs leading-5 text-muted">Semantic similarity: {details.semantic_similarity_percentage}% · TF-IDF keyword match: {details.keyword_match_percentage}%</p>
        </article>
      </section>

      <section className="grid gap-5 lg:grid-cols-3">
        <article className="panel">
          <div className="flex items-center gap-2"><Check className="text-emerald-600" size={19} /><h2 className="section-title">Matched skills</h2></div>
          <div className="mt-4 flex flex-wrap gap-2">
            {fullyMatchedSkills.length ? fullyMatchedSkills.map((item) => <span className="skill-tag skill-tag-match" key={`${item.category}-${item.skill}`}>{item.skill}</span>) : <p className="text-sm text-muted">No fully matched skills were detected.</p>}
          </div>
          <p className="mt-4 text-xs text-muted">Required skill match: {details.required_skills_match_percentage === null ? "Not assessed" : `${details.required_skills_match_percentage}%`}</p>
        </article>
        <article className="panel">
          <div className="flex items-center gap-2"><CircleHelp className="text-amber-600" size={19} /><h2 className="section-title">Partially matched skills</h2></div>
          <div className="mt-4 flex flex-wrap gap-2">
            {partiallyMatchedSkills.length ? partiallyMatchedSkills.map((item) => <span className="skill-tag skill-tag-partial" key={`${item.category}-${item.skill}`}>{item.skill} · partial</span>) : <p className="text-sm text-muted">No partial skill matches were detected.</p>}
          </div>
          <p className="mt-4 text-xs text-muted">Partial evidence is not counted as a complete skill match.</p>
        </article>
        <article className="panel">
          <div className="flex items-center gap-2"><CircleHelp className="text-amber-600" size={19} /><h2 className="section-title">Missing skills</h2></div>
          {details.missing_skills.length ? (
            <ul className="mt-4 space-y-3">
              {details.missing_skills.map((item) => <li className="rounded-xl bg-amber-50/70 p-3" key={`${item.category}-${item.skill}`}>
                <div className="flex items-center justify-between gap-3"><span className="font-semibold">{item.skill}</span><span className="text-xs text-muted">{item.category}</span></div>
                <p className="mt-1 text-sm leading-5 text-muted">{item.explanation}</p>
              </li>)}
            </ul>
          ) : <p className="mt-4 text-sm text-muted">No missing required or preferred skills were detected in the parsed job description.</p>}
        </article>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <article className="panel">
          <h2 className="section-title">Relevant resume sections</h2>
          {details.relevant_sections.length ? (
            <div className="mt-4 space-y-3">
              {details.relevant_sections.map((section) => <div className="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3" key={section.section}>
                <span className="font-medium">{section.section}</span>
                <span className="text-sm text-muted">TF-IDF {section.tfidf_similarity}% · Semantic {section.semantic_similarity}%</span>
              </div>)}
            </div>
          ) : <p className="mt-3 text-sm text-muted">No standard resume sections were confidently detected.</p>}
        </article>
        <article className="panel">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="section-title">Keyword matching</h2>
            <span className="score-pill">{details.keyword_match_percentage}%</span>
          </div>
          <p className="mt-1 text-sm text-muted">TF-IDF cosine similarity between the supplied job description and resume text.</p>
          <h3 className="mt-5 text-sm font-semibold">Matched keywords</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {details.matched_keywords?.length ? details.matched_keywords.map((keyword) => <span className="skill-tag" key={keyword}>{keyword}</span>) : <p className="text-sm text-muted">No matching keywords were detected.</p>}
          </div>
          <h3 className="mt-5 text-sm font-semibold">Important keywords to review</h3>
          <p className="mt-1 text-xs text-muted">Only consider these if they truthfully describe your experience.</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {details.important_missing_keywords.length ? details.important_missing_keywords.map((keyword) => <span className="keyword-tag" key={keyword}>{keyword}</span>) : <p className="text-sm text-muted">No high-priority unmatched keywords found.</p>}
          </div>
        </article>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <article className="panel">
          <div className="flex items-center gap-2"><Check className="text-emerald-600" size={19} /><h2 className="section-title">Resume strengths</h2></div>
          {resumeStrengths.length ? (
            <ul className="mt-4 space-y-3">{resumeStrengths.map((strength) => <li className="flex gap-2 text-sm leading-6 text-slate-700" key={strength}><Check aria-hidden="true" className="mt-1 shrink-0 text-emerald-600" size={15} />{strength}</li>)}</ul>
          ) : <p className="mt-4 text-sm text-muted">No clear strengths could be confidently extracted from the supplied resume text.</p>}
        </article>
        <article className="panel">
          <div className="flex items-center gap-2"><Lightbulb className="text-amber-500" size={19} /><h2 className="section-title">Areas to improve</h2></div>
          {areasToImprove.length ? (
            <ul className="mt-4 space-y-3">{areasToImprove.map((area) => <li className="flex gap-2 text-sm leading-6 text-slate-700" key={area}><span aria-hidden="true" className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />{area}</li>)}</ul>
          ) : <p className="mt-4 text-sm text-muted">No specific improvement area was identified from the available evidence.</p>}
        </article>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <article className="panel">
          <div className="flex items-center gap-2"><Lightbulb className="text-amber-500" size={20} /><h2 className="section-title">Actionable improvements</h2></div>
          <ul className="mt-4 space-y-3">{details.improvement_suggestions.map((suggestion, index) => <li className="flex gap-3 text-sm leading-6 text-slate-700" key={`${index}-${suggestion}`}><span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-blue-50 text-xs font-bold text-brand">{index + 1}</span>{suggestion}</li>)}</ul>
        </article>
        <article className="panel">
          <h2 className="section-title">Section-by-section feedback</h2>
          <div className="mt-4 space-y-4">
            {Object.entries(details.section_feedback).map(([section, feedback]) => <div key={section}>
              <h3 className="text-sm font-semibold capitalize">{section}</h3>
              <p className="mt-1 text-sm leading-6 text-muted">{feedback}</p>
            </div>)}
          </div>
          {details.skills_to_learn.length > 0 && <div className="mt-5 rounded-xl bg-blue-50 p-4">
            <h3 className="text-sm font-semibold text-ink">Skills to genuinely learn</h3>
            <ul className="mt-2 space-y-2 text-sm text-muted">{details.skills_to_learn.map((item) => <li key={item}>• {item}</li>)}</ul>
          </div>}
        </article>
      </section>
      <p className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-xs leading-5 text-muted">{details.scoring_note}</p>
    </div>
  );
}

export function HistoryPage() {
  const [analyses, setAnalyses] = useState<AnalysisSummary[]>([]);
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [resumes, setResumes] = useState<ResumeRecord[]>([]);
  const [search, setSearch] = useState("");
  const [resumeFilter, setResumeFilter] = useState("");
  const [jobFilter, setJobFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.get<JobRecord[]>("/jobs"), api.get<ResumeRecord[]>("/resumes")])
      .then(([jobResponse, resumeResponse]) => {
        setJobs(jobResponse.data);
        setResumes(resumeResponse.data);
      })
      .catch((requestError: unknown) => setError(getApiError(requestError)));
  }, []);

  useEffect(() => {
    setLoading(true);
    api
      .get<AnalysisSummary[]>("/analyses", {
        params: {
          limit: 200,
          resume_id: resumeFilter || undefined,
          job_description_id: jobFilter || undefined,
        },
      })
      .then(({ data }) => setAnalyses(data))
      .catch((requestError: unknown) => setError(getApiError(requestError)))
      .finally(() => setLoading(false));
  }, [resumeFilter, jobFilter]);

  const visible = useMemo(
    () => analyses.filter((item) => `${item.job_title} ${item.company || ""} ${item.resume_filename}`.toLowerCase().includes(search.toLowerCase())),
    [analyses, search],
  );

  return (
    <div className="space-y-6">
      <div><p className="eyebrow">YOUR COMPARISONS</p><h1 className="page-title mt-2">Analysis history</h1><p className="mt-2 text-sm text-muted">Search and filter scores saved from your previous resume/job comparisons.</p></div>
      <section className="panel">
        <div className="grid gap-3 md:grid-cols-3">
          <label className="relative"><span className="sr-only">Search analyses</span><Search className="absolute left-3 top-3 text-muted" size={16} /><input className="field-control pl-9" onChange={(event) => setSearch(event.target.value)} placeholder="Search role or resume" value={search} /></label>
          <label><span className="sr-only">Filter by resume</span><select className="field-control" onChange={(event) => setResumeFilter(event.target.value)} value={resumeFilter}><option value="">All resumes</option>{resumes.map((resume) => <option key={resume.id} value={resume.id}>{resume.filename}</option>)}</select></label>
          <label><span className="sr-only">Filter by job</span><select className="field-control" onChange={(event) => setJobFilter(event.target.value)} value={jobFilter}><option value="">All jobs</option>{jobs.map((job) => <option key={job.id} value={job.id}>{job.title}</option>)}</select></label>
        </div>
      </section>
      {error && <p className="notice-error" role="alert">{error}</p>}
      {loading ? <div className="loading-panel" /> : visible.length === 0 ? (
        <div className="empty-card"><FileSearch className="mx-auto text-slate-300" size={28} /><p className="mt-3 font-semibold">No analyses match these filters</p><p className="mt-1 text-sm text-muted">Run a comparison to start building your history.</p><Link className="mt-4 inline-flex text-sm font-semibold text-brand" to="/app/analyze">Create an analysis</Link></div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
          <table className="data-table">
            <thead><tr><th>Job</th><th>Resume</th><th>Date</th><th>Estimate</th><th /></tr></thead>
            <tbody>{visible.map((analysis) => <tr key={analysis.id}>
              <td><span className="font-semibold">{analysis.job_title}</span><span className="block text-xs text-muted">{analysis.company || "Company not specified"}</span></td>
              <td>{analysis.resume_filename}</td><td>{new Date(analysis.created_at).toLocaleDateString()}</td>
              <td><span className="score-pill">{analysis.overall_score}%</span></td>
              <td><Link aria-label={`Open ${analysis.job_title} result`} className="inline-flex items-center gap-1 text-sm font-semibold text-brand" to={`/app/analysis/${analysis.id}`}>Details <ArrowUpRight size={15} /></Link></td>
            </tr>)}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}

interface ApplicationRecord {
  id: number;
  job_description_id: number;
  job_title: string;
  company: string | null;
  status: ApplicationStatus;
  notes: string | null;
  updated_at: string;
  latest_score: number | null;
}

export function TrackerPage() {
  const [applications, setApplications] = useState<ApplicationRecord[]>([]);
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [selectedJob, setSelectedJob] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function refresh() {
    setLoading(true);
    try {
      const [applicationResponse, jobResponse] = await Promise.all([
        api.get<ApplicationRecord[]>("/applications", { params: statusFilter ? { status: statusFilter } : undefined }),
        api.get<JobRecord[]>("/jobs"),
      ]);
      setApplications(applicationResponse.data);
      setJobs(jobResponse.data);
    } catch (requestError) {
      setError(getApiError(requestError));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refresh(); }, [statusFilter]);

  async function addJob(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSuccess("");
    try {
      const { data } = await api.post<ApplicationRecord>("/applications", { job_description_id: Number(selectedJob) });
      setApplications((current) => [data, ...current]);
      setSelectedJob("");
      setSuccess("Job added to your application tracker.");
    } catch (requestError) {
      setError(getApiError(requestError));
    }
  }

  async function updateStatus(application: ApplicationRecord, nextStatus: ApplicationStatus) {
    try {
      const { data } = await api.patch<ApplicationRecord>(`/applications/${application.id}`, { status: nextStatus });
      setApplications((current) => current.map((item) => item.id === data.id ? data : item));
    } catch (requestError) {
      setError(getApiError(requestError));
    }
  }

  async function updateNotes(application: ApplicationRecord, notes: string) {
    try {
      const { data } = await api.patch<ApplicationRecord>(`/applications/${application.id}`, { notes });
      setApplications((current) => current.map((item) => item.id === data.id ? data : item));
    } catch (requestError) {
      setError(getApiError(requestError));
    }
  }

  async function deleteApplication(application: ApplicationRecord) {
    try {
      await api.delete(`/applications/${application.id}`);
      setApplications((current) => current.filter((item) => item.id !== application.id));
    } catch (requestError) {
      setError(getApiError(requestError));
    }
  }

  const trackedIds = new Set(applications.map((application) => application.job_description_id));
  const availableJobs = jobs.filter((job) => !trackedIds.has(job.id));

  return (
    <div className="space-y-6">
      <div><p className="eyebrow">APPLICATION PIPELINE</p><h1 className="page-title mt-2">Job tracker</h1><p className="mt-2 text-sm text-muted">Update your real application progress and keep useful notes in one place.</p></div>
      <section className="panel">
        <h2 className="section-title">Track a saved job</h2>
        <form className="mt-4 flex flex-col gap-3 sm:flex-row" onSubmit={addJob}>
          <label className="flex-1"><span className="sr-only">Choose a saved job</span><select className="field-control" onChange={(event) => setSelectedJob(event.target.value)} required value={selectedJob}><option value="">Choose a saved job description</option>{availableJobs.map((job) => <option key={job.id} value={job.id}>{job.title}{job.company ? ` · ${job.company}` : ""}</option>)}</select></label>
          <button className="btn-primary" disabled={!selectedJob} type="submit">Add to tracker</button>
        </form>
      </section>
      {error && <p className="notice-error" role="alert">{error}</p>}
      {success && <p className="notice-success" role="status">{success}</p>}
      <section className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="section-title">Tracked opportunities <span className="text-sm font-medium text-muted">({applications.length})</span></h2>
        <label className="flex items-center gap-2 text-sm text-muted">Filter status
          <select className="field-control py-2" onChange={(event) => setStatusFilter(event.target.value)} value={statusFilter}><option value="">All statuses</option>{STATUS_OPTIONS.map((item) => <option key={item}>{item}</option>)}</select>
        </label>
      </section>
      {loading ? <div className="loading-panel" /> : applications.length === 0 ? (
        <div className="empty-card"><BriefcaseBusiness className="mx-auto text-slate-300" size={28} /><p className="mt-3 font-semibold">Your tracker is ready</p><p className="mt-1 text-sm text-muted">Add a saved job and update its status as your application progresses.</p></div>
      ) : <div className="grid gap-4 xl:grid-cols-2">
        {applications.map((application) => <article className="panel" key={application.id}>
          <div className="flex items-start justify-between gap-3"><div><p className="text-sm font-semibold text-brand">{application.company || "Company not specified"}</p><h3 className="mt-1 font-bold">{application.job_title}</h3></div><button aria-label={`Remove ${application.job_title} from tracker`} className="icon-button text-muted hover:text-rose-600" onClick={() => void deleteApplication(application)} type="button"><X size={17} /></button></div>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <label className="text-sm font-medium">Application status
              <select aria-label={`${application.job_title} status`} className="field-control mt-1 py-2" onChange={(event) => void updateStatus(application, event.target.value as ApplicationStatus)} value={application.status}>{STATUS_OPTIONS.map((item) => <option key={item}>{item}</option>)}</select>
            </label>
            <div className="text-right"><p className="text-xs text-muted">Latest estimate</p><p className="mt-1 text-xl font-bold">{application.latest_score === null ? "—" : `${application.latest_score}%`}</p></div>
          </div>
          <label className="field-label mt-4">Notes<textarea aria-label={`${application.job_title} notes`} className="field-control mt-1 min-h-20" maxLength={4000} onBlur={(event) => { if (event.currentTarget.value !== (application.notes || "")) void updateNotes(application, event.currentTarget.value); }} defaultValue={application.notes || ""} /></label>
          <p className="mt-2 text-xs text-muted">Updated {new Date(application.updated_at).toLocaleDateString()}</p>
        </article>)}
      </div>}
    </div>
  );
}

export function SettingsPage() {
  const { user, updateProfile } = useAuth();
  const [name, setName] = useState(user?.full_name || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => setName(user?.full_name || ""), [user?.full_name]);

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await updateProfile(name);
      setSuccess("Profile updated.");
    } catch (requestError) {
      setError(getApiError(requestError));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div><p className="eyebrow">ACCOUNT</p><h1 className="page-title mt-2">Profile & settings</h1><p className="mt-2 text-sm text-muted">Manage the personal details associated with your account.</p></div>
      <form className="panel space-y-5" onSubmit={saveProfile}>
        <h2 className="section-title">Profile details</h2>
        <label className="field-label">Full name<input className="field-control mt-2" maxLength={120} minLength={1} onChange={(event) => setName(event.target.value)} required value={name} /></label>
        <label className="field-label">Email address<input className="field-control mt-2 bg-slate-50" readOnly value={user?.email || ""} /></label>
        {error && <p className="notice-error" role="alert">{error}</p>}
        {success && <p className="notice-success" role="status">{success}</p>}
        <button className="btn-primary" disabled={saving || name.trim() === user?.full_name} type="submit">{saving ? "Saving…" : "Save profile"}</button>
      </form>
      <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
        <h2 className="text-sm font-bold text-amber-900">Your data and privacy</h2>
        <p className="mt-2 text-sm leading-6 text-amber-900/80">Uploaded original files are processed and discarded; extracted resume text and analysis results are saved to your account. Deleting a resume removes its associated analyses.</p>
      </section>
    </div>
  );
}