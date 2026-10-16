import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import { useState, useEffect } from 'react';
import { Briefcase, FileText, CheckCircle, XCircle, Plus, ArrowUpRight, Search, Award, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { HrShell } from '@/components/hr-shell';
import { EmptyState, Field, Modal } from '@/components/tribe-ui';
import { useTribe } from '@/lib/tribe-store';
import { pageHead } from '@/lib/tribe-data';
import { photos } from '@/lib/photos';

export const Route = createFileRoute('/hr/')({
  head: () =>
    pageHead(
      'HR Dashboard',
      'Manage placement drive job postings, applicants, shortlist decisions, and referrals.'
    ),
  component: Dashboard,
});

function Dashboard() {
  const { view: currentView } = Route.useSearch();
  const view = currentView ?? 'overview';
  const { jobs, applications, user, toast, refreshApplications, refreshJobs, deleteJob, updateJobStatus } = useTribe();
  const navigate = useNavigate();

  const [jobToDelete, setJobToDelete] = useState<any | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    void refreshApplications();
    void refreshJobs();
    const timer = setInterval(() => {
      void refreshApplications();
      void refreshJobs();
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  const [search, setSearch] = useState('');
  const [notify, setNotify] = useState(true);

  const recruiterName =
    user?.user_metadata?.full_name || (user?.email ? user.email.split('@')[0] : 'Recruiter');

  const totalAppsCount = applications.length;

  const shortlistedCount = applications.filter(
    (a) => a.status === 'Shortlisted' || a.decision === 'ADVANCE'
  ).length;

  const rejectedCount = applications.filter(
    (a) => a.status === 'Rejected' || a.decision === 'REJECT'
  ).length;

  const activeJobsCount = jobs.filter((j) => j.status === 'Active').length;

  const referralApps = applications.filter(
    (a) =>
      a.is_referral ||
      (a.referral_code && a.referral_code.trim() !== '') ||
      a.status === 'Referred'
  );

  const stats = [
    ['Active Jobs', String(activeJobsCount), 'Real-time sync', Briefcase],
    ['Total Applications', totalAppsCount.toLocaleString(), 'Supabase Cloud', FileText],
    ['Shortlisted (≥65)', shortlistedCount.toLocaleString(), 'Policy ADVANCE', CheckCircle],
    ['Rejected (<30)', rejectedCount.toLocaleString(), 'Policy REJECT', XCircle],
  ] as const;

  const title =
    ({
      overview: 'Dashboard',
      jobs: 'Job Postings',
      referrals: 'Referrals',
      candidates: 'Candidates',
      settings: 'Settings',
    } as const)[view as string] ?? 'Dashboard';

  const candidatePool = applications;

  return (
    <HrShell title={title} active={view}>
      <main className="hr-main">
        <div className="eyebrow">PLACEMENT DRIVE · HR OVERVIEW</div>
        <h1 className="mt-3!">
          {view === 'overview' ? `Welcome back, ${recruiterName}.` : title}
        </h1>
        <p className="muted text-xs">
          {view === 'overview'
            ? 'Here is where your hiring and multi-stage screening stands today.'
            : `Manage your ${title.toLowerCase()}.`}
        </p>

        {view === 'overview' && (
          <div className="overview-stats">
            <img src={photos[11]} alt="An office workspace" />
            {stats.map(([label, value, delta, Icon]) => (
              <div className="overview-card" key={label}>
                <span className="stat-label">{label}</span>
                <Icon />
                <strong>{value}</strong>
                <small className={label.includes('Rejected') ? 'text-danger' : 'text-success'}>
                  {delta}
                </small>
              </div>
            ))}
          </div>
        )}

        {(view === 'overview' || view === 'jobs') && (
          <section className={view === 'jobs' ? 'mt-8' : ''}>
            <div className="section-row">
              <h2>Your Job Postings</h2>
              <Button asChild variant="blue" size="sm">
                <Link to="/hr/create-job">
                  <Plus />
                  Create Job Posting
                </Link>
              </Button>
            </div>
            {jobs.length > 0 ? (
              <div className="table-container">
                <table className="responsive-table">
                  <thead>
                    <tr>
                      {['Job Title', 'Posted On', 'Status', 'Applications', 'Shortlisted', 'Rejected', 'Action'].map(
                        (s) => (
                          <th key={s}>{s}</th>
                        )
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {jobs.map((j) => {
                      const jobApps = applications.filter((a) => a.jobId === j.id);
                      const jobAdv = jobApps.filter(
                        (a) => a.status === 'Shortlisted' || a.decision === 'ADVANCE'
                      );
                      const jobRej = jobApps.filter(
                        (a) => a.status === 'Rejected' || a.decision === 'REJECT'
                      );

                      return (
                        <tr
                          className="clickable"
                          key={j.id}
                          onClick={() => navigate({ to: '/hr/jobs/$jobId', params: { jobId: j.id } })}
                        >
                          <td data-label="Job Title">
                            <Link to="/hr/jobs/$jobId" params={{ jobId: j.id }}>
                              {j.title}
                            </Link>
                          </td>
                          <td data-label="Posted On" className="muted text-xs">
                            {j.posted}
                          </td>
                          <td data-label="Status">
                            <span
                              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                                j.status === 'Active'
                                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/25'
                                  : 'bg-zinc-500/10 text-zinc-400 border border-zinc-500/20'
                              }`}
                            >
                              <span
                                className={`size-1.5 rounded-full ${
                                  j.status === 'Active' ? 'bg-emerald-400' : 'bg-zinc-400'
                                }`}
                              />
                              {j.status}
                            </span>
                          </td>
                          <td data-label="Applications" className="font-mono">
                            {jobApps.length}
                          </td>
                          <td data-label="Shortlisted" className="font-mono text-success">
                            {jobAdv.length}
                          </td>
                          <td data-label="Rejected" className="font-mono text-danger">
                            {jobRej.length}
                          </td>
                          <td data-label="Action" onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center gap-1">
                              <Button asChild variant="ghost" size="icon" title="View details">
                                <Link
                                  to="/hr/jobs/$jobId"
                                  params={{ jobId: j.id }}
                                  aria-label={`View ${j.title}`}
                                >
                                  <ArrowUpRight size={16} />
                                </Link>
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                                title="Delete job posting"
                                onClick={() => setJobToDelete(j)}
                              >
                                <Trash2 size={16} />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState text="No job postings yet.">
                <Button asChild variant="outline">
                  <Link to="/hr/create-job">Create your first job posting</Link>
                </Button>
              </EmptyState>
            )}
          </section>
        )}

        {(view === 'overview' || view === 'referrals') && (
          <section className="referral-panel">
            <div className="flex items-center justify-between mb-3">
              <h2>Referral Candidates</h2>
              <span className="text-xs text-muted-foreground font-mono">
                {referralApps.length} Verified Referrals
              </span>
            </div>
            {referralApps.length > 0 ? (
              <div className="flex flex-col gap-2">
                {referralApps.map((a) => (
                  <div className="referral-row" key={a.id}>
                    <div>
                      <strong>{a.name}</strong>
                      <small>{a.email}</small>
                    </div>
                    <div>
                      <span className="text-purple-400 font-mono text-xs">{a.referral_code || 'EMP-001'}</span>
                      <small>Referral Code</small>
                    </div>
                    <div>
                      {a.title}
                      <small>Job Applied</small>
                    </div>
                    <span className="font-mono text-success font-bold">{a.score}%</span>
                    <Button asChild variant="blue" size="sm">
                      <Link to="/hr/jobs/$jobId" params={{ jobId: a.jobId }}>
                        Review
                        <ArrowUpRight size={13} className="ml-1" />
                      </Link>
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState text="No referral candidates yet. When candidates apply with a referral code (e.g. EMP-001), they will appear here." />
            )}
          </section>
        )}

        {view === 'candidates' && (
          <>
            <div className="search-field mt-8 mb-6">
              <Search />
              <input
                className="control"
                aria-label="Search candidates"
                placeholder="Search candidate name or email…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            {candidatePool.length > 0 ? (
              <div className="table-container">
                <table className="responsive-table">
                  <thead>
                    <tr>
                      <th>Candidate</th>
                      <th>Email</th>
                      <th>Fit Score & Verdict</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {candidatePool
                      .filter(
                        (a) =>
                          a.name.toLowerCase().includes(search.toLowerCase()) ||
                          a.email.toLowerCase().includes(search.toLowerCase())
                      )
                      .map((a) => (
                        <tr key={a.id}>
                          <td data-label="Candidate">
                            <strong>{a.name}</strong>
                            {a.is_referral && (
                              <span className="ml-2 text-[10px] font-mono px-1 py-0.5 rounded bg-purple-500/20 text-purple-300">
                                {a.referral_code || 'EMP-001'}
                              </span>
                            )}
                          </td>
                          <td data-label="Email" className="muted text-xs">
                            {a.email}
                          </td>
                          <td data-label="Fit Score & Verdict">
                            <span
                              className={`font-mono font-semibold ${
                                a.score >= 65
                                  ? 'text-success'
                                  : a.score >= 30
                                  ? 'text-warning'
                                  : 'text-danger'
                              }`}
                            >
                              {a.score}%
                            </span>
                            <span className="text-[10px] uppercase font-mono ml-2 muted">
                              ({a.decision || (a.score >= 65 ? 'ADVANCE' : a.score >= 30 ? 'ESCALATE' : 'REJECT')})
                            </span>
                          </td>
                          <td data-label="Action">
                            <Button asChild variant="ghost" size="icon">
                              <Link
                                to="/hr/jobs/$jobId"
                                params={{ jobId: a.jobId }}
                                aria-label={`Review ${a.name}`}
                              >
                                <ArrowUpRight />
                              </Link>
                            </Button>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState text="No candidate applications received yet." />
            )}
          </>
        )}

        {view === 'settings' && (
          <form
            className="form-stack form-narrow mt-8"
            onSubmit={(e) => {
              e.preventDefault();
              toast('Settings saved.');
            }}
          >
            <Field label="Recruiter Name">
              <input defaultValue={recruiterName} required />
            </Field>
            <Field label="Advance Threshold (score ≥ X)">
              <input type="number" min={0} max={100} defaultValue={65} disabled />
              <small className="text-[11px] text-muted-foreground mt-1">
                Synced with backend policy ADVANCE_THRESHOLD = 65
              </small>
            </Field>
            <Field label="Escalate Threshold (score ≥ X)">
              <input type="number" min={0} max={100} defaultValue={30} disabled />
              <small className="text-[11px] text-muted-foreground mt-1">
                Synced with backend policy ESCALATE_THRESHOLD = 30
              </small>
            </Field>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={notify}
                onChange={(e) => setNotify(e.target.checked)}
              />
              Email me on new candidate submissions
            </label>
            <Button variant="blue" type="submit">
              Save Settings
            </Button>
          </form>
        )}
      </main>

      {/* Delete Job Modal */}
      {jobToDelete && (
        <Modal title="Delete Job Posting?" onClose={() => !isDeleting && setJobToDelete(null)}>
          <p className="text-sm text-foreground">
            Are you sure you want to permanently delete <strong>{jobToDelete.title}</strong>?
          </p>
          <p className="muted text-xs mt-2 leading-relaxed">
            This will permanently remove the job posting along with all its candidate applications, AI evaluation records, and fairness audits from the database. This action cannot be undone.
          </p>
          <div className="form-actions mt-6">
            <Button
              variant="destructive"
              disabled={isDeleting}
              onClick={async () => {
                setIsDeleting(true);
                try {
                  const success = await deleteJob(jobToDelete.id);
                  if (success) {
                    setJobToDelete(null);
                  }
                } finally {
                  setIsDeleting(false);
                }
              }}
            >
              {isDeleting ? 'Deleting...' : 'Delete Job Posting'}
            </Button>
            <Button variant="outline" disabled={isDeleting} onClick={() => setJobToDelete(null)}>
              Cancel
            </Button>
          </div>
        </Modal>
      )}
    </HrShell>
  );
}
