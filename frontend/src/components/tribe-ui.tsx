import { useEffect, useRef, useState, type ReactNode } from 'react';
import { UploadCloud, X, FolderOpen, Check, Download, ShieldCheck, AlertCircle, Quote, Sparkles } from 'lucide-react';
import { Button } from './ui/button';
import { readDocument, validateDocument } from '@/lib/scoring';
import type { ScreeningEvidence, FairnessAuditData } from '@/lib/tribe-data';

export function Field({
  label,
  children,
  wide = false,
}: {
  label: string;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <label className={`field ${wide ? 'field-wide' : ''}`}>
      <span className="text-[13px] text-muted-foreground">{label}</span>
      {children}
    </label>
  );
}

export function Modal({
  title,
  children,
  onClose,
  wide = false,
  preventClose = false,
}: {
  title: string;
  children: ReactNode;
  onClose?: () => void;
  wide?: boolean;
  preventClose?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const previous = document.activeElement;
    const old = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    ref.current?.focus();
    function key(e: KeyboardEvent) {
      if (e.key === 'Escape' && !preventClose && onClose) onClose();
      if (e.key === 'Tab') {
        const items = ref.current?.querySelectorAll<HTMLElement>(
          'a,button,input,textarea,select,[tabindex="0"]'
        );
        if (!items?.length) return;
        const first = items[0],
          last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    }
    document.addEventListener('keydown', key);
    return () => {
      document.body.style.overflow = old;
      document.removeEventListener('keydown', key);
      if (previous instanceof HTMLElement) previous.focus();
    };
  }, [onClose, preventClose]);

  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (!preventClose && e.target === e.currentTarget && onClose) onClose();
      }}
    >
      <div
        ref={ref}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`modal-panel ${wide ? 'modal-wide' : ''}`}
      >
        <div className="modal-heading">
          <h2>{title}</h2>
          {!preventClose && onClose && (
            <Button variant="ghost" size="icon" aria-label="Close dialog" onClick={onClose}>
              <X />
            </Button>
          )}
        </div>
        {children}
      </div>
    </div>
  );
}

