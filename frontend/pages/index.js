// ============================================================
// pages/index.js
// Admin Dashboard overview page.
// Displays summary stats, quick links, and embedding sync status.
// ============================================================

import { useEffect, useState } from "react";
import Link from "next/link";
import Layout from "../components/Layout";
import StatsCard from "../components/StatsCard";
import { getDashboardStats, syncAllEmbeddings } from "../services/api";
import toast from "react-hot-toast";
import {
  BriefcaseBusiness,
  Users,
  CheckCircle,
  RefreshCw,
  PlusCircle,
  AlertTriangle,
  TrendingUp,
  FileText,
} from "lucide-react";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  // Fetch dashboard stats on mount
  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const data = await getDashboardStats();
      setStats(data);
    } catch (err) {
      toast.error("Failed to load dashboard stats");
    } finally {
      setLoading(false);
    }
  };

  // Trigger batch embedding sync for all pending jobs
  const handleSyncEmbeddings = async () => {
    setSyncing(true);
    try {
      const result = await syncAllEmbeddings();
      toast.success(
        `Sync complete: ${result.synced?.length || 0} jobs updated`
      );
      fetchStats(); // Refresh stats
    } catch (err) {
      toast.error("Sync failed: " + (err.userMessage || "Unknown error"));
    } finally {
      setSyncing(false);
    }
  };

  return (
    <Layout title="Dashboard">
      {/* Page header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Welcome back, Admin</h2>
          <p className="text-gray-500 mt-1 text-sm">
            Here's your AI candidate screening overview
          </p>
        </div>

        <div className="flex gap-3">
          {/* Sync button — shown when there are pending updates */}
          {stats?.pending_embedding_sync > 0 && (
            <button
              onClick={handleSyncEmbeddings}
              disabled={syncing}
              className="btn-secondary"
            >
              <RefreshCw size={16} className={syncing ? "animate-spin" : ""} />
              Sync {stats.pending_embedding_sync} Pending
            </button>
          )}

          <Link href="/jobs/create" className="btn-primary">
            <PlusCircle size={16} />
            Post New Job
          </Link>
        </div>
      </div>

      {/* Stats grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card p-6 animate-pulse">
              <div className="h-12 w-12 bg-gray-200 rounded-xl mb-4" />
              <div className="h-4 bg-gray-200 rounded w-24 mb-2" />
              <div className="h-8 bg-gray-200 rounded w-16" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
          <StatsCard
            label="Total Jobs"
            value={stats?.total_jobs}
            icon={BriefcaseBusiness}
            color="blue"
            subLabel={`${stats?.draft_jobs} draft, ${stats?.closed_jobs} closed`}
          />
          <StatsCard
            label="Active Jobs"
            value={stats?.active_jobs}
            icon={TrendingUp}
            color="green"
            subLabel="Currently open for applications"
          />
          <StatsCard
            label="Total Candidates"
            value={stats?.total_candidates}
            icon={Users}
            color="purple"
            href="/jobs"
            subLabel="Open a job to view candidates"
          />
          <StatsCard
            label="Shortlisted"
            value={stats?.shortlisted_candidates}
            icon={CheckCircle}
            color="green"
            subLabel="AI-recommended candidates"
          />
        </div>
      )}

      {/* Embedding sync alert */}
      {!loading && stats?.pending_embedding_sync > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-8 flex items-center gap-3">
          <AlertTriangle size={18} className="text-amber-500 shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-amber-800">
              {stats.pending_embedding_sync} job{stats.pending_embedding_sync > 1 ? "s" : ""} need Pinecone sync
            </p>
            <p className="text-xs text-amber-600 mt-0.5">
              These jobs were recently updated. Their embeddings need to be regenerated for accurate matching.
            </p>
          </div>
          <button onClick={handleSyncEmbeddings} disabled={syncing} className="btn-secondary text-amber-700 border-amber-300 text-xs">
            <RefreshCw size={14} className={syncing ? "animate-spin" : ""} />
            Sync Now
          </button>
        </div>
      )}

      {/* Quick actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        <Link href="/jobs" className="card p-6 hover:shadow-md transition-shadow group cursor-pointer">
          <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center mb-4 group-hover:bg-blue-100 transition-colors">
            <BriefcaseBusiness size={20} className="text-blue-600" />
          </div>
          <h3 className="font-semibold text-gray-900">Manage Jobs</h3>
          <p className="text-sm text-gray-500 mt-1">View, edit, and manage all job postings</p>
        </Link>

        <Link href="/jobs/create" className="card p-6 hover:shadow-md transition-shadow group cursor-pointer">
          <div className="w-10 h-10 bg-green-50 rounded-xl flex items-center justify-center mb-4 group-hover:bg-green-100 transition-colors">
            <PlusCircle size={20} className="text-green-600" />
          </div>
          <h3 className="font-semibold text-gray-900">Post New Job</h3>
          <p className="text-sm text-gray-500 mt-1">Create a job with requirements and skills</p>
        </Link>

        <div className="card p-6 opacity-60 cursor-not-allowed">
          <div className="w-10 h-10 bg-purple-50 rounded-xl flex items-center justify-center mb-4">
            <FileText size={20} className="text-purple-600" />
          </div>
          <h3 className="font-semibold text-gray-900">CV Analysis</h3>
          <p className="text-sm text-gray-500 mt-1">Coming in Phase 2 — Candidate portal</p>
        </div>
      </div>
    </Layout>
  );
}
