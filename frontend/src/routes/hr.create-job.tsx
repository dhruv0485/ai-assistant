import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { ArrowLeft, X, Plus, Sparkles, CheckCircle2 } from 'lucide-react';
import { pageHead, type Job } from '@/lib/tribe-data';
import { useTribe } from '@/lib/tribe-store';
import { HrShell } from '@/components/hr-shell';
import { Field, UploadZone } from '@/components/tribe-ui';
import { Button } from '@/components/ui/button';
import { supabase } from '@/lib/supabase';

export const Route = createFileRoute('/hr/create-job')({
  head: () =>
    pageHead(
      'Create Job Posting',
      'Publish a new placement drive role with a job description, requirements, and skills.'
    ),
  component: CreateJob,
});

function CreateJob() {
  const { setJobs, refreshJobs, user, toast } = useTribe();
  const navigate = useNavigate();

  const [data, setData] = useState({
    title: '',
    department: '',
    location: '',
    type: 'Full-time',
    min: '',
    max: '',
    salaryMin: '',
    salaryMax: '',
    description: '',
  });

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function save(draft = false) {
    if (!data.title.trim()) {
      setError('Please enter a job title.');
      return;
    }
    if (!draft && (!data.department.trim() || !data.location.trim() || !data.description.trim())) {
      setError('Please complete the department, location, and job description.');
      return;
    }
    if (data.min && data.max && Number(data.min) > Number(data.max)) {
      setError('Maximum experience must be at least minimum experience.');
      return;
    }

    setBusy(true);
    setError('');

    try {
      // 1. Insert into Supabase 'jobs' table
      const { data: inserted, error: dbErr } = await supabase
        .from('jobs')
        .insert({
          title: data.title.trim(),
          department: data.department.trim(),
          location: data.location.trim(),
          employment_type: data.type,
          min_years_experience: Number(data.min) || 0,
          max_years_experience: Number(data.max) || 3,
          salary_min: data.salaryMin ? Number(data.salaryMin) : null,
          salary_max: data.salaryMax ? Number(data.salaryMax) : null,
          description: data.description.trim(),
          skills: [],
          must_have_skills: [],
          nice_to_have_skills: [],
          status: draft ? 'Draft' : 'Active',
          created_by: user?.id || null,
        })
        .select()
        .single();

      if (dbErr) {
        console.error('Supabase jobs insert error:', dbErr.message);
        setError(`Failed to save job to Supabase: ${dbErr.message}`);
        toast(`Error: ${dbErr.message}`);
        return;
      }

      const finalJobId = inserted.id;

      // Refresh store to ensure all pages see the new live job
      await refreshJobs();
      toast(draft ? 'Job saved as draft.' : 'Job published! Backend AI engine will parse competencies automatically.');

      navigate({ to: '/hr/jobs/$jobId', params: { jobId: finalJobId } });
    } catch (err: any) {
      console.error('Job creation error:', err);
      setError(err?.message || 'Failed to create job posting');
      toast('Failed to create job posting.');
    } finally {
      setBusy(false);
    }
  }

  function handleParsedJd(text: string) {
    setData((d) => ({ ...d, description: text }));
    toast('Job description uploaded. Backend AI engine will parse requirements on submission.');
  }

  return (
    <HrShell title="Create Job Posting" active="jobs">
      <main className="container page-main form-narrow">
        <Link to="/hr" search={{ view: 'jobs' }} className="back-link">
          <ArrowLeft />
          Back to Job Postings
        </Link>
        <h1 className="page-title">Create Job Posting</h1>
        <p className="page-subtitle">
          Define role requirements. Backend Pass 1 & 2 will verify applicant claims against these skills.
        </p>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            save(false);
          }}
        >
          <div className="form-grid">
            <Field label="Job Title">
              <input
                required
                value={data.title}
                onChange={(e) => setData({ ...data, title: e.target.value })}
                placeholder="e.g. Senior Backend Engineer"
              />
            </Field>
            <Field label="Department">
              <input
                required
                value={data.department}
                onChange={(e) => setData({ ...data, department: e.target.value })}
                placeholder="e.g. Core Platform / Engineering"
              />
            </Field>
            <Field label="Location">
              <input
                required
                value={data.location}
                onChange={(e) => setData({ ...data, location: e.target.value })}
                placeholder="Bengaluru, Hyderabad, or Remote"
              />
            </Field>
            <Field label="Employment Type">
              <select
                value={data.type}
                onChange={(e) => setData({ ...data, type: e.target.value })}
              >
                {['Full-time', 'Part-time', 'Contract', 'Internship'].map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </Field>
            <Field label="Minimum Experience (years)">
              <input
                type="number"
                min="0"
                max="50"
                value={data.min}
                onChange={(e) => setData({ ...data, min: e.target.value })}
              />
            </Field>
            <Field label="Maximum Experience (years)">
              <input
                type="number"
                min="0"
                max="50"
                value={data.max}
                onChange={(e) => setData({ ...data, max: e.target.value })}
              />
            </Field>
            <Field label="Salary Min (optional)">
              <input
                type="number"
                min="0"
                value={data.salaryMin}
                onChange={(e) => setData({ ...data, salaryMin: e.target.value })}
                placeholder="₹ Min CTC"
              />
            </Field>
            <Field label="Salary Max (optional)">
              <input
                type="number"
                min="0"
                value={data.salaryMax}
                onChange={(e) => setData({ ...data, salaryMax: e.target.value })}
                placeholder="₹ Max CTC"
              />
            </Field>
            <Field label="Job Description & Responsibilities" wide>
              <textarea
                rows={8}
                required
                value={data.description}
                onChange={(e) => setData({ ...data, description: e.target.value })}
                placeholder="Describe the role, key responsibilities, and expected technical competencies…"
              />
            </Field>
          </div>

          <div className="form-divider">OR UPLOAD JD FILE</div>
          <UploadZone
            label="Upload existing JD (PDF or DOCX)"
            onParsed={handleParsedJd}
          />

          {/* Autonomous AI Extraction Callout */}
          <div className="preview-panel mt-6 p-4 rounded-lg bg-secondary/30 border border-primary/20 space-y-2">
            <div className="flex items-center gap-2 text-primary font-mono text-xs uppercase tracking-wider">
              <Sparkles size={15} />
              <span>Autonomous AI Engine JD Ingestion</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              No manual skill entry required. When you publish this job, the backend engine (
              <code className="text-foreground font-mono text-[11px]">parser.py</code>, LLM entity extractor,
              38-category technical skill ontology, and FAISS RAG template normalizer) automatically detects,
              canonicalizes, and separates all must-have vs. nice-to-have competencies directly from your raw text or file.
            </p>
          </div>

          {error && (
            <p className="error-text mt-4" role="alert">
              {error}
            </p>
          )}

          <div className="form-actions">
            <Button type="submit" disabled={busy}>
              {busy ? 'Publishing…' : 'Publish Job'}
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={busy}
              onClick={() => save(true)}
            >
              Save as Draft
            </Button>
          </div>
        </form>
      </main>
    </HrShell>
  );
}
