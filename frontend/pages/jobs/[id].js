// ============================================================
// pages/jobs/[id].js
// Edit Job page — loads existing job and allows full editing.
// Supports editing requirements in-place and adding new ones.
// INCREMENTAL SYNC: backend auto-detects changed fields.
// ============================================================

import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import Layout from "../../components/Layout";
import {
  getJob,
  updateJob,
  addRequirement,
  updateRequirement,
  deleteRequirement,
  regenerateJobEmbedding,
} from "../../services/api";
import toast from "react-hot-toast";
import { Save, PlusCircle, Trash2, X, ArrowLeft, RefreshCw, AlertTriangle } from "lucide-react";

export default function EditJobPage() {
  const router = useRouter();
  const { id } = router.query;

  const [job, setJob] = useState(null);
  const [form, setForm] = useState({});
  const [requirements, setRequirements] = useState([]);
  const [newReq, setNewReq] = useState({ category: "", description: "", is_mandatory: true });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  // Load job data when ID is available
  useEffect(() => {
    if (!id) return;
    fetchJob();
  }, [id]);

  const fetchJob = async () => {
    try {
      setLoading(true);
      const data = await getJob(id);
      setJob(data);
      // Pre-fill form with existing values
      setForm({
        title: data.title,
        department: data.department,
        description: data.description,
        required_skills: data.required_skills,
        experience: data.experience || "",
        education: data.education || "",
        status: data.status,
      });
      setRequirements(data.requirements || []);
    } catch (err) {
      toast.error("Failed to load job");
      router.push("/jobs");
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  // Save job updates — backend handles incremental embedding sync
  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await updateJob(id, form);
      toast.success("Job updated. Embedding sync triggered if needed.");
      fetchJob(); // Reload to get latest embedding_needs_update flag
    } catch (err) {
      toast.error("Update failed: " + (err.userMessage || "Unknown error"));
    } finally {
      setSaving(false);
    }
  };

  // Add a new requirement inline
  const handleAddRequirement = async () => {
    if (!newReq.category.trim() || !newReq.description.trim()) {
      toast.error("Category and description are required");
      return;
    }
    try {
      const created = await addRequirement(id, newReq);
      setRequirements((prev) => [...prev, created]);
      setNewReq({ category: "", description: "", is_mandatory: true });
      toast.success("Requirement added");
    } catch (err) {
      toast.error("Failed to add requirement");
    }
  };

  // Delete an existing requirement
  const handleDeleteRequirement = async (reqId) => {
    if (!confirm("Remove this requirement?")) return;
    try {
      await deleteRequirement(id, reqId);
      setRequirements((prev) => prev.filter((r) => r.id !== reqId));
      toast.success("Requirement removed");
    } catch (err) {
      toast.error("Failed to delete requirement");
    }
  };

  // Manually trigger embedding regeneration
  const handleRegenerate = async () => {
    setRegenerating(true);
    try {
      const result = await regenerateJobEmbedding(id, true); // force=true
      toast.success(result.message || "Embedding regenerated");
      fetchJob();
    } catch (err) {
      toast.error("Regeneration failed: " + (err.userMessage || "Unknown error"));
    } finally {
      setRegenerating(false);
    }
  };

  if (loading) {
    return (
      <Layout title="Edit Job">
        <div className="max-w-3xl space-y-6">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="card p-6 animate-pulse">
              <div className="h-5 bg-gray-200 rounded w-1/3 mb-4" />
              <div className="h-10 bg-gray-200 rounded w-full mb-3" />
              <div className="h-10 bg-gray-200 rounded w-full" />
            </div>
          ))}
        </div>
      </Layout>
    );
  }

  return (
    <Layout title={`Edit: ${job?.title || "Job"}`}>
      {/* Back link */}
      <Link href="/jobs" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-6">
        <ArrowLeft size={16} />
        Back to Jobs
      </Link>

      {/* Sync warning */}
      {job?.embedding_needs_update && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6 flex items-center gap-3">
          <AlertTriangle size={16} className="text-amber-500 shrink-0" />
          <p className="text-sm text-amber-800 flex-1">
            Pinecone embedding is out of sync. Save the job or click "Sync Now" to update.
          </p>
          <button onClick={handleRegenerate} disabled={regenerating} className="btn-secondary text-xs border-amber-300">
            <RefreshCw size={13} className={regenerating ? "animate-spin" : ""} />
            Sync Now
          </button>
        </div>
      )}

      <form onSubmit={handleSave} className="max-w-3xl space-y-8">

        {/* ======== JOB DETAILS FORM ======== */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-5 pb-3 border-b border-gray-100">
            <h3 className="font-semibold text-gray-900">Job Details</h3>
            <span className="text-xs text-gray-400">ID: {id}</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <div className="sm:col-span-2">
              <label className="label">Job Title *</label>
              <input type="text" name="title" value={form.title || ""} onChange={handleChange} className="input-field" required />
            </div>
            <div>
              <label className="label">Department *</label>
              <input type="text" name="department" value={form.department || ""} onChange={handleChange} className="input-field" required />
            </div>
            <div>
              <label className="label">Status</label>
              <select name="status" value={form.status || "DRAFT"} onChange={handleChange} className="input-field">
                <option value="DRAFT">Draft</option>
                <option value="OPEN">Open</option>
                <option value="CLOSED">Closed</option>
              </select>
            </div>
            <div>
              <label className="label">Experience</label>
              <input type="text" name="experience" value={form.experience || ""} onChange={handleChange} placeholder="e.g. 3+ years" className="input-field" />
            </div>
            <div>
              <label className="label">Education</label>
              <input type="text" name="education" value={form.education || ""} onChange={handleChange} placeholder="e.g. Bachelor's in CS" className="input-field" />
            </div>
            <div className="sm:col-span-2">
              <label className="label">Description *</label>
              <textarea name="description" value={form.description || ""} onChange={handleChange} rows={5} className="input-field resize-none" required />
            </div>
            <div className="sm:col-span-2">
              <label className="label">Required Skills *</label>
              <input type="text" name="required_skills" value={form.required_skills || ""} onChange={handleChange} placeholder="Python, FastAPI, Docker" className="input-field" required />
              <p className="text-xs text-gray-400 mt-1">Comma-separated. Changing skills triggers embedding re-sync.</p>
            </div>
          </div>
        </div>

        {/* ======== REQUIREMENTS ======== */}
        <div className="card p-6">
          <h3 className="font-semibold text-gray-900 mb-5 pb-3 border-b border-gray-100">Requirements</h3>

          {/* Existing requirements */}
          {requirements.length === 0 ? (
            <p className="text-gray-400 text-sm mb-4">No requirements yet.</p>
          ) : (
            <div className="space-y-3 mb-5">
              {requirements.map((req) => (
                <div key={req.id} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg text-sm">
                  <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium shrink-0">
                    {req.category}
                  </span>
                  <p className="flex-1 text-gray-700 text-xs">{req.description}</p>
                  <span className={`text-xs shrink-0 ${req.is_mandatory ? "text-red-500" : "text-gray-400"}`}>
                    {req.is_mandatory ? "Required" : "Optional"}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleDeleteRequirement(req.id)}
                    className="text-gray-400 hover:text-red-500 transition-colors shrink-0"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Add new requirement inline */}
          <div className="border-t border-gray-100 pt-4">
            <p className="text-xs font-medium text-gray-500 mb-3">Add New Requirement</p>
            <div className="flex gap-3 items-end">
              <div className="w-32">
                <input
                  type="text"
                  value={newReq.category}
                  onChange={(e) => setNewReq((p) => ({ ...p, category: e.target.value }))}
                  placeholder="Category"
                  className="input-field text-xs"
                />
              </div>
              <div className="flex-1">
                <input
                  type="text"
                  value={newReq.description}
                  onChange={(e) => setNewReq((p) => ({ ...p, description: e.target.value }))}
                  placeholder="Requirement description"
                  className="input-field text-xs"
                />
              </div>
              <label className="flex items-center gap-1.5 text-xs text-gray-500 pb-2 shrink-0">
                <input
                  type="checkbox"
                  checked={newReq.is_mandatory}
                  onChange={(e) => setNewReq((p) => ({ ...p, is_mandatory: e.target.checked }))}
                  className="accent-blue-600"
                />
                Required
              </label>
              <button type="button" onClick={handleAddRequirement} className="btn-primary text-xs py-2 shrink-0">
                <PlusCircle size={14} />
                Add
              </button>
            </div>
          </div>
        </div>

        {/* ======== ACTIONS ======== */}
        <div className="flex gap-3">
          <button type="submit" disabled={saving} className="btn-primary">
            {saving ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save size={16} />
                Save Changes
              </>
            )}
          </button>
          <button
            type="button"
            onClick={handleRegenerate}
            disabled={regenerating}
            className="btn-secondary"
          >
            <RefreshCw size={16} className={regenerating ? "animate-spin" : ""} />
            Force Resync
          </button>
          <Link href="/jobs" className="btn-secondary">
            Cancel
          </Link>
        </div>
      </form>
    </Layout>
  );
}
