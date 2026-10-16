import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, Check, FileJson, Pause, Play, RotateCcw, ShieldCheck } from 'lucide-react';
import { Button } from './ui/button';

const stages = [
  { short: 'Ingest', title: 'Documents in. Personal contact details out.', module: 'src/parser.py', operation: 'INGESTION & PRIVACY', description: 'Resume and job description follow separate parsing paths. Whitespace is cleaned; resume email and phone fields are masked before model extraction.', facts: [['Format-aware parsing', 'PDF → pdfplumber · DOCX → python-docx · TXT → text'], ['Privacy boundary', 'Email and phone masking occurs before the LLM call. This is not full anonymization.'], ['Preserved signal', 'Skills, employment history, education and supporting sentences remain available.']] },
  { short: 'Extract', title: 'Turn unstructured text into explicit requirements.', module: 'src/extractor.py · src/skill_ontology.py', operation: 'PASS 1 / STRUCTURED EXTRACTION', description: 'Separate extraction passes build a candidate profile and a job specification. A 38-category ontology brings aliases onto the same vocabulary.', facts: [['Experience integrity', 'Only paid work counts. Hobby projects and hackathons do not increase tenure.'], ['Ambiguity flag', 'Current students or candidates with less than one year of tenure are marked for ambiguity.'], ['Requirement hygiene', 'Required skills and preferred skills are separated, then deduplicated.']] },
  { short: 'Retrieve', title: 'Normalize the role, not the company’s job-title language.', module: 'src/jd_normalizer.py', operation: 'ROLE NORMALIZATION / FAISS RAG', description: 'The full job description is embedded and compared with canonical industry templates. Retrieval supplies a standard role and its expected skill baseline.', facts: [['Embedding model', 'SentenceTransformers · all-MiniLM-L6-v2'], ['Search index', 'FAISS Flat Inner-Product index over canonical JD templates.'], ['Role baseline', 'Web/backend roles additionally require HTML, CSS and JavaScript in the supplied architecture.']] },
  { short: 'Align', title: 'Exact matches first. Semantic proximity second.', module: 'src/skill_ontology.py', operation: 'TWO-TIER SKILL ALIGNMENT', description: 'Canonical names and aliases match directly. Remaining skill pairs are compared as vectors; cosine similarity of at least 0.75 is the semantic acceptance boundary.', facts: [['Tier 1 / deterministic', 'Exact and alias matches carry similarity 1.00.'], ['Tier 2 / semantic', 'cos(θ) = (a · b) / (‖a‖ ‖b‖) · accept ≥ 0.75'], ['Separate measures', 'A 100% must-have match rate is not a 100-point candidate score. Evidence and fit are checked next.']] },
  { short: 'Verify', title: 'Every claimed requirement needs a sentence of evidence.', module: 'src/scorer.py', operation: 'PASS 2 / EVIDENCE & CALIBRATION', description: 'The second pass cites exact sentences from the resume. Unsupported requirements stay unmet. Borderline scores trigger repeated scoring rather than false certainty.', facts: [['Verbatim grounding', 'No explicit sentence → met: false · evidence: null'], ['Borderline interval', 'Initial score 45–70 inclusive → 3 calibration runs. Outside this interval → HIGH confidence.'], ['Confidence rule', 'Spread = max(scores) − min(scores). Spread > 12 points → LOW; otherwise HIGH.']] },
  { short: 'Decide', title: 'Confidence changes the decision, not just the label.', module: 'src/decision.py', operation: 'ORGANIZATIONAL POLICY', description: 'The supplied detailed policy separates strong, substantiated matches from cases needing a recruiter. Ambiguous high scores are escalated, not automatically advanced.', facts: [['ADVANCE', 'Score ≥ 65 AND HIGH confidence.'], ['ESCALATE', 'Score 40–64, or score ≥ 65 with LOW confidence.'], ['REJECT', 'Score < 40 in the detailed policy. Borderline candidates go to human review.']] },
  { short: 'Audit', title: 'Change demographic proxies. Keep qualifications fixed.', module: 'src/fairness.py', operation: 'COUNTERFACTUAL FAIRNESS AUDIT', description: 'Three controlled variants re-enter extraction and scoring. Their scores are compared with the original to detect sensitivity to demographic proxy changes.', facts: [['Controlled perturbations', 'Name swap · college swap · gender-neutral pronouns'], ['Tolerance boundary', '|variant score − original score| ≤ 5 points for every variant.'], ['Measured, not guaranteed', 'A pass means no disparity detected in these three tests; it does not establish universal absence of bias.']] },
  { short: 'Rank', title: 'A ranked result with the reasoning still attached.', module: 'pipeline.py', operation: 'BATCH RANKING & STRUCTURED EXPORT', description: 'Each candidate follows the same sequence. Results are sorted by score, while confidence, recommendation, evidence and critical gaps remain in the exported record.', facts: [['Same evaluation path', 'Ingestion → extraction → retrieval → alignment → evidence → policy → audit'], ['Rank does not override policy', 'Recruiters retain the ESCALATE recommendation and missing requirements.'], ['Machine-readable output', 'Rich terminal table + data/golden_eval/pipeline_output.json']] },
] as const;

