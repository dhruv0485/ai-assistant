export type ScreeningEvidence = {
  skill: string;
  evidence: string | null;
  met: boolean;
};

export type FairnessAuditData = {
  orig_score: number;
  max_delta: number;
  bias_detected: boolean;
  audit_passed?: boolean;
  variants?: Array<{
    type: string;
    description: string;
    score: number;
    delta: number;
  }>;
};

export type ScreeningResult = {
  score: number;
  confidence: 'HIGH' | 'LOW';
  decision: 'ADVANCE' | 'ESCALATE' | 'REJECT';
  decision_reason: string;
  critical_gaps: string[];
  must_have_met?: ScreeningEvidence[];
  nice_to_have_met?: ScreeningEvidence[];
  experience_fit?: {
    required_years: number | null;
    candidate_years: number | null;
    note: string;
  };
  education_fit?: 'strong' | 'adequate' | 'weak' | 'unknown';
  gaps?: string[];
  strengths?: string[];
  overall_explanation?: string;
  fairness_audit?: FairnessAuditData;
};

export type Job = {
  id: string;
  title: string;
  department: string;
  location: string;
  type: string;
  experience: string;
  posted: string;
  applications: number;
  shortlisted: number;
  rejected: number;
  status: 'Active' | 'Closed' | 'Draft';
  summary: string;
  skills: string[];
  must_have_skills?: string[];
  nice_to_have_skills?: string[];
  salary_min?: number;
  salary_max?: number;
};

export const initialJobs: Job[] = [
  {
    id: 'frontend-developer',
    title: 'Frontend Developer',
    department: 'Engineering',
    location: 'Bengaluru',
    type: 'Full-time',
    experience: '1–3 years',
    posted: '12 Oct 2026',
    applications: 428,
    shortlisted: 86,
    rejected: 294,
    status: 'Active',
    summary: 'Build thoughtful, accessible web experiences with React and TypeScript. Work closely with our design and engineering teams to bring useful products to life.',
    skills: ['React', 'TypeScript', 'JavaScript', 'HTML', 'CSS', 'Git', 'REST API', 'Accessibility'],
    must_have_skills: ['React', 'TypeScript', 'JavaScript', 'HTML', 'CSS', 'Git'],
    nice_to_have_skills: ['REST API', 'Accessibility']
  },
  {
    id: 'backend-developer',
    title: 'Backend Developer',
    department: 'Engineering',
    location: 'Hyderabad',
    type: 'Full-time',
    experience: '2–4 years',
    posted: '10 Oct 2026',
    applications: 356,
    shortlisted: 62,
    rejected: 249,
    status: 'Active',
    summary: 'Design reliable services and APIs that power our products. Bring your experience with Node.js, databases, and practical problem solving.',
    skills: ['Node.js', 'JavaScript', 'SQL', 'PostgreSQL', 'REST API', 'Git', 'Docker'],
    must_have_skills: ['Node.js', 'PostgreSQL', 'REST API', 'Git'],
    nice_to_have_skills: ['Docker', 'SQL']
  },
  {
    id: 'product-designer',
    title: 'Product Designer',
    department: 'Design',
    location: 'Remote',
    type: 'Full-time',
    experience: '1–3 years',
    posted: '08 Oct 2026',
    applications: 312,
    shortlisted: 43,
    rejected: 218,
    status: 'Active',
    summary: 'Turn complex problems into clear, useful interfaces. Partner with researchers and engineers from early ideas through carefully considered details.',
    skills: ['Figma', 'User Research', 'Prototyping', 'Accessibility', 'Design Systems'],
    must_have_skills: ['Figma', 'Prototyping', 'Design Systems'],
    nice_to_have_skills: ['User Research', 'Accessibility']
  },
  {
    id: 'data-analyst',
    title: 'Data Analyst',
    department: 'Analytics',
    location: 'Pune',
    type: 'Full-time',
    experience: '0–2 years',
    posted: '06 Oct 2026',
    applications: 188,
    shortlisted: 22,
    rejected: 110,
    status: 'Active',
    summary: 'Help teams make better decisions through data. Explore datasets, build dashboards, and communicate findings with clarity.',
    skills: ['Python', 'SQL', 'Excel', 'Tableau', 'Statistics'],
    must_have_skills: ['Python', 'SQL'],
    nice_to_have_skills: ['Excel', 'Tableau', 'Statistics']
  },
];

