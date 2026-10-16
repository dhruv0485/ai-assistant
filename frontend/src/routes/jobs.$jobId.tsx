import { createFileRoute, Link } from '@tanstack/react-router';
import { useEffect } from 'react';
import { ArrowLeft, MapPin, Briefcase, ArrowRight, CheckCircle2 } from 'lucide-react';
import { useTribe } from '@/lib/tribe-store';
import { pageHead } from '@/lib/tribe-data';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/tribe-ui';
import { photos } from '@/lib/photos';

export const Route = createFileRoute('/jobs/$jobId')({
  head: () =>
    pageHead(
      'Job Details & Apply',
      'Review the role, requirements, and job details before applying to the Hunt Your Tribe placement drive.'
    ),
  component: JobDetail,
});

function JobDetail() {
  const { jobId } = Route.useParams();
  const { jobs, applications, user, candidateProfile, refreshJobs, refreshApplications } = useTribe();

  useEffect(() => {
    void refreshJobs();
    void refreshApplications();
  }, [jobId]);

  const job = jobs.find((j) => j.id === jobId);

  const candidateEmail = (user?.email || candidateProfile?.email || '').trim().toLowerCase();
  const hasApplied = Boolean(
    candidateEmail &&
    applications.some(
      (a) => a.jobId === jobId && (a.email || '').trim().toLowerCase() === candidateEmail
    )
  );

  if (!job) {
    return (
      <main className="container page-main">
        <EmptyState text="This position is unavailable or has been removed.">
          <Link to="/openings" className="text-primary">
            Back to Openings
          </Link>
        </EmptyState>
      </main>
    );
  }

  return (
    <main className="container page-main page-narrow">
      <Link to="/openings" className="back-link">
        <ArrowLeft size={16} />
        Back to Openings
      </Link>
      <div className="flex items-center gap-2 mt-2 mb-1">
        <img
          src="/brand-icon.png"
          alt="Job Portal"
          className="w-5 h-5 rounded-full object-contain bg-white p-0.5 border border-border shadow-xs"
        />
        <span className="text-xs font-mono font-medium tracking-wider uppercase text-primary bg-primary/10 border border-primary/20 px-2.5 py-0.5 rounded-full">
          Job Portal
        </span>
      </div>
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="page-title">{job.title}</h1>
        {hasApplied && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 size={13} />
            Submitted
          </span>
        )}
      </div>
      <div className="job-meta">
        <MapPin size={14} />
        {job.location}
        <span>·</span>
        <Briefcase size={14} />
        {job.type}
        <span>·</span>
        {job.department}
      </div>
      <div className="detail-grid">
        <article className="jd-content">
          <h2>About the role</h2>
          <p className="whitespace-pre-line">{job.summary}</p>
          <h2>What you'll do</h2>
          <ul>
            <li>Work closely with a collaborative team to build and improve useful products.</li>
            <li>Take ownership of well-defined projects, from planning through delivery.</li>
            <li>Communicate clearly, share knowledge, and contribute to thoughtful decisions.</li>
          </ul>
          <h2>What we're looking for</h2>
          <ul>
            {job.skills && job.skills.length > 0 ? (
              job.skills.map((s) => <li key={s}>Practical experience with {s}.</li>)
            ) : (
              <li>Key technical and domain skills listed in the job description.</li>
            )}
            <li>{job.experience} of relevant experience.</li>
          </ul>
          <h2>Education</h2>
          <p>
            A relevant degree or equivalent practical experience. We value demonstrated skills and a
            willingness to learn.
          </p>
        </article>
        <aside className="sticky-panel">
          {hasApplied ? (
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/25 text-center mb-4">
              <div className="inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-400 mb-1">
                <CheckCircle2 size={16} />
                Application Submitted
              </div>
              <p className="text-xs text-muted-foreground mb-3">
                You have already submitted your application for this position.
              </p>
              <Button asChild variant="outline" size="sm" className="w-full">
                <Link to="/applications">View My Applications</Link>
              </Button>
            </div>
          ) : job.status === 'Active' ? (
            <Button asChild className="w-full">
              <Link to="/apply/$jobId" params={{ jobId: job.id }}>
                Apply Now
                <ArrowRight size={16} />
              </Link>
            </Button>
          ) : (
            <p className="muted">This position is closed.</p>
          )}
          <dl className="facts">
            {[
              ['Location', job.location],
              ['Experience', job.experience],
              ['Posted date', job.posted],
              ['Applicants', String(job.applications || 0)],
            ].map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>
          <img
            className="sidebar-photo"
            src={photos[13]}
            alt="A candidate reviewing documents on a laptop"
            loading="lazy"
          />
        </aside>
      </div>
    </main>
  );
}