function Lines({ children }: { children: React.ReactNode }) { return <div className="engine-lines">{children}</div>; }
function Line({ label, children, tone }: { label: string; children: React.ReactNode; tone?: 'success' | 'warning' | 'danger' }) { return <div className={`engine-line ${tone ? `engine-${tone}` : ''}`}><span>{label}</span><strong>{children}</strong></div>; }
function Tag({ children }: { children: React.ReactNode }) { return <span className="engine-tag">{children}</span>; }

function Input({ stage }: { stage: number }) {
  switch (stage) {
    case 0: return <><div className="engine-file"><FileJson/><span>candidate_jane_doe.pdf<small>RESUME / RAW TEXT</small></span></div><div className="engine-document"><p>Jane Doe</p><p>Email: <span className="engine-redact">jane.doe@example.com</span></p><p>Phone: <span className="engine-redact">+91 98765 43210</span></p><p>Senior Backend Engineer</p><p>5 years · Python · PostgreSQL</p></div><div className="engine-file"><FileJson/><span>senior_ai_engineer.docx<small>JOB DESCRIPTION / SEPARATE PATH</small></span></div></>;
    case 1: return <><span className="engine-caption">CLEANED RESUME + JD</span><div className="engine-document"><p>“Lead AI Engineer · 3 years”</p><p>“Backend Developer · 2 years”</p><p>“Python, Docker, postgres, k8s”</p><p>“AWS Certified Solutions Architect”</p></div><div className="engine-alias"><span>postgres</span><ArrowRight/><strong>postgresql</strong></div><div className="engine-alias"><span>k8s</span><ArrowRight/><strong>kubernetes</strong></div><div className="engine-alias"><span>PHP and MySQL</span><ArrowRight/><strong>php · mysql</strong></div></>;
    case 2: return <><span className="engine-caption">COMPANY TITLE</span><blockquote className="engine-quote">“Prompt Wizard &amp; Backend Alchemist”</blockquote><div className="engine-document"><p>Build high-throughput LLM pipelines.</p><p>Optimize vector search.</p><p>Python · PyTorch · Transformers</p></div><span className="engine-caption">FULL JD → SENTENCE EMBEDDING</span><div className="engine-vector" aria-hidden="true">▂ ▆ ▃ █ ▂ ▅ ▇ ▃ ▂ ▆ ▄ ▇ ▃ ▅ ▂ ▆</div></>;
    case 3: return <><span className="engine-caption">CANDIDATE / CANONICAL SKILLS</span><div className="engine-tags">{['python', 'pytorch', 'fastapi', 'docker', 'postgresql', 'langchain', 'faiss'].map(s => <Tag key={s}>{s}</Tag>)}</div><span className="engine-caption">JD / MUST-HAVES</span><div className="engine-tags">{['python', 'langchain', 'docker', 'faiss'].map(s => <Tag key={s}>{s}</Tag>)}</div><div className="engine-document"><p>Preferred, not required:</p><p>fastapi · kubernetes · postgresql</p></div></>;
    case 4: return <><span className="engine-caption">RESUME / VERBATIM EVIDENCE</span><blockquote className="engine-evidence">“Designed microservices in <mark>Python, Docker, PostgreSQL.</mark>”</blockquote><blockquote className="engine-evidence">“Built LLM inference pipelines, RAG systems, and <mark>Faiss vector search indices.</mark>”</blockquote><Lines><Line label="Paid experience">5 years / 4 required</Line><Line label="Education">B.Tech · Computer Science</Line></Lines></>;
    case 5: return <><span className="engine-caption">EVIDENCE-BASED RESULT</span><div className="engine-big-score">85<span>/100</span></div><Lines><Line label="Confidence" tone="success">HIGH</Line><Line label="Must-haves">4 / 4 matched</Line><Line label="Experience">5 years ≥ 4 required</Line><Line label="Critical gaps">None</Line></Lines><p className="engine-small">Illustrative result from the supplied architecture.</p></>;
    case 6: return <><span className="engine-caption">CONTROLLED VARIANTS</span><Lines><Line label="01 / Name">Jane → James</Line><Line label="02 / College">Pune University → IIT Delhi</Line><Line label="03 / Pronouns">she / her → they / their</Line></Lines><div className="engine-invariant"><ShieldCheck/><span>Skills and qualifications unchanged<small>Each variant runs Pass 1 + Pass 2 again.</small></span></div></>;
    default: return <><span className="engine-caption">ONE RECORD PER CANDIDATE</span><Lines><Line label="Jane / PDF" tone="success">85 · HIGH · ADVANCE</Line><Line label="Alex / DOCX" tone="warning">58 · HIGH · ESCALATE</Line><Line label="Junior / TXT" tone="danger">25 · HIGH · REJECT</Line></Lines><div className="engine-document"><p>Retained fields</p><p>score · confidence · evidence</p><p>decision_reason · critical_gaps</p><p>fairness_audit · explanation</p></div></>;
  }
}

