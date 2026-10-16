import { createFileRoute, Link } from '@tanstack/react-router';
import { useState } from 'react';
import { ArrowUpRight, Sparkles, Clock, CheckCircle2 } from 'lucide-react';
import { pageHead } from '@/lib/tribe-data';
import { useTribe, type Application } from '@/lib/tribe-store';
import { Button } from '@/components/ui/button';
import { EmptyState, Modal, ScorePanel } from '@/components/tribe-ui';
import { photos } from '@/lib/photos';

export const Route = createFileRoute('/applications')({
  head: () =>
    pageHead(
      'My Applications',
      'View your applications, match scores, and placement drive application status.',
      photos[15]
    ),
  component: History,
});

function History() {
  const { applications } = useTribe();
  const [selected, setSelected] = useState<Application>();

  return (
    <main className="container page-main page-narrow">
      <div className="page-banner">
        <img src={photos[15]} alt="Printed applications and notes on a desk" />
        <h1>My Applications</h1>
        <p>Real-time updates on your applications and multi-stage AI screening results.</p>
      </div>

      {applications.length ? (
        <div className="table-container">
          <table className="responsive-table">
            <thead>
              <tr>
                {['Job Title', 'Applied On', 'Fit Score', 'Verdict / Status', 'Details'].map((s) => (
                  <th key={s}>{s}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {applications.map((a) => {
                const isShortlisted = a.status === 'Shortlisted' || a.decision === 'ADVANCE';
                const isRejected = a.status === 'Rejected' || a.decision === 'REJECT';
                const isPending = a.status === 'Pending AI Screening' || a.status === 'Under Review';
                const isEscalated =
                  a.status === 'Escalated to Recruiter' || a.decision === 'ESCALATE';

                return (
                  <tr className="clickable" key={a.id} onClick={() => setSelected(a)}>
                    <td data-label="Job Title">
                      <strong>{a.title}</strong>
                      <small className="block text-[11px] text-muted-foreground">
                        {a.resume_file_name || 'Resume'}
                      </small>
                    </td>
                    <td data-label="Applied On" className="muted text-xs">
                      {a.date}
                    </td>
                    <td data-label="Fit Score">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`font-mono font-semibold ${
                            isShortlisted
                              ? 'text-success'
                              : isPending
                              ? 'text-primary'
                              : isEscalated
                              ? 'text-warning'
                              : 'text-danger'
                          }`}
                        >
                          {a.score > 0 ? `${a.score}%` : 'Evaluating'}
                        </span>
                        {a.confidence && (
                          <small className="text-[10px] font-mono text-muted-foreground">
                            ({a.confidence})
                          </small>
                        )}
                      </div>
                    </td>
                    <td data-label="Verdict / Status">
                      <span
                        className={`status ${
                          isShortlisted
                            ? 'text-success'
                            : isRejected
                            ? 'text-danger'
                            : isEscalated
                            ? 'text-warning'
                            : isPending
                            ? 'text-primary'
                            : 'muted'
                        }`}
                      >
                        {a.status}
                      </span>
                    </td>
                    <td data-label="Details">
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`View ${a.title} application`}
                        onClick={() => setSelected(a)}
                      >
                        <ArrowUpRight />
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState text="You haven't submitted any applications yet.">
          <Button asChild variant="blue">
            <Link to="/openings">Browse Open Positions</Link>
          </Button>
        </EmptyState>
      )}

      {selected && (
        <Modal title={selected.title} wide onClose={() => setSelected(undefined)}>
          <div className="p-3 bg-secondary rounded border border-border mb-6 flex items-center justify-between text-xs">
            <div>
              <strong>{selected.name}</strong> · Applied {selected.date}
            </div>
            <span className="font-mono text-primary">{selected.status}</span>
          </div>

          <ScorePanel
            score={selected.score}
            confidence={selected.confidence}
            decision={selected.decision}
            decision_reason={selected.decision_reason}
            must_have_met={selected.must_have_met}
            nice_to_have_met={selected.nice_to_have_met}
            experience_fit={selected.experience_fit}
            education_fit={selected.education_fit}
            fairness_audit={selected.fairness_audit}
            critical_gaps={selected.critical_gaps}
            matched={selected.matched}
            missing={selected.missing}
          />

          <div className="mt-6 border-t border-border pt-4 flex justify-between items-center">
            <Button asChild variant="blue">
              <Link to="/jobs/$jobId" params={{ jobId: selected.jobId }}>
                View Job Description
                <ArrowUpRight />
              </Link>
            </Button>
            <Button variant="outline" onClick={() => setSelected(undefined)}>
              Close
            </Button>
          </div>
        </Modal>
      )}
    </main>
  );
}
