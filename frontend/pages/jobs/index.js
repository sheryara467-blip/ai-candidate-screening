// ============================================================
// pages/jobs/index.js
// Job Management page — lists all jobs with search and filter.
// Admin can view, edit, delete jobs and trigger embedding sync.
// ============================================================

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import Layout from "../../components/Layout";
import JobCard from "../../components/JobCard";
import { getJobs, deleteJob, regenerateJobEmbedding } from "../../services/api";
import toast from "react-hot-toast";
import { PlusCircle, Search, RefreshCw } from "lucide-react";

const STATUS_OPTIONS = ["ALL", "OPEN", "DRAFT", "CLOSED"];

export default function JobsPage() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [regeneratingId, setRegeneratingId] = useState(null);

  // Fetch jobs from API with current filters
  const fetchJobs = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getJobs({
        search: search || null,
        status: statusFilter === "ALL" ? null : statusFilter,
      });
      setJobs(data);
    } catch (err) {
      toast.error("Failed to load jobs");
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter]);

  // Re-fetch whenever search or filter changes (debounced on search)
  useEffect(() => {
    const timer = setTimeout(() => fetchJobs(), search ? 400 : 0);
    return () => clearTimeout(timer);
  }, [fetchJobs]);

  // Handle job deletion with confirmation
  const handleDelete = async (jobId, jobTitle) => {
    if (!confirm(`Delete "${jobTitle}"?\n\nThis will also remove the candidate records and Pinecone embedding.`)) return;

    try {
      await deleteJob(jobId);
      toast.success(`"${jobTitle}" deleted`);
      setJobs((prev) => prev.filter((j) => j.id !== jobId));
    } catch (err) {
      toast.error("Delete failed: " + (err.userMessage || "Unknown error"));
    }
  };

  // Manually trigger embedding regeneration for a single job
  const handleRegenerate = async (jobId) => {
    setRegeneratingId(jobId);
    try {
      const result = await regenerateJobEmbedding(jobId);
      toast.success(result.message || "Embedding regenerated");
      // Update the embedding_needs_update flag in local state
      setJobs((prev) =>
        prev.map((j) =>
          j.id === jobId ? { ...j, embedding_needs_update: false } : j
        )
      );
    } catch (err) {
      toast.error("Regeneration failed: " + (err.userMessage || "Unknown error"));
    } finally {
      setRegeneratingId(null);
    }
  };

  return (
    <Layout title="Job Management">
      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">All Jobs</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {loading ? "Loading..." : `${jobs.length} job${jobs.length !== 1 ? "s" : ""} found`}
          </p>
        </div>
        <Link href="/jobs/create" className="btn-primary">
          <PlusCircle size={16} />
          Post New Job
        </Link>
      </div>

      {/* Search + Filter toolbar */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        {/* Search input */}
        <div className="relative flex-1">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
          />
          <input
            type="text"
            placeholder="Search by title, department, skills..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input-field pl-9"
          />
        </div>

        {/* Status filter tabs */}
        <div className="flex gap-1.5 bg-gray-100 rounded-lg p-1">
          {STATUS_OPTIONS.map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                statusFilter === s
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Job grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card p-5 animate-pulse">
              <div className="h-5 bg-gray-200 rounded w-3/4 mb-3" />
              <div className="h-4 bg-gray-200 rounded w-1/2 mb-4" />
              <div className="flex gap-2 mb-4">
                <div className="h-6 bg-gray-200 rounded w-16" />
                <div className="h-6 bg-gray-200 rounded w-16" />
              </div>
              <div className="h-8 bg-gray-200 rounded w-full" />
            </div>
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-20">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Search size={24} className="text-gray-400" />
          </div>
          <h3 className="text-gray-900 font-medium">No jobs found</h3>
          <p className="text-gray-500 text-sm mt-1">
            {search || statusFilter !== "ALL"
              ? "Try adjusting your search or filter"
              : "Create your first job posting to get started"}
          </p>
          {!search && statusFilter === "ALL" && (
            <Link href="/jobs/create" className="btn-primary mt-4 inline-flex">
              <PlusCircle size={16} />
              Post New Job
            </Link>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {jobs.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              onDelete={handleDelete}
              onRegenerate={handleRegenerate}
              isRegenerating={regeneratingId === job.id}
            />
          ))}
        </div>
      )}
    </Layout>
  );
}