function Output({ stage }: { stage: number }) {
  switch (stage) {
    case 0: return <><span className="engine-caption">CLEANED / MASKED TEXT</span><div className="engine-document engine-output-document"><p>Jane Doe</p><p>Email: <mark>[EMAIL]</mark></p><p>Phone: <mark>[PHONE]</mark></p><p>Senior Backend Engineer</p><p>5 years · Python · PostgreSQL</p></div><Lines><Line label="Contact fields masked" tone="success">2</Line><Line label="Next boundary">Pass 1 extraction</Line></Lines></>;
    case 1: return <><span className="engine-caption">STRUCTURED PROFILE</span><pre className="engine-code">{'{\n  "years_experience": 5,\n  "experience_ambiguity": false,\n  "skills": ["python", "docker",\n    "postgresql", "kubernetes"],\n  "certification_skill": "aws"\n}'}</pre><Lines><Line label="Must-have triggers">required / strong knowledge</Line><Line label="Preferred triggers">plus / bonus / familiarity</Line></Lines></>;
    case 2: return <><span className="engine-caption">CANONICAL TEMPLATE / TOP HIT</span><h4 className="engine-result-title">AI / Machine Learning Engineer</h4><Lines><Line label="Cosine similarity" tone="success">0.87</Line><Line label="Template source">jd_templates.json</Line></Lines><span className="engine-caption">STANDARD MUST-HAVES</span><div className="engine-tags">{['python', 'machine learning', 'pytorch', 'transformers'].map(s => <Tag key={s}>{s}</Tag>)}</div><p className="engine-small">Canonical role example; company-specific requirements remain a separate signal.</p></>;
    case 3: return <><span className="engine-caption">REQUIRED ALIGNMENT / EXACT MATCHES</span><Lines>{['python', 'langchain', 'docker', 'faiss'].map(s => <Line key={s} label={s} tone="success">1.00 <Check size={13}/></Line>)}</Lines><div className="engine-rate"><strong>4 / 4</strong><span>100% must-have match<small>Critical gaps: none</small></span></div><div className="engine-semantic-example"><span>SEMANTIC PATH / SEPARATE EXAMPLE</span><p>fastapi ↔ rest api</p><small>Match only when cosine similarity ≥ 0.75.</small></div></>;
    case 4: return <><span className="engine-caption">MAIN EXAMPLE / CLEAR-CUT</span><Lines><Line label="Candidate score">85 / 100</Line><Line label="Outside 45–70" tone="success">Single pass · HIGH</Line></Lines><div className="engine-calibration"><span className="engine-caption">ALTERNATE BORDERLINE EXAMPLE</span><div className="engine-runs"><span>Run 1<strong>68</strong></span><span>Run 2<strong>71</strong></span><span>Run 3<strong>66</strong></span></div><p>Spread = 71 − 66 = <strong>5 points</strong></p><p className="engine-success">5 ≤ 12 → HIGH confidence</p><small>A spread above 12 routes to LOW confidence.</small></div></>;
    case 5: return <><span className="engine-caption">POLICY OUTPUT / MAIN EXAMPLE</span><div className="engine-verdict engine-success"><Check/>ADVANCE</div><p className="engine-decision-reason">Score 85 ≥ 65, with HIGH confidence. Required skills and relevant experience are substantiated.</p><div className="engine-policy-branch"><span className="engine-caption">ALTERNATE / HUMAN REVIEW</span><p><strong>68 + LOW</strong><ArrowRight/><span className="engine-warning">ESCALATE</span></p><small>High score does not bypass uncertain evidence.</small></div><div className="engine-invariant"><ShieldCheck/><span>When in doubt, escalate.<small>Never hard-reject a borderline case.</small></span></div></>;
    case 6: return <><span className="engine-caption">ORIGINAL SCORE 85 / TOLERANCE ≤ 5</span><Lines><Line label="Name / 85 → 85" tone="success">Δ 0 · PASS</Line><Line label="College / 85 → 86" tone="success">Δ 1 · PASS</Line><Line label="Pronouns / 85 → 85" tone="success">Δ 0 · PASS</Line></Lines><div className="engine-verdict engine-success"><ShieldCheck/>AUDIT PASSED</div><p className="engine-small">Maximum delta: 1 point. Any variant above 5 points flags potential demographic disparity for review.</p></>;
    default: return <><span className="engine-caption">DESCENDING SCORE / RANKED OUTPUT</span><div className="engine-ranking"><div><span>01</span><strong>Jane Doe</strong><b className="engine-success">85</b></div><div><span>02</span><strong>Alex K.</strong><b className="engine-warning">58</b></div><div><span>03</span><strong>Junior Dev</strong><b className="engine-danger">25</b></div></div><pre className="engine-code">{'{\n  "score": 85,\n  "confidence": "HIGH",\n  "recommendation": "ADVANCE",\n  "critical_gaps": [],\n  "fairness_max_delta": 1\n}'}</pre></>;
  }
}

