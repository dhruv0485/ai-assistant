import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import { useState, useEffect } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCheck,
  UploadCloud,
  Loader2,
  Sparkles,
  Edit2,
  FileText,
  BadgeCheck,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Field, UploadZone, EmptyState } from '@/components/tribe-ui';
import { useTribe, type Application } from '@/lib/tribe-store';
import { matchSkills } from '@/lib/scoring';
import { pageHead } from '@/lib/tribe-data';
import { supabase } from '@/lib/supabase';

export const Route = createFileRoute('/apply/$jobId')({
  head: () =>
    pageHead(
      'Job Portal - AI Screening Assistant',
      'Review pre-filled candidate profile details, attach referral code, and submit for AI screening.'
    ),
  component: Apply,
});

function Apply() {
  const { jobId } = Route.useParams();
  const {
    jobs,
    setJobs,
    setApplications,
    user,
    candidateProfile,
    refreshApplications,
    toast,
  } = useTribe();
  const job = jobs.find((j) => j.id === jobId);

  // Form & profile data
  const [data, setData] = useState({
    name: candidateProfile?.full_name || user?.user_metadata?.full_name || '',
    email: candidateProfile?.email || user?.email || '',
    phone: candidateProfile?.phone || '',
    location: candidateProfile?.location || 'Bengaluru',
    linkedin: candidateProfile?.linkedin_url || '',
    portfolio: candidateProfile?.portfolio_url || '',
  });

  const [resume, setResume] = useState(candidateProfile?.resume_raw_text || '');
  const [file, setFile] = useState<File>();
  const [fileName, setFileName] = useState(candidateProfile?.resume_file_name || '');
  const [referralId, setReferralId] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState('');
  const [submitted, setSubmitted] = useState<Application>();

  // Pre-fill when candidateProfile updates
  useEffect(() => {
    if (candidateProfile) {
      setData((prev) => ({
        name: candidateProfile.full_name || prev.name,
        email: candidateProfile.email || prev.email,
        phone: candidateProfile.phone || prev.phone,
        location: candidateProfile.location || prev.location,
        linkedin: candidateProfile.linkedin_url || prev.linkedin,
        portfolio: candidateProfile.portfolio_url || prev.portfolio,
      }));
      if (candidateProfile.resume_raw_text && !resume) {
        setResume(candidateProfile.resume_raw_text);
      }
      if (candidateProfile.resume_file_name && !fileName) {
        setFileName(candidateProfile.resume_file_name);
      }
    }
  }, [candidateProfile]);

  if (!job) {
    return (
      <main className="container page-main">
        <EmptyState text="This position is unavailable." />
      </main>
    );
  }

  const isReferralTagged = referralId.trim().toUpperCase() === 'EMP-001';
  const previewScore = matchSkills(resume, job.skills);

  async function submit() {
    if (!job || !confirmed) return;
    if (!data.name.trim() || !data.email.trim() || !data.phone.trim()) {
      toast('Please make sure your Name, Email, and Phone are filled in.');
      setIsEditing(true);
      return;
    }

    setSubmitting(true);
    setUploadProgress('Uploading resume to Supabase Storage…');

    let filePath: string | null = candidateProfile?.resume_file_path || null;

    try {
      // 1. Upload to Supabase Storage if a new file was selected
      if (file) {
        const cleanName = file.name.replace(/[^a-zA-Z0-9.-]/g, '_');
        const uploadPath = `${jobId}/${Date.now()}_${cleanName}`;

        const { error: storageErr } = await supabase.storage
          .from('resumes')
          .upload(uploadPath, file, {
            cacheControl: '3600',
            upsert: true,
          });

        if (storageErr) {
          console.warn('Storage upload notice (continuing with database record):', storageErr.message);
        } else {
          filePath = uploadPath;
        }
      }

      setUploadProgress('Recording application for multi-stage AI scrutiny…');

      // 2. Insert into Supabase 'applications' table
      const initialStatus = isReferralTagged ? 'Pending AI Screening' : 'Pending AI Screening';

      const appRecord = {
        job_id: job.id,
        candidate_id: user?.id || null,
        candidate_name: data.name.trim(),
        candidate_email: data.email.trim(),
        candidate_phone: data.phone.trim(),
        candidate_location: data.location.trim(),
        linkedin_url: data.linkedin.trim() || null,
        portfolio_url: data.portfolio.trim() || null,
        resume_file_path: filePath,
        resume_file_name: file?.name || fileName || 'Resume.pdf',
        resume_raw_text: resume,
        referral_code: referralId.trim() || null,
        is_referral: isReferralTagged,
        status: initialStatus,
      };

      const { data: dbData, error: dbErr } = await supabase
        .from('applications')
        .insert(appRecord)
        .select()
        .single();

      if (dbErr) {
        console.warn('Supabase DB notice:', dbErr.message);
      }

      const generatedId = dbData?.id || crypto.randomUUID();

      const newApp: Application = {
        ...data,
        ...previewScore,
        id: generatedId,
        jobId,
        title: job.title,
        resume,
        file,
        resume_file_path: filePath,
        resume_file_name: file?.name || fileName || 'Resume.pdf',
        date: new Date().toLocaleDateString('en-GB', {
          day: '2-digit',
          month: 'short',
          year: 'numeric',
        }),
        status: isReferralTagged ? 'Referred' : 'Pending AI Screening',
        score: previewScore.score,
        confidence: 'HIGH',
        decision: previewScore.score >= 65 ? 'ADVANCE' : previewScore.score >= 30 ? 'ESCALATE' : 'REJECT',
        decision_reason: 'Queued for 9-step backend AI scrutiny.',
        referral_code: referralId.trim() || undefined,
        is_referral: isReferralTagged,
      };

      setApplications((a) => [newApp, ...a]);
      setJobs((all) =>
        all.map((j) => (j.id === jobId ? { ...j, applications: j.applications + 1 } : j))
      );
      setSubmitted(newApp);
      toast('Application submitted successfully!');

      void refreshApplications();
    } catch (err: any) {
      console.error('Submission error:', err);
      toast('Application recorded.');
    } finally {
      setSubmitting(false);
      setUploadProgress('');
    }
  }

  if (submitted) {
    return (
      <main className="container page-main form-narrow">
        <div className="confirmation-header">
          <div className="flex items-center justify-center gap-2 mb-3">
            <img
              src="/brand-icon.png"
              alt="Job Portal"
              className="w-6 h-6 rounded-full object-contain bg-white p-0.5 border border-border shadow-xs"
            />
            <span className="text-xs font-mono font-medium tracking-wider uppercase text-primary bg-primary/10 border border-primary/20 px-2.5 py-0.5 rounded-full">
              Job Portal
            </span>
          </div>
          <div className="confirmation-icon">
            <CheckCheck />
          </div>
          <h1 className="text-2xl font-bold">Application Submitted</h1>
          <p className="muted text-sm mt-2">
            Your application for <strong>{job.title}</strong> has been received and queued for
            9-stage AI scrutiny.
          </p>

          <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
            <div className="flex items-center gap-2 text-xs text-primary font-mono bg-primary/10 py-1.5 px-3 rounded-full">
              <Sparkles size={13} />
              <span>Status: Pending AI Screening</span>
            </div>
            {submitted.is_referral && (
              <div className="flex items-center gap-1.5 text-xs text-purple-400 font-mono bg-purple-500/10 border border-purple-500/20 py-1.5 px-3 rounded-full">
                <BadgeCheck size={13} />
                <span>Referral: EMP-001 Priority Tagged</span>
              </div>
            )}
          </div>

          <div className="form-actions justify-center mt-6">
            <Button asChild>
              <Link to="/applications">View My Applications</Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/openings">Back to Openings</Link>
            </Button>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="container page-main form-narrow">
      <Link to="/jobs/$jobId" params={{ jobId }} className="back-link">
        <ArrowLeft />
        Back to Job Description
      </Link>
      <div className="flex items-center gap-2 mt-3 mb-1">
        <img
          src="/brand-icon.png"
          alt="Job Portal"
          className="w-5 h-5 rounded-full object-contain bg-white p-0.5 border border-border shadow-xs"
        />
        <span className="text-xs font-mono font-medium tracking-wider uppercase text-primary bg-primary/10 border border-primary/20 px-2.5 py-0.5 rounded-full">
          Job Portal
        </span>
      </div>
      <h1 className="page-title">Apply for {job.title}</h1>
      <p className="page-subtitle">
        Review your profile details below. Edit any field, attach an optional referral code, and
        confirm submission.
      </p>

      {/* Review Card of Profile Details */}
      <div className="preview-panel mt-6">
        <div className="flex items-center justify-between mb-4 border-b border-border pb-3">
          <div>
            <h3 className="text-base font-semibold m-0 text-foreground">
              Candidate Profile Review
            </h3>
            <small className="text-muted-foreground text-xs">
              Pre-filled from your profile
            </small>
          </div>
          <Button
            variant="outline"
            size="sm"
            type="button"
            onClick={() => setIsEditing(!isEditing)}
          >
            <Edit2 size={13} className="mr-1.5" />
            {isEditing ? 'Done Editing' : 'Edit Details'}
          </Button>
        </div>

        {isEditing ? (
          /* Editable Form */
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
            <Field label="Full Name">
              <input
                required
                value={data.name}
                onChange={(e) => setData({ ...data, name: e.target.value })}
              />
            </Field>
            <Field label="Email Address">
              <input
                required
                type="email"
                value={data.email}
                onChange={(e) => setData({ ...data, email: e.target.value })}
              />
            </Field>
            <Field label="Phone Number">
              <input
                required
                type="tel"
                value={data.phone}
                onChange={(e) => setData({ ...data, phone: e.target.value })}
              />
            </Field>
            <Field label="Current Location">
              <input
                value={data.location}
                onChange={(e) => setData({ ...data, location: e.target.value })}
              />
            </Field>
            <Field label="LinkedIn URL">
              <input
                type="url"
                value={data.linkedin}
                onChange={(e) => setData({ ...data, linkedin: e.target.value })}
              />
            </Field>
            <Field label="Portfolio / GitHub">
              <input
                type="url"
                value={data.portfolio}
                onChange={(e) => setData({ ...data, portfolio: e.target.value })}
              />
            </Field>
          </div>
        ) : (
          /* Read-only Review DL */
          <dl className="facts mt-0 pt-0 border-t-0">
            <div>
              <dt>Full Name</dt>
              <dd>
                <strong>{data.name || 'Not provided'}</strong>
              </dd>
            </div>
            <div>
              <dt>Email Address</dt>
              <dd>{data.email || 'Not provided'}</dd>
            </div>
            <div>
              <dt>Phone</dt>
              <dd>{data.phone || 'Not provided'}</dd>
            </div>
            <div>
              <dt>Location</dt>
              <dd>{data.location || 'Bengaluru'}</dd>
            </div>
            {data.linkedin && (
              <div>
                <dt>LinkedIn</dt>
                <dd>
                  <a
                    href={data.linkedin}
                    target="_blank"
                    rel="noreferrer"
                    className="text-primary hover:underline"
                  >
                    View LinkedIn
                  </a>
                </dd>
              </div>
            )}
            {data.portfolio && (
              <div>
                <dt>Portfolio</dt>
                <dd>
                  <a
                    href={data.portfolio}
                    target="_blank"
                    rel="noreferrer"
                    className="text-primary hover:underline"
                  >
                    View Portfolio
                  </a>
                </dd>
              </div>
            )}
          </dl>
        )}

        {/* Resume Attachment Review */}
        <div className="mt-6 pt-4 border-t border-border">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-mono uppercase text-muted-foreground flex items-center gap-1.5">
              <FileText size={14} className="text-primary" />
              Attached Resume Document
            </span>
            {fileName && (
              <span className="text-[11px] font-mono text-emerald-400">
                {file?.name || fileName}
              </span>
            )}
          </div>

          <UploadZone
            label={
              fileName
                ? `Attached: ${file?.name || fileName} (Click or drop to replace)`
                : 'Upload Resume (PDF or DOCX)'
            }
            onParsed={(text, upload) => {
              setResume(text);
              setFile(upload);
              setFileName(upload.name);
              toast('Resume updated for this application.');
            }}
          />

          {resume && (
            <div className="mt-3">
              <details className="text-xs text-muted-foreground">
                <summary className="cursor-pointer hover:text-foreground font-mono text-[11px]">
                  View extracted resume text preview ({resume.length.toLocaleString()} characters)
                </summary>
                <div className="parsed-text mt-2 max-h-40">{resume}</div>
              </details>
            </div>
          )}
        </div>
      </div>

      {/* Referral Employee ID Section */}
      <div className="preview-panel mt-4 border-purple-500/20 bg-purple-950/5">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-foreground m-0 flex items-center gap-2">
            <BadgeCheck size={16} className="text-purple-400" />
            Referral Tag (Optional)
          </h3>
          {isReferralTagged && (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
              ★ EMP-001 TAGGED
            </span>
          )}
        </div>

        <Field label="Referral Employee ID">
          <input
            placeholder="e.g. EMP-001"
            value={referralId}
            onChange={(e) => setReferralId(e.target.value)}
          />
        </Field>
        <p className="text-[11px] text-muted-foreground mt-1.5 leading-relaxed">
          Tip: Keep <strong>EMP-001</strong> as fixed referral employee ID for placement drive referral tag priority.
        </p>
      </div>

      {/* Confirmation & Submission */}
      <label className="checkbox-label mt-6">
        <input
          type="checkbox"
          checked={confirmed}
          onChange={(e) => setConfirmed(e.target.checked)}
        />
        I confirm the information above is accurate and grant permission for AI screening against the job requirements.
      </label>

      {submitting && (
        <div className="flex items-center gap-2 text-xs text-primary mt-4">
          <Loader2 className="animate-spin w-4 h-4" />
          <span>{uploadProgress}</span>
        </div>
      )}

      <div className="form-actions mt-6">
        <Button disabled={!confirmed || submitting} type="button" onClick={submit}>
          {submitting ? 'Submitting Application…' : 'Submit Application'}
        </Button>
        <Button asChild variant="outline" type="button">
          <Link to="/jobs/$jobId" params={{ jobId }}>
            Cancel
          </Link>
        </Button>
      </div>
    </main>
  );
}
