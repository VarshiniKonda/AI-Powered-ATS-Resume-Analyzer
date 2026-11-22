import "@testing-library/jest-dom/vitest";
import { AxiosHeaders } from "axios";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api/client";
import { AnalysisResultsPage, AnalyzePage } from "./pages/AnalysisPages";

vi.mock("./api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
  getApiError: (error: unknown) =>
    error instanceof Error ? error.message : "The request failed.",
}));

const JOB_DESCRIPTION =
  "Senior Python Engineer. Required Python and FastAPI experience building reliable API services.";

function response<T>(data: T) {
  return {
    data,
    status: 200,
    statusText: "OK",
    headers: {},
    config: { headers: new AxiosHeaders() },
  };
}

function CurrentPath() {
  const location = useLocation();
  return <output data-testid="current-path">{location.pathname}</output>;
}

function renderAnalyzer() {
  return render(
    <MemoryRouter
      future={{ v7_relativeSplatPath: true, v7_startTransition: true }}
      initialEntries={["/app/analyze"]}
    >
      <Routes>
        <Route element={<AnalyzePage />} path="/app/analyze" />
        <Route element={<CurrentPath />} path="/app/analysis/:analysisId" />
      </Routes>
    </MemoryRouter>,
  );
}

function renderResults() {
  return render(
    <MemoryRouter
      future={{ v7_relativeSplatPath: true, v7_startTransition: true }}
      initialEntries={["/app/analysis/42"]}
    >
      <Routes>
        <Route element={<AnalysisResultsPage />} path="/app/analysis/:analysisId" />
      </Routes>
    </MemoryRouter>,
  );
}

function createResume(name = "candidate.pdf") {
  return new File(["actual resume text"], name, { type: "application/pdf" });
}

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