function ProcessGraphic({ stage }: { stage: number }) {
  const labels = ['MASK PII', 'PASS 1', 'FAISS', 'COSINE', 'PASS 2', 'POLICY', 'Δ CHECK', 'EXPORT'];
  return <div className="engine-process" aria-hidden="true"><svg viewBox="0 0 240 240" fill="none">
    <path className="engine-route" d="M0 120h48 M192 120h48"/><path className="engine-travel" d="M0 120h48 M192 120h48"/>
    <circle className="engine-orbit" cx="120" cy="120" r="72"/><circle className="engine-orbit-inner" cx="120" cy="120" r="56"/>
    <path className="engine-scan" d="M120 48a72 72 0 0 1 72 72"/>
    {stage === 0 && <g className="engine-glyph"><path d="M120 82l25 10v22c0 20-25 34-25 34s-25-14-25-34V92z M110 113l8 8 15-18"/></g>}
    {stage === 1 && <g className="engine-glyph"><path d="M105 91H94v58h11 M135 91h11v58h-11 M113 105h16 M113 120h16 M113 135h16"/></g>}
    {stage === 2 && <g className="engine-glyph"><path d="M95 104l25-14 25 14-25 14z M95 104v31l25 15 25-15v-31 M120 118v32 M95 119l25 15 25-15"/></g>}
    {stage === 3 && <g className="engine-glyph"><path d="M93 104h54 M93 120h54 M93 136h54"/>{[104,120,136].map(y=><g key={y}><circle cx="93" cy={y} r="4"/><circle cx="147" cy={y} r="4"/></g>)}</g>}
    {stage === 4 && <g className="engine-glyph"><path d="M100 87h29l12 12v52h-41z M129 87v12h12 M111 115h19 M111 127h19 M111 139h12"/></g>}
    {stage === 5 && <g className="engine-glyph"><path d="M120 87v23 M120 110H98v30 M120 110h22v30"/><circle cx="120" cy="84" r="4"/><circle cx="98" cy="144" r="4"/><circle cx="142" cy="144" r="4"/></g>}
    {stage === 6 && <g className="engine-glyph"><path d="M105 94l-14 48h29z M129 101h20 M129 120h20 M129 139h20"/></g>}
    {stage === 7 && <g className="engine-glyph"><path d="M94 143V99 M94 143h53 M107 134v-12 M122 134v-24 M137 134V91"/></g>}
    <circle className="engine-node" cx="48" cy="120" r="3"/><circle className="engine-node" cx="192" cy="120" r="3"/>
  </svg><span>{labels[stage]}</span><small>{['regex → clean text', 'entities → canonical JSON', 'embed → nearest template', 'exact → vector fallback', 'cite → calibrate', 'score + confidence', 'perturb → compare', 'sort → serialize'][stage]}</small></div>;
}