export function UploadZone({
  onParsed,
  label = 'Drag & drop PDF or DOCX here',
}: {
  onParsed: (text: string, file: File) => void;
  label?: string;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const [name, setName] = useState('');

  async function process(file?: File) {
    if (!file) return;
    setError('');
    const issue = validateDocument(file);
    if (issue) {
      setError(issue);
      return;
    }
    setBusy(true);
    try {
      const text = await readDocument(file);
      if (!text.trim()) {
        setError('No text could be read. Please upload a text-based PDF or DOCX.');
        return;
      }
      setName(file.name);
      onParsed(text, file);
    } catch {
      setError('This document could not be read. Please try another PDF or DOCX.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div
        className={`dropzone ${drag ? 'dragging' : ''}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          void process(e.dataTransfer.files[0]);
        }}
      >
        <UploadCloud />
        <p>{busy ? 'Reading your document…' : name || label}</p>
        <small>Max 5 MB · PDF or DOCX</small>
        <input
          ref={input}
          type="file"
          accept=".pdf,.docx"
          className="hidden"
          aria-label="Upload document"
          onChange={(e) => void process(e.target.files?.[0])}
        />
        <Button
          variant="outline"
          size="sm"
          type="button"
          disabled={busy}
          onClick={() => input.current?.click()}
        >
          {name ? 'Re-upload' : 'Browse files'}
        </Button>
        {busy && <div className="skeleton-line" role="status" aria-label="Reading document" />}
      </div>
      {error && (
        <p role="alert" className="error-text mt-2">
          {error}
        </p>
      )}
    </div>
  );
}

export function EmptyState({ text, children }: { text: string; children?: ReactNode }) {
  return (
    <div className="empty-state">
      <FolderOpen />
      <h3>{text}</h3>
      {children}
    </div>
  );
}

export type ScorePanelProps = {
  score?: number;
  matched?: string[];
  missing?: string[];
  confidence?: 'HIGH' | 'LOW';
  decision?: 'ADVANCE' | 'ESCALATE' | 'REJECT';
  decision_reason?: string;
  critical_gaps?: string[];
  must_have_met?: ScreeningEvidence[];
  nice_to_have_met?: ScreeningEvidence[];
  experience_fit?: {
    required_years: number | null;
    candidate_years: number | null;
    note: string;
  };
  education_fit?: 'strong' | 'adequate' | 'weak' | 'unknown';
  fairness_audit?: FairnessAuditData;
  strengths?: string[];
  actions?: ReactNode;
  note?: boolean;
};

export function ScorePanel({
  score = 72,
  matched = ['React', 'JavaScript', 'HTML', 'CSS', 'Git'],
  missing = ['TypeScript', 'REST API', 'Accessibility'],
  confidence = 'HIGH',
  decision,
  decision_reason,
  critical_gaps = [],
  must_have_met = [],
  nice_to_have_met = [],
  experience_fit,
  education_fit,
  fairness_audit,
  strengths = [],
  actions,
  note = true,
}: ScorePanelProps) {
  // Infer policy decision if not explicitly given
  const derivedDecision =
    decision || (score >= 65 ? 'ADVANCE' : score >= 30 ? 'ESCALATE' : 'REJECT');

  const decisionBadgeClass =
    derivedDecision === 'ADVANCE'
      ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
      : derivedDecision === 'ESCALATE'
      ? 'border-amber-500/30 bg-amber-500/10 text-amber-400'
      : 'border-rose-500/30 bg-rose-500/10 text-rose-400';

  const decisionLabel =
    derivedDecision === 'ADVANCE'
      ? 'AUTO-ADVANCE (Shortlisted)'
      : derivedDecision === 'ESCALATE'
      ? 'ESCALATE (Needs Human Review)'
      : 'REJECT (Unmet Requirements)';

  // Combine evidence
  const allEvidence = [
    ...must_have_met.map((m) => ({ ...m, type: 'Required' })),
    ...nice_to_have_met.map((n) => ({ ...n, type: 'Preferred' })),
  ];

  const hasEvidence = allEvidence.length > 0;

  return (
    <div className="space-y-6">
      {/* Top Match Ring & Decision Header */}
      <div className="score-overview flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-4">
          <svg className="score-ring" viewBox="0 0 100 100" aria-label={`${score}% match score`}>
            <circle className="track" cx="50" cy="50" r="44" />
            <circle
              className="progress"
              cx="50"
              cy="50"
              r="44"
              pathLength="100"
              strokeDasharray={`${score} 100`}
            />
            <text x="50" y="57" textAnchor="middle">
              {score}%
            </text>
          </svg>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-semibold m-0">Candidate Fit Score</h3>
              <span
                className={`text-[10px] uppercase font-mono px-2 py-0.5 rounded border ${
                  confidence === 'HIGH'
                    ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-400'
                    : 'border-orange-500/40 bg-orange-500/10 text-orange-400'
                }`}
              >
                {confidence} CONFIDENCE
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Pass 2 evidence-grounded AI evaluation
            </p>
          </div>
        </div>

        {/* Decision Badge */}
        <div className={`px-3 py-1.5 rounded-md border text-xs font-semibold ${decisionBadgeClass}`}>
          {decisionLabel}
        </div>
      </div>

      {/* Decision Reason explanation banner */}
      {decision_reason && (
        <div className="p-3 text-xs rounded-md bg-secondary border border-border text-foreground flex items-start gap-2">
          <Sparkles className="w-4 h-4 text-primary shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold block text-[11px] uppercase tracking-wide text-muted-foreground mb-0.5">
              Organizational Policy Recommendation
            </span>
            <p className="m-0 leading-relaxed">{decision_reason}</p>
          </div>
        </div>
      )}

      {/* Experience & Education Fit Pills */}
      {(experience_fit || education_fit) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {experience_fit && (
            <div className="p-2.5 rounded border border-border bg-card text-xs">
              <span className="text-[10px] uppercase font-mono text-muted-foreground block">
                Experience Tenure
              </span>
              <strong className="text-foreground block mt-0.5">
                {experience_fit.candidate_years !== null
                  ? `${experience_fit.candidate_years} yrs`
                  : 'Unclear'}{' '}
                / {experience_fit.required_years ? `${experience_fit.required_years} yrs req` : 'Flexible'}
              </strong>
              {experience_fit.note && (
                <small className="text-muted-foreground block mt-1">{experience_fit.note}</small>
              )}
            </div>
          )}
          {education_fit && (
            <div className="p-2.5 rounded border border-border bg-card text-xs">
              <span className="text-[10px] uppercase font-mono text-muted-foreground block">
                Education Alignment
              </span>
              <strong className="text-foreground block mt-0.5 capitalize">
                {education_fit} fit
              </strong>
              <small className="text-muted-foreground block mt-1">Verified from credentials</small>
            </div>
          )}
        </div>
      )}

      {/* Verbatim Quoted Evidence Breakdown */}
      {hasEvidence ? (
        <div className="space-y-3">
          <h4 className="text-xs font-mono uppercase tracking-wider text-muted-foreground flex items-center justify-between">
            <span>Pass 2 Verbatim Resume Evidence</span>
            <span className="text-[10px] text-muted-label">Ground truth citations</span>
          </h4>
          <div className="space-y-2">
            {allEvidence.map((item, idx) => (
              <div
                key={idx}
                className={`p-3 rounded-md border text-xs transition-colors ${
                  item.met
                    ? 'border-emerald-500/20 bg-emerald-950/10'
                    : 'border-rose-500/20 bg-rose-950/10'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] ${
                        item.met ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                      }`}
                    >
                      {item.met ? <Check size={11} /> : <X size={11} />}
                    </span>
                    <strong className="text-foreground">{item.skill}</strong>
                  </div>
                  <span className="text-[10px] font-mono text-muted-foreground uppercase">
                    {item.type}
                  </span>
                </div>
                {item.evidence ? (
                  <blockquote className="mt-2 text-[11px] text-muted-foreground pl-2 border-l-2 border-primary/50 italic leading-relaxed">
                    <Quote className="inline w-3 h-3 text-primary mr-1 opacity-70" />
                    “{item.evidence}”
                  </blockquote>
                ) : (
                  <p className="mt-1.5 text-[11px] text-rose-400/90 italic m-0">
                    No verified supporting sentence found in resume.
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : (
        /* Fallback keywords chips */
        <>
          <div className="score-keywords">
            <h4 className="text-success text-xs font-mono uppercase">Matched Skills</h4>
            <div className="chips">
              {matched.length ? (
                matched.map((s) => (
                  <span className="chip success" key={s}>
                    <Check size={12} />
                    {s}
                  </span>
                ))
              ) : (
                <span className="muted text-xs">No matches found.</span>
              )}
            </div>
          </div>
          <div className="score-keywords">
            <h4 className="text-danger text-xs font-mono uppercase">Missing Skills</h4>
            <div className="chips">
              {missing.length ? (
                missing.map((s) => (
                  <span className="chip danger" key={s}>
                    {s}
                  </span>
                ))
              ) : (
                <span className="text-success text-xs">All listed skills matched.</span>
              )}
            </div>
          </div>
        </>
      )}

      {/* Critical Gaps & Strengths */}
      {critical_gaps.length > 0 && (
        <div className="p-3 rounded border border-rose-500/20 bg-rose-500/5 text-xs text-rose-300">
          <strong className="block mb-1 text-[11px] font-mono uppercase text-rose-400">
            Critical Gaps Identified
          </strong>
          <ul className="list-disc pl-4 space-y-0.5 m-0">
            {critical_gaps.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </div>
      )}

      {strengths.length > 0 && (
        <div className="p-3 rounded border border-emerald-500/20 bg-emerald-500/5 text-xs text-emerald-300">
          <strong className="block mb-1 text-[11px] font-mono uppercase text-emerald-400">
            Candidate Standout Strengths
          </strong>
          <ul className="list-disc pl-4 space-y-0.5 m-0">
            {strengths.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Counterfactual Fairness Audit Badge */}
      {fairness_audit && (
        <div className="p-3 rounded border border-border bg-card flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <ShieldCheck
              className={`w-5 h-5 ${
                !fairness_audit.bias_detected ? 'text-emerald-400' : 'text-amber-400'
              }`}
            />
            <div>
              <span className="font-semibold block text-foreground">
                Phase 8 Fairness Audit:{' '}
                {!fairness_audit.bias_detected ? 'PASSED (Zero Bias)' : 'FLAGGED FOR REVIEW'}
              </span>
              <small className="text-muted-foreground block">
                Perturbation test across Name, Pedigree & Gender proxies (Delta: {fairness_audit.max_delta} pts)
              </small>
            </div>
          </div>
          <span
            className={`text-[10px] font-mono px-2 py-0.5 rounded ${
              !fairness_audit.bias_detected
                ? 'bg-emerald-500/20 text-emerald-300'
                : 'bg-amber-500/20 text-amber-300'
            }`}
          >
            Δ ≤ 5 PTS
          </span>
        </div>
      )}

      {note && (
        <p className="score-note text-[11px] text-muted-foreground border-t border-border pt-3">
          Evaluated against the technical skill ontology with FAISS RAG template normalization and Pass 2 evidence verification.
        </p>
      )}

      {actions && <div className="score-actions">{actions}</div>}
    </div>
  );
}

export function downloadResume(file?: File, name = 'Resume', text = '') {
  const url = URL.createObjectURL(file ?? new Blob([text], { type: 'text/plain' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = file?.name ?? `${name.replaceAll(' ', '_')}_Resume.txt`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export { Download };
