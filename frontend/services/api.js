// ============================================================
// EXACT FILE LOCATION: frontend/services/api.js
// ============================================================
// Complete API service for ALL phases.
// Phase 1 — Admin Dashboard    (/api/*)
// Phase 2 — Candidate Portal   (/portal/*)
// Phase 3 — Resume Processing  (/resume/*)
// Phase 4 — Embeddings         (/embeddings/*)
// Phase 5 — Semantic Matching  (/matching/*)
// ============================================================

import axios from "axios";

// Base URL from .env.local
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Create Axios instance with default config
const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 15000,
});

// ============================================================
// Request interceptor — add auth token here later if needed
// ============================================================
api.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
);

// ============================================================
// Response interceptor — normalize all error messages
// ============================================================
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      "An unexpected error occurred";
    error.userMessage = message;
    return Promise.reject(error);
  }
);


// ============================================================
// PHASE 1 — DASHBOARD
// ============================================================

/** Get admin dashboard summary stats */
export const getDashboardStats = async () => {
  const { data } = await api.get("/api/dashboard/stats");
  return data;
};


// ============================================================
// PHASE 1 — JOBS
// ============================================================

/** Get all jobs with optional status filter and search */
export const getJobs = async ({ status = null, search = null, skip = 0, limit = 50 } = {}) => {
  const params = {};
  if (status) params.status = status;
  if (search) params.search = search;
  params.skip  = skip;
  params.limit = limit;
  const { data } = await api.get("/api/jobs", { params });
  return data;
};

/** Get single job with all its requirements */
export const getJob = async (jobId) => {
  const { data } = await api.get(`/api/jobs/${jobId}`);
  return data;
};

/** Create a new job posting */
export const createJob = async (jobData) => {
  const { data } = await api.post("/api/jobs", jobData);
  return data;
};

/** Update an existing job */
export const updateJob = async (jobId, jobData) => {
  const { data } = await api.put(`/api/jobs/${jobId}`, jobData);
  return data;
};

/** Delete a job by ID */
export const deleteJob = async (jobId) => {
  await api.delete(`/api/jobs/${jobId}`);
};

/** Add a requirement to a job */
export const addRequirement = async (jobId, reqData) => {
  const { data } = await api.post(`/api/jobs/${jobId}/requirements`, reqData);
  return data;
};

/** Update an existing requirement */
export const updateRequirement = async (jobId, reqId, reqData) => {
  const { data } = await api.put(`/api/jobs/${jobId}/requirements/${reqId}`, reqData);
  return data;
};

/** Delete a requirement */
export const deleteRequirement = async (jobId, reqId) => {
  await api.delete(`/api/jobs/${jobId}/requirements/${reqId}`);
};

/** Regenerate Pinecone embedding for a single job (Phase 1 admin panel) */
export const regenerateJobEmbedding = async (jobId, force = false) => {
  const { data } = await api.post(`/api/jobs/${jobId}/regenerate-embedding`, {
    force_full: force,
  });
  return data;
};

/** Batch sync all Phase 1 job embeddings that have pending updates */
export const syncJobEmbeddings = async () => {
  const { data } = await api.post("/api/jobs/sync-embeddings");
  return data;
};


// ============================================================
// PHASE 1 — CANDIDATES (Admin view)
// ============================================================

/** Get all candidates who applied for a specific job */
export const getCandidatesForJob = async (jobId, status = null) => {
  const params = {};
  if (status) params.status = status;
  const { data } = await api.get(`/api/jobs/${jobId}/candidates`, { params });
  return data;
};

/** Get single candidate detail by ID */
export const getCandidate = async (candidateId) => {
  const { data } = await api.get(`/api/candidates/${candidateId}`);
  return data;
};


// ============================================================
// PHASE 2 — CANDIDATE PORTAL (/portal/*)
// ============================================================

/** Get all OPEN jobs for the public careers page */
export const getOpenJobs = async () => {
  const { data } = await api.get("/portal/jobs");
  return data;
};

/** Get single job detail for the careers/[jobId] page */
export const getPublicJob = async (jobId) => {
  const { data } = await api.get(`/portal/jobs/${jobId}`);
  return data;
};