describe("direct resume analysis", () => {
  it("requires a resume and preserves pasted job text after validation errors", async () => {
    const user = userEvent.setup();
    renderAnalyzer();

    const description = screen.getByLabelText("Job description text");
    await user.type(description, JOB_DESCRIPTION);
    await user.click(screen.getByRole("button", { name: "Analyze Resume" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Upload a PDF or DOCX resume");
    expect(description).toHaveValue(JOB_DESCRIPTION);
    expect(api.post).not.toHaveBeenCalled();
  });

  it("displays the selected filename and size and supports removal", async () => {
    const user = userEvent.setup();
    renderAnalyzer();

    await user.upload(
      screen.getByLabelText("Choose a PDF or DOCX resume"),
      createResume(),
    );

    expect(screen.getByText("candidate.pdf")).toBeInTheDocument();
    expect(screen.getByText("18 B")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Remove selected resume" }));
    expect(screen.queryByText("candidate.pdf")).not.toBeInTheDocument();
  });

  it("rejects unsupported file types before submission", async () => {
    renderAnalyzer();

    fireEvent.change(
      screen.getByLabelText("Choose a PDF or DOCX resume"),
      {
        target: {
          files: [new File(["not a resume"], "notes.txt", { type: "text/plain" })],
        },
      },
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Choose a PDF or DOCX resume");
    expect(screen.queryByText("notes.txt")).not.toBeInTheDocument();
  });

  it("accepts a resume dropped into the upload area", () => {
    renderAnalyzer();
    const uploadZone = screen.getByText("Drop your resume here").parentElement;
    if (!uploadZone) throw new Error("Resume drop area was not rendered.");

    fireEvent.drop(uploadZone, { dataTransfer: { files: [createResume()] } });

    expect(screen.getByText("candidate.pdf")).toBeInTheDocument();
    expect(screen.getByText("Resume selected")).toBeInTheDocument();
  });

  it("rejects a short description without clearing it or uploading", async () => {
    const user = userEvent.setup();
    renderAnalyzer();
    const description = screen.getByLabelText("Job description text");
    await user.upload(
      screen.getByLabelText("Choose a PDF or DOCX resume"),
      createResume(),
    );
    await user.type(description, "Too short");
    await user.click(screen.getByRole("button", { name: "Analyze Resume" }));

    expect(screen.getByRole("alert")).toHaveTextContent("at least 30 characters");
    expect(description).toHaveValue("Too short");
    expect(api.post).not.toHaveBeenCalled();
  });

  it("requires a non-empty job description even when a resume is selected", async () => {
    const user = userEvent.setup();
    renderAnalyzer();
    await user.upload(
      screen.getByLabelText("Choose a PDF or DOCX resume"),
      createResume(),
    );
    await user.click(screen.getByRole("button", { name: "Analyze Resume" }));

    expect(screen.getByRole("alert")).toHaveTextContent("at least 30 characters");
    expect(api.post).not.toHaveBeenCalled();
  });

  it("sends the selected file and pasted description, then opens the real result route", async () => {
    vi.mocked(api.post).mockResolvedValue(response({ id: 42 }));
    const user = userEvent.setup();
    renderAnalyzer();

    const file = createResume();
    await user.upload(screen.getByLabelText("Choose a PDF or DOCX resume"), file);
    await user.type(screen.getByLabelText("Job description text"), JOB_DESCRIPTION);
    await user.click(screen.getByRole("button", { name: "Analyze Resume" }));

    await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));
    const call = vi.mocked(api.post).mock.calls[0];
    expect(call?.[0]).toBe("/analyses/upload");
    const payload = call?.[1];
    expect(payload).toBeInstanceOf(FormData);
    if (!(payload instanceof FormData)) throw new Error("Expected multipart form data.");
    expect(payload.get("job_description")).toBe(JOB_DESCRIPTION);
    const uploadedFile = payload.get("file");
    if (!(uploadedFile instanceof File)) throw new Error("Expected the selected resume file.");
    expect(uploadedFile.name).toBe(file.name);
    expect(call?.[2]).toEqual(
      expect.objectContaining({
        timeout: 300_000,
        onUploadProgress: expect.any(Function),
      }),
    );
    expect(await screen.findByTestId("current-path")).toHaveTextContent("/app/analysis/42");
  });

  it("retains the selected inputs and shows backend errors", async () => {
    vi.mocked(api.post).mockRejectedValue(new Error("The document could not be parsed."));
    const user = userEvent.setup();
    renderAnalyzer();

    const description = screen.getByLabelText("Job description text");
    await user.upload(
      screen.getByLabelText("Choose a PDF or DOCX resume"),
      createResume(),
    );
    await user.type(description, JOB_DESCRIPTION);
    await user.click(screen.getByRole("button", { name: "Analyze Resume" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("The document could not be parsed.");
    expect(description).toHaveValue(JOB_DESCRIPTION);
    expect(screen.getByText("candidate.pdf")).toBeInTheDocument();
  });

  it("displays score components, skill evidence, strengths, and the estimate disclaimer", async () => {
    vi.mocked(api.get).mockResolvedValue(
      response({
        id: 42,
        resume_id: 7,
        resume_filename: "candidate.pdf",
        job_description_id: 8,
        job_title: "Senior Python Engineer",
        company: null,
        overall_score: 72,
        created_at: "2025-01-01T00:00:00Z",
        breakdown: {
          required_skills: { score: 50, available: true, configured_weight: 35, effective_weight_percent: 28 },
          keyword_match: { score: 70, available: true, configured_weight: 25, effective_weight_percent: 20 },
          experience: { score: 80, available: true, configured_weight: 20, effective_weight_percent: 16 },
          education: { score: 100, available: true, configured_weight: 40, effective_weight_percent: 32 },
          project_relevance: { score: 60, available: true, configured_weight: 10, effective_weight_percent: 4 },
        },
        details: {
          required_skills_match_percentage: 50,
          keyword_match_percentage: 70,
          experience_relevance_percentage: 80,
          education_relevance_percentage: 100,
          project_relevance_percentage: 60,
          semantic_similarity_percentage: 75,
          matched_skills: [{ skill: "Python", category: "required", match_type: "matched" }],
          partially_matched_skills: [{ skill: "AWS", category: "required", match_type: "partial" }],
          matched_keywords: ["Python"],
          missing_required_skills: [],
          missing_preferred_skills: [],
          missing_skills: [{ skill: "PostgreSQL", category: "required", explanation: "Not evidenced in the resume." }],
          important_missing_keywords: ["Kubernetes"],
          resume_strengths: ["Experience evidence aligns with the role."],
          areas_to_improve: ["Clarify PostgreSQL experience if accurate."],
          relevant_sections: [],
          improvement_suggestions: ["Add specific, verifiable examples."],
          skills_to_learn: ["Build genuine Kubernetes proficiency."],
          section_feedback: { experience: "Prioritize role-relevant examples." },
          scoring_note: "Available components are normalized.",
        },
      }),
    );
    renderResults();

    expect(await screen.findByRole("heading", { name: "Senior Python Engineer" })).toBeInTheDocument();
    expect(screen.getByText("Python", { selector: ".skill-tag-match" })).toBeInTheDocument();
    expect(screen.getByText("AWS · partial")).toBeInTheDocument();
    expect(screen.getByText("PostgreSQL")).toBeInTheDocument();
    expect(screen.getByText("Matched keywords")).toBeInTheDocument();
    expect(screen.getByText("Resume strengths")).toBeInTheDocument();
    expect(screen.getByText("Experience relevance")).toBeInTheDocument();
    expect(screen.getByText(/does not represent or predict any employer/)).toBeInTheDocument();
  });
});