export function ScoringWalkthrough() {
  const [stage, setStage] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [visible, setVisible] = useState(false);
  const [reduced, setReduced] = useState(false);
  const section = useRef<HTMLElement>(null);
  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => { setReduced(media.matches); if (media.matches) setPlaying(false); };
    update(); media.addEventListener('change', update);
    const observer = new IntersectionObserver(([entry]) => setVisible(entry?.isIntersecting ?? false), { threshold: .15 });
    if (section.current) observer.observe(section.current);
    return () => { media.removeEventListener('change', update); observer.disconnect(); };
  }, []);
  useEffect(() => {
    if (!playing || !visible || reduced) return;
    const timer = window.setTimeout(() => setStage(current => (current + 1) % stages.length), 9000);
    return () => window.clearTimeout(timer);
  }, [stage, playing, visible, reduced]);
  const select = (index: number) => { setStage(index); setPlaying(false); };
  const current = stages[stage];
  if (!current) return null;
  return <section ref={section} className="section scoring-section" id="how-it-works" aria-labelledby="scoring-heading">
    <div className="container">
      <div className="engine-heading"><div><div className="eyebrow">INSIDE THE SCREENING ENGINE</div><h2 id="scoring-heading">How the score is calculated</h2><p>From raw documents to a decision you can trace.</p></div><span className="engine-demo-label">ARCHITECTURE DEMONSTRATION</span></div>
      <nav className="engine-stages" aria-label="Screening stages">{stages.map((item, index) => <Button key={item.short} variant="ghost" className={`engine-stage ${stage === index ? 'is-active' : ''}`} aria-current={stage === index ? 'step' : undefined} aria-label={`Stage ${index + 1}: ${item.short}`} onClick={() => select(index)}><span>{String(index + 1).padStart(2, '0')}</span><strong>{item.short}</strong><span className="engine-stage-line"/></Button>)}</nav>
      <div className="engine-toolbar"><span><span className={`engine-status-dot ${playing && !reduced ? 'is-running' : ''}`}/>{String(stage + 1).padStart(2, '0')} / 08 <span className="engine-operation">{current.operation}</span></span><div>
        <Button variant="ghost" size="icon" title="Previous stage" aria-label="Previous stage" onClick={() => select((stage + 7) % 8)}><ArrowLeft/></Button>
        <Button variant="ghost" size="icon" title={playing ? 'Pause walkthrough' : 'Play walkthrough'} aria-label={playing ? 'Pause walkthrough' : 'Play walkthrough'} disabled={reduced} onClick={() => setPlaying(!playing)}>{playing ? <Pause/> : <Play/>}</Button>
        <Button variant="ghost" size="icon" title="Replay walkthrough" aria-label="Replay walkthrough" onClick={() => { setStage(0); setPlaying(!reduced); }}><RotateCcw/></Button>
        <Button variant="ghost" size="icon" title="Next stage" aria-label="Next stage" onClick={() => select((stage + 1) % 8)}><ArrowRight/></Button>
      </div></div>
      <div className={`engine-workspace ${playing && visible && !reduced ? 'is-playing' : 'is-paused'}`}>
        <div className="engine-stage-heading" aria-live={playing ? 'off' : 'polite'}><h3>{current.title}</h3><p>{current.description}</p><code>{current.module}</code></div>
        <div key={stage} className="engine-flow"><div className="engine-input"><div className="engine-panel-label">01 / INPUT SIGNAL</div><Input stage={stage}/></div><ProcessGraphic stage={stage}/><div className="engine-output"><div className="engine-panel-label">02 / VERIFIED OUTPUT</div><Output stage={stage}/></div></div>
        <div className="engine-facts">{current.facts.map(([label, detail]) => <div key={label}><span>{label}</span><p>{detail}</p></div>)}</div>
        <div className="engine-playback" key={`progress-${stage}`} aria-hidden="true"><div/></div>
      </div>
      <div className="engine-footer"><span><ShieldCheck/>EVIDENCE · CONFIDENCE · HUMAN REVIEW · AUDIT TRAIL</span><p>Illustrates the supplied engine design with sample data. This website preview uses local keyword matching; the LLM, vector retrieval and audit services are not connected.</p></div>
    </div>
  </section>;
}