/** Upload a PDF CV — returns { resume_path, filename } */
export const uploadCV = async (file) => {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post("/portal/upload-cv", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

/** Submit a job application form */
export const submitApplication = async (payload) => {
  const { data } = await api.post("/portal/apply", payload);
  return data;
};

/** Get all applications by email — used on the status page */
export const getMyApplications = async (email) => {
  const { data } = await api.get(`/portal/applications/${encodeURIComponent(email)}`);
  return data;
};

/** Get single application detail by ID */
export const getApplicationDetail = async (applicationId) => {
  const { data } = await api.get(`/portal/applications/detail/${applicationId}`);
  return data;
};


// ============================================================
// PHASE 3 — RESUME PROCESSING (/resume/*)
// ============================================================

/**
 * Extract and parse a candidate's uploaded PDF resume.
 * Extracts: skills, education, experience, certifications.
 * Run this BEFORE generating embeddings (Phase 4).
 */
export const processResume = async (candidateId) => {
  const { data } = await api.post(`/resume/process/${candidateId}`);
  return data;
};

/** Get stored resume extraction data for a candidate */
export const getResumeData = async (candidateId) => {
  const { data } = await api.get(`/resume/${candidateId}`);
  return data;
};


// ============================================================
// PHASE 4 — EMBEDDING GENERATION (/embeddings/*)
// ============================================================

/**
 * Generate and store Pinecone embedding for a job.
 * Set force=true to regenerate even if already synced.
 */
export const generateJobEmbedding = async (jobId, force = false) => {
  const { data } = await api.post(`/embeddings/job/${jobId}`, { force });
  return data;
};

/**
 * Generate and store Pinecone embedding for a candidate resume.
 * Resume must be processed first via processResume().
 */
export const generateCandidateEmbedding = async (candidateId, force = false) => {
  const { data } = await api.post(`/embeddings/candidate/${candidateId}`, { force });
  return data;
};

/**
 * Batch sync ALL pending embeddings (jobs + candidates).
 * Use after processing multiple resumes or editing many jobs.
 */
export const syncAllEmbeddings = async () => {
  const { data } = await api.post("/embeddings/sync");
  return data;
};

/** Get embedding sync status — shows how many are pending */
export const getEmbeddingStatus = async () => {
  const { data } = await api.get("/embeddings/status");
  return data;
};


// ============================================================
// PHASE 5 — SEMANTIC MATCHING (/matching/*)
// ============================================================

/**
 * Run full AI matching for one candidate vs one job.
 * Prerequisites in order:
 *   1. processResume(candidateId)
 *   2. generateCandidateEmbedding(candidateId)
 *   3. generateJobEmbedding(jobId)
 *   4. then call runMatch()
 */
export const runMatch = async (candidateId, jobId, force = false) => {
  const { data } = await api.post("/matching/run", {
    candidate_profile_id : parseInt(candidateId),
    job_id               : parseInt(jobId),
    force_recalculate    : force,
  });
  return data;
};

/**
 * Run AI matching for ALL candidates who applied for a job.
 * Returns results sorted by final score descending.
 */
export const runBulkMatch = async (jobId, force = false) => {
  const { data } = await api.post(`/matching/bulk/${jobId}?force=${force}`);
  return data;
};

/**
 * Get stored match result for one candidate + job pair.
 * Used on the admin analysis page.
 */
export const getMatchResult = async (candidateId, jobId) => {
  const { data } = await api.get(`/matching/result/${candidateId}/${jobId}`);
  return data;
};

/**
 * Get all match results for a job sorted best-first.
 * Used on the job leaderboard view.
 */
export const getJobMatchResults = async (jobId) => {
  const { data } = await api.get(`/matching/job/${jobId}`);
  return data;
};


// ============================================================
// Default export
// MUST be at the bottom — after all named exports above
// ============================================================
export default api;


// ============================================================
// PHASE 6/7/8 — INTERVIEW SYSTEM (/interview/*, /voice/*)
// ============================================================

/**
 * Auto-generate interview questions for a candidate+job pair.
 * Called after matching completes.
 * POST /interview/generate/{candidateId}/{jobId}
 */
export const generateInterviewForCandidate = async (candidateId, jobId) => {
  const { data } = await api.post(`/interview/generate/${candidateId}/${jobId}`);
  return data;
};

/**
 * Get interview session by its own session ID.
 * Used on the candidate interview page.
 * GET /interview/session/id/{sessionId}
 */
export const getInterviewSession = async (sessionId) => {
  const { data } = await api.get(`/interview/session/id/${sessionId}`);
  return data;
};

/**
 * Get interview session for a candidate+job pair.
 * GET /interview/session/{candidateId}/{jobId}
 */
export const getInterviewSessionForCandidate = async (candidateId, jobId) => {
  const { data } = await api.get(`/interview/session/${candidateId}/${jobId}`);
  return data;
};

/**
 * Mark interview session as started.
 * POST /interview/start/{sessionId}
 */
export const startInterview = async (sessionId) => {
  const { data } = await api.post(`/interview/start/${sessionId}`);
  return data;
};

/**
 * Submit a text answer to an interview question.
 * POST /interview/submit-answer
 */
export const submitTextAnswer = async (payload) => {
  const { data } = await api.post("/interview/submit-answer", payload);
  return data;
};

/**
 * Trigger AI evaluation of all answers in a session.
 * POST /interview/evaluate/{sessionId}
 */
export const evaluateInterview = async (sessionId) => {
  const { data } = await api.post(`/interview/evaluate/${sessionId}`);
  return data;
};

/**
 * Get completed interview evaluation results (admin view).
 * GET /interview/results/{sessionId}
 */
export const getInterviewResults = async (sessionId) => {
  const { data } = await api.get(`/interview/results/${sessionId}`);
  return data;
};

/**
 * Get all interview sessions for a job (admin view).
 * GET /interview/job/{jobId}/sessions
 */
export const getJobInterviewSessions = async (jobId) => {
  const { data } = await api.get(`/interview/job/${jobId}/sessions`);
  return data;
};

/**
 * Generate TTS audio for an interview question.
 * POST /voice/question-audio/{questionId}
 */
export const getQuestionAudio = async (questionId) => {
  const { data } = await api.post(`/voice/question-audio/${questionId}`);
  return data;
};

/**
 * Upload voice recording and get transcript via Whisper.
 * POST /voice/transcribe (multipart form)
 */
export const transcribeVoice = async (sessionId, questionId, audioFile) => {
  const formData = new FormData();
  formData.append("session_id",  sessionId);
  formData.append("question_id", questionId);
  formData.append("file",        audioFile);
  const { data } = await api.post("/voice/transcribe", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

/**
 * Shortlist or reject a candidate (admin action)
 * PATCH /api/candidates/{candidateId}/status
 */
export const updateCandidateStatus = async (candidateId, status) => {
  const { data } = await api.patch(`/api/candidates/${candidateId}/status`, { status });
  return data;
};