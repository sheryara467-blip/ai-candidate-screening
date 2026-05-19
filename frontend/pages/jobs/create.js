// ============================================================
// pages/jobs/create.js
// Create Job page — full form for posting a new job.
// Includes: basic fields, skills, requirements builder.
// On submit, sends to backend which auto-generates Pinecone embedding.
// ============================================================

import { useState } from "react";
import { useRouter } from "next/router";
import Layout from "../../components/Layout";
import { createJob } from "../../services/api";
import toast from "react-hot-toast";
import { PlusCircle, X, ArrowLeft } from "lucide-react";
import Link from "next/link";

// Initial empty form state
const EMPTY_FORM = {
  title: "",
  department: "",
  description: "",
  required_skills: "",
  experience: "",
  education: "",
  status: "DRAFT",
};

// Initial empty requirement row
const EMPTY_REQ = { category: "", description: "", is_mandatory: true };

export default function CreateJobPage() {
  const router = useRouter();
  const [form, setForm] = useState(EMPTY_FORM);
  const [requirements, setRequirements] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});

  // Handle top-level field change
  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    // Clear validation error for this field
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: null }));
  };

  // Add a blank requirement row
  const addRequirement = () => {
    setRequirements((prev) => [...prev, { ...EMPTY_REQ }]);
  };

  // Update a specific requirement row field
  const updateRequirement = (index, field, value) => {
    setRequirements((prev) =>
      prev.map((r, i) => (i === index ? { ...r, [field]: value } : r))
    );
  };

  // Remove a requirement row
  const removeRequirement = (index) => {
    setRequirements((prev) => prev.filter((_, i) => i !== index));
  };

  // Validate form before submission
  const validate = () => {
    const newErrors = {};
    if (!form.title.trim()) newErrors.title = "Job title is required";
    if (!form.department.trim()) newErrors.department = "Department is required";
    if (!form.description.trim()) newErrors.description = "Description is required";
    if (!form.required_skills.trim()) newErrors.required_skills = "At least one skill is required";
    return newErrors;
  };

  // Submit form to API
  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validate inputs
    const validationErrors = validate();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      toast.error("Please fix the form errors");
      return;
    }

    setSubmitting(true);
    try {
      // Filter out empty requirement rows before submitting
      const validRequirements = requirements.filter(
        (r) => r.category.trim() && r.description.trim()
      );

      // Create job via API (embedding auto-generated on backend)
      const newJob = await createJob({ ...form, requirements: validRequirements });

      toast.success(`Job "${newJob.title}" created successfully!`);
      router.push("/jobs");
    } catch (err) {
      toast.error("Failed to create job: " + (err.userMessage || "Unknown error"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Layout title="Post New Job">
      {/* Back link */}
      <Link href="/jobs" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-6">
        <ArrowLeft size={16} />
        Back to Jobs
      </Link>

      <form onSubmit={handleSubmit} className="max-w-3xl space-y-8">

        {/* ======== BASIC INFORMATION ======== */}
        <div className="card p-6">
          <h3 className="font-semibold text-gray-900 mb-5 pb-3 border-b border-gray-100">
            Job Information
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            {/* Title */}
            <div className="sm:col-span-2">
              <label className="label">Job Title *</label>
              <input
                type="text"
                name="title"
                value={form.title}
                onChange={handleChange}
                placeholder="e.g. Senior Python Developer"
                className={`input-field ${errors.title ? "border-red-400 focus:ring-red-400" : ""}`}
              />
              {errors.title && <p className="text-red-500 text-xs mt-1">{errors.title}</p>}
            </div>

            {/* Department */}
            <div>
              <label className="label">Department *</label>
              <input
                type="text"
                name="department"
                value={form.department}
                onChange={handleChange}
                placeholder="e.g. Engineering"
                className={`input-field ${errors.department ? "border-red-400" : ""}`}
              />
              {errors.department && <p className="text-red-500 text-xs mt-1">{errors.department}</p>}
            </div>

            {/* Status */}
            <div>
              <label className="label">Status</label>
              <select name="status" value={form.status} onChange={handleChange} className="input-field">
                <option value="DRAFT">Draft</option>
                <option value="OPEN">Open</option>
                <option value="CLOSED">Closed</option>
              </select>
            </div>

            {/* Experience */}
            <div>
              <label className="label">Experience Required</label>
              <input
                type="text"
                name="experience"
                value={form.experience}
                onChange={handleChange}
                placeholder="e.g. 3+ years"
                className="input-field"
              />
            </div>

            {/* Education */}
            <div>
              <label className="label">Education Requirement</label>
              <input
                type="text"
                name="education"
                value={form.education}
                onChange={handleChange}
                placeholder="e.g. Bachelor's in Computer Science"
                className="input-field"
              />
            </div>

            {/* Description */}
            <div className="sm:col-span-2">
              <label className="label">Job Description *</label>
              <textarea
                name="description"
                value={form.description}
                onChange={handleChange}
                rows={5}
                placeholder="Describe the role, responsibilities, and what you're looking for..."
                className={`input-field resize-none ${errors.description ? "border-red-400" : ""}`}
              />
              {errors.description && <p className="text-red-500 text-xs mt-1">{errors.description}</p>}
            </div>

            {/* Required Skills */}
            <div className="sm:col-span-2">
              <label className="label">Required Skills *</label>
              <input
                type="text"
                name="required_skills"
                value={form.required_skills}
                onChange={handleChange}
                placeholder="Python, FastAPI, Docker, PostgreSQL (comma-separated)"
                className={`input-field ${errors.required_skills ? "border-red-400" : ""}`}
              />
              {errors.required_skills ? (
                <p className="text-red-500 text-xs mt-1">{errors.required_skills}</p>
              ) : (
                <p className="text-gray-400 text-xs mt-1">
                  Separate skills with commas. These are used for semantic matching.
                </p>
              )}
            </div>
          </div>
        </div>

        {/* ======== JOB REQUIREMENTS BUILDER ======== */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-5 pb-3 border-b border-gray-100">
            <h3 className="font-semibold text-gray-900">
              Job Requirements
              <span className="ml-2 text-xs text-gray-400 font-normal">(optional)</span>
            </h3>
            <button type="button" onClick={addRequirement} className="btn-secondary text-xs">
              <PlusCircle size={14} />
              Add Requirement
            </button>
          </div>

          {requirements.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-6">
              No requirements added yet. Click "Add Requirement" to add structured requirements.
            </p>
          ) : (
            <div className="space-y-4">
              {requirements.map((req, index) => (
                <div key={index} className="flex gap-3 items-start p-4 bg-gray-50 rounded-lg">
                  {/* Category */}
                  <div className="w-36 shrink-0">
                    <input
                      type="text"
                      value={req.category}
                      onChange={(e) => updateRequirement(index, "category", e.target.value)}
                      placeholder="Category"
                      className="input-field text-xs"
                    />
                  </div>

                  {/* Description */}
                  <div className="flex-1">
                    <input
                      type="text"
                      value={req.description}
                      onChange={(e) => updateRequirement(index, "description", e.target.value)}
                      placeholder="Requirement description..."
                      className="input-field text-xs"
                    />
                  </div>

                  {/* Mandatory toggle */}
                  <div className="shrink-0 flex items-center gap-2 text-xs text-gray-500 pt-2">
                    <input
                      type="checkbox"
                      id={`mandatory-${index}`}
                      checked={req.is_mandatory}
                      onChange={(e) => updateRequirement(index, "is_mandatory", e.target.checked)}
                      className="accent-blue-600"
                    />
                    <label htmlFor={`mandatory-${index}`}>Required</label>
                  </div>

                  {/* Remove */}
                  <button
                    type="button"
                    onClick={() => removeRequirement(index)}
                    className="shrink-0 p-1.5 text-gray-400 hover:text-red-500 transition-colors mt-1"
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ======== SUBMIT ======== */}
        <div className="flex gap-3">
          <button
            type="submit"
            disabled={submitting}
            className="btn-primary"
          >
            {submitting ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <PlusCircle size={16} />
                Post Job
              </>
            )}
          </button>
          <Link href="/jobs" className="btn-secondary">
            Cancel
          </Link>
        </div>

      </form>
    </Layout>
  );
}