export const applicants = [
  {
    id: 'aarav',
    name: 'Aarav Sharma',
    email: 'aarav@example.com',
    score: 82,
    date: '14 Oct 2026',
    status: 'Shortlisted',
    skills: ['React', 'TypeScript', 'JavaScript', 'HTML', 'CSS', 'Git'],
    confidence: 'HIGH' as const,
    decision: 'ADVANCE' as const,
    decision_reason: 'Strong match (score 82). Substantial React and TypeScript experience.',
    must_have_met: [
      { skill: 'React', evidence: 'Built frontend architecture in React and Next.js', met: true },
      { skill: 'TypeScript', evidence: 'Migrated JavaScript codebase to TypeScript with strict type checking', met: true },
      { skill: 'Git', evidence: 'Managed team git branching strategy and CI/CD pipelines', met: true }
    ],
    experience_fit: { required_years: 2, candidate_years: 3, note: 'Meets tenure requirement' },
    education_fit: 'strong' as const,
    fairness_audit: { orig_score: 82, max_delta: 0, bias_detected: false, audit_passed: true }
  },
  {
    id: 'ananya',
    name: 'Ananya Patel',
    email: 'ananya@example.com',
    score: 72,
    date: '13 Oct 2026',
    status: 'Shortlisted',
    skills: ['React', 'JavaScript', 'HTML', 'CSS', 'Git'],
    confidence: 'HIGH' as const,
    decision: 'ADVANCE' as const,
    decision_reason: 'Meets core requirements with proven production delivery.',
    must_have_met: [
      { skill: 'React', evidence: 'Developed component libraries using React and Tailwind', met: true },
      { skill: 'JavaScript', evidence: 'Engineered high-performance ES6+ single page apps', met: true }
    ],
    experience_fit: { required_years: 2, candidate_years: 2.5, note: 'Meets requirement' },
    education_fit: 'adequate' as const,
    fairness_audit: { orig_score: 72, max_delta: 1, bias_detected: false, audit_passed: true }
  },
  {
    id: 'rohan',
    name: 'Rohan Mehta',
    email: 'rohan@example.com',
    score: 48,
    date: '13 Oct 2026',
    status: 'Escalated to Recruiter',
    skills: ['JavaScript', 'HTML', 'CSS'],
    confidence: 'HIGH' as const,
    decision: 'ESCALATE' as const,
    decision_reason: 'Partial match (score 48). Missing TypeScript and production state management. Recruiter review recommended.',
    critical_gaps: ['TypeScript', 'Git workflows'],
    must_have_met: [
      { skill: 'JavaScript', evidence: 'Implemented interactive DOM widgets in pure JavaScript', met: true },
      { skill: 'TypeScript', evidence: null, met: false }
    ],
    experience_fit: { required_years: 2, candidate_years: 1, note: 'Under minimum tenure requirement' },
    education_fit: 'adequate' as const,
    fairness_audit: { orig_score: 48, max_delta: 2, bias_detected: false, audit_passed: true }
  },
  {
    id: 'isha',
    name: 'Isha Nair',
    email: 'isha@example.com',
    score: 91,
    date: '12 Oct 2026',
    status: 'Referred',
    skills: ['React', 'TypeScript', 'JavaScript', 'HTML', 'CSS', 'Git', 'REST API'],
    confidence: 'HIGH' as const,
    decision: 'ADVANCE' as const,
    decision_reason: 'Exceptional profile with verified full-stack architecture background.',
    must_have_met: [
      { skill: 'React', evidence: 'Architected micro-frontends serving 500k monthly active users', met: true },
      { skill: 'TypeScript', evidence: 'Designed enterprise types and SDK wrappers', met: true },
      { skill: 'REST API', evidence: 'Integrated GraphQL and RESTful microservice APIs', met: true }
    ],
    experience_fit: { required_years: 2, candidate_years: 4, note: 'Exceeds experience requirements' },
    education_fit: 'strong' as const,
    fairness_audit: { orig_score: 91, max_delta: 0, bias_detected: false, audit_passed: true }
  },
  {
    id: 'kabir',
    name: 'Kabir Singh',
    email: 'kabir@example.com',
    score: 26,
    date: '12 Oct 2026',
    status: 'Rejected',
    skills: ['HTML', 'CSS'],
    confidence: 'HIGH' as const,
    decision: 'REJECT' as const,
    decision_reason: 'Weak match (score 26). Missing core requirements: React, TypeScript, Git.',
    critical_gaps: ['React', 'TypeScript', 'Git'],
    must_have_met: [
      { skill: 'React', evidence: null, met: false },
      { skill: 'TypeScript', evidence: null, met: false }
    ],
    experience_fit: { required_years: 2, candidate_years: 0, note: 'No professional engineering experience' },
    education_fit: 'weak' as const,
    fairness_audit: { orig_score: 26, max_delta: 0, bias_detected: false, audit_passed: true }
  },
];

export function pageHead(title: string, description: string, image?: string) {
  const full = `${title} | Hunt Your Tribe`;
  return {
    meta: [
      { title: full },
      { name: 'description', content: description },
      { property: 'og:title', content: full },
      { property: 'og:description', content: description },
      { property: 'og:type', content: 'website' },
      { name: 'twitter:card', content: 'summary_large_image' },
      ...(image?.startsWith('https://')
        ? [
            { property: 'og:image', content: image },
            { name: 'twitter:image', content: image },
          ]
        : []),
    ],
  };
}

export const tips = [
  'Keep resume to 1 page if under 3 years experience',
  'Use numbers: “increased sales by 40%” beats “responsible for sales”',
  'Match your job title to the JD title',
  'List skills in a plain column — no skill bars',
  'Name your file: Firstname_Lastname_Resume.pdf',
  'Avoid tables and columns — ATS parsers break',
  'Lead every bullet with an action verb',
  'Tailor the top third of your resume to each JD',
];
