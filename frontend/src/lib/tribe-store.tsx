import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import type { User, Session } from '@supabase/supabase-js';
import { supabase } from './supabase';
import { initialJobs, type Job, type ScreeningEvidence, type FairnessAuditData, type ScreeningResult } from './tribe-data';

export type CandidateProfile = {
  id: string;
  email: string;
  full_name: string;
  phone: string;
  location: string;
  linkedin_url?: string;
  portfolio_url?: string;
  resume_file_path?: string;
  resume_file_name?: string;
  resume_raw_text?: string;
};

export type Application = {
  id: string;
  jobId: string;
  title: string;
  name: string;
  email: string;
  phone: string;
  location: string;
  linkedin?: string;
  portfolio?: string;
  resume: string;
  score: number;
  matched: string[];
  missing: string[];
  date: string;
  status: string;
  file?: File | undefined;
  resume_file_path?: string;
  resume_file_name?: string;
  confidence?: 'HIGH' | 'LOW';
  decision?: 'ADVANCE' | 'ESCALATE' | 'REJECT';
  decision_reason?: string;
  critical_gaps?: string[];
  must_have_met?: ScreeningEvidence[];
  nice_to_have_met?: ScreeningEvidence[];
  experience_fit?: { required_years: number | null; candidate_years: number | null; note: string };
  education_fit?: 'strong' | 'adequate' | 'weak' | 'unknown';
  fairness_audit?: FairnessAuditData;
  screening?: ScreeningResult;
  referral_code?: string;
  is_referral?: boolean;
  step_details?: Record<string, any>;
};

type Store = {
  jobs: Job[];
  setJobs: React.Dispatch<React.SetStateAction<Job[]>>;
  applications: Application[];
  setApplications: React.Dispatch<React.SetStateAction<Application[]>>;
  user: User | null;
  session: Session | null;
  userRole: 'candidate' | 'recruiter' | 'admin';
  candidateProfile: CandidateProfile | null;
  isProfileComplete: boolean;
  showProfileModal: boolean;
  setShowProfileModal: (show: boolean) => void;
  saveCandidateProfile: (profile: Partial<CandidateProfile>) => Promise<boolean>;
  loading: boolean;
  refreshJobs: () => Promise<void>;
  refreshApplications: () => Promise<void>;
  refreshProfile: () => Promise<void>;
  updateJobStatus: (jobId: string, status: 'Active' | 'Closed') => Promise<boolean>;
  deleteJob: (jobId: string) => Promise<boolean>;
  updateJobDetails: (jobId: string, updates: { title?: string; summary?: string }) => Promise<boolean>;
  signOut: () => Promise<void>;
  toast: (message: string) => void;
};

const Context = createContext<Store | null>(null);

export function TribeProvider({ children }: { children: ReactNode }) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [userRole, setUserRole] = useState<'candidate' | 'recruiter' | 'admin'>('candidate');
  const [candidateProfile, setCandidateProfile] = useState<CandidateProfile | null>(null);
  const [showProfileModal, setShowProfileModal] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [message, setMessage] = useState('');

  function toast(text: string) {
    setMessage(text);
    window.setTimeout(() => setMessage(''), 4000);
  }

  // 1. Fetch user profile
  const refreshProfile = async (currentUser?: User | null) => {
    const targetUser = currentUser !== undefined ? currentUser : user;
    if (!targetUser) {
      setCandidateProfile(null);
      return;
    }

    try {
      const { data, error } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', targetUser.id)
        .maybeSingle();

      if (data) {
        setCandidateProfile({
          id: data.id,
          email: data.email,
          full_name: data.full_name || '',
          phone: data.phone || '',
          location: data.location || '',
          linkedin_url: data.linkedin_url || '',
          portfolio_url: data.portfolio_url || '',
          resume_file_path: data.resume_file_path,
          resume_file_name: data.resume_file_name,
          resume_raw_text: data.resume_raw_text,
        });

        // If candidate role and mandatory info is missing, prompt setup
        if (
          targetUser.user_metadata?.role !== 'recruiter' &&
          (!data.full_name || !data.phone || !data.location)
        ) {
          setShowProfileModal(true);
        }
      } else {
        // Create initial row or fallback
        const newProfile: CandidateProfile = {
          id: targetUser.id,
          email: targetUser.email || '',
          full_name: targetUser.user_metadata?.full_name || '',
          phone: '',
          location: '',
        };
        setCandidateProfile(newProfile);
        if (targetUser.user_metadata?.role !== 'recruiter') {
          setShowProfileModal(true);
        }
      }
    } catch (err) {
      console.warn('Profile read notice:', err);
    }
  };

  const saveCandidateProfile = async (updates: Partial<CandidateProfile>): Promise<boolean> => {
    if (!user) return false;

    try {
      const payload = {
        id: user.id,
        email: user.email,
        full_name: updates.full_name,
        phone: updates.phone,
        location: updates.location,
        linkedin_url: updates.linkedin_url,
        portfolio_url: updates.portfolio_url,
        resume_file_path: updates.resume_file_path,
        resume_file_name: updates.resume_file_name,
        resume_raw_text: updates.resume_raw_text,
        role: userRole,
      };

      const { error } = await supabase.from('profiles').upsert(payload);
      if (error) {
        console.warn('Profile upsert notice:', error.message);
      }

      setCandidateProfile((prev) => (prev ? { ...prev, ...updates } : (payload as any)));
      toast('Candidate profile updated successfully!');
      setShowProfileModal(false);
      return true;
    } catch (err) {
      console.error('Failed saving profile:', err);
      toast('Profile updated locally.');
      return false;
    }
  };

  // 2. Auth initialization
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      if (session?.user?.user_metadata?.role) {
        setUserRole(session.user.user_metadata.role);
      }
      if (session?.user) {
        void refreshProfile(session.user);
      }
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);
      if (session?.user?.user_metadata?.role) {
        setUserRole(session.user.user_metadata.role);
      }
      if (session?.user) {
        void refreshProfile(session.user);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  // 3. Fetch Jobs
  const refreshJobs = async () => {
    try {
      const { data, error } = await supabase
        .from('jobs')
        .select('*')
        .order('created_at', { ascending: false });

      if (error) {
        console.warn('Jobs read notice:', error.message);
        return;
      }

      setJobs(() =>
        (data || [])
          .filter(
            (j) =>
              j.department !== 'Benchmark_Template' &&
              j.id !== '26325341-2401-4849-87be-caff96c5626b'
          )
          .map((j) => {
            const count = applications.filter((a) => a.jobId === j.id).length;
            const shortlisted = applications.filter(
              (a) => a.jobId === j.id && (a.status === 'Shortlisted' || a.decision === 'ADVANCE')
            ).length;
            const rejected = applications.filter(
              (a) => a.jobId === j.id && (a.status === 'Rejected' || a.decision === 'REJECT')
            ).length;

          return {
            id: j.id,
            title: j.title,
            department: j.department || 'General',
            location: j.location || 'Remote',
            type: j.employment_type || 'Full-time',
            experience: `${j.min_years_experience || 0}–${j.max_years_experience || 3} years`,
            posted: new Date(j.created_at).toLocaleDateString('en-GB', {
              day: '2-digit',
              month: 'short',
              year: 'numeric',
            }),
            applications: count,
            shortlisted,
            rejected,
            status: j.status || 'Active',
            summary: j.description || '',
            skills: [...(j.must_have_skills || []), ...(j.nice_to_have_skills || [])],
            must_have_skills: j.must_have_skills || [],
            nice_to_have_skills: j.nice_to_have_skills || [],
            salary_min: j.salary_min,
            salary_max: j.salary_max,
          };
        })
      );
    } catch (err) {
      console.warn('Jobs fetch notice:', err);
    }
  };

  // 4. Fetch Applications with screening results & step_details
  const refreshApplications = async () => {
    try {
      const { data, error } = await supabase
        .from('applications')
        .select(`
          id,
          job_id,
          candidate_name,
          candidate_email,
          candidate_phone,
          candidate_location,
          linkedin_url,
          portfolio_url,
          resume_file_path,
          resume_file_name,
          resume_raw_text,
          status,
          referral_code,
          is_referral,
          created_at,
          jobs ( id, title, department, must_have_skills, nice_to_have_skills ),
          screening_results (
            score,
            confidence,
            decision,
            decision_reason,
            critical_gaps,
            must_have_met,
            nice_to_have_met,
            experience_fit,
            education_fit,
            gaps,
            strengths,
            overall_explanation,
            step_details
          ),
          fairness_audits (
            original_score,
            max_delta,
            bias_detected,
            variants_evaluated,
            audit_passed
          )
        `)
        .order('created_at', { ascending: false });

      if (error) {
        console.warn('Applications read notice:', error.message);
        return;
      }

      const mappedApps: Application[] = (data || [])
        .filter(
          (row: any) =>
            row.job_id !== '26325341-2401-4849-87be-caff96c5626b' &&
            row.jobs?.department !== 'Benchmark_Template'
        )
        .map((row: any) => {
        const screening = Array.isArray(row.screening_results)
          ? row.screening_results[0]
          : row.screening_results;
        const fairness = Array.isArray(row.fairness_audits)
          ? row.fairness_audits[0]
          : row.fairness_audits;

        const jobTitle = row.jobs?.title || 'Applied Position';
        const jobSkills = [
          ...(row.jobs?.must_have_skills || []),
          ...(row.jobs?.nice_to_have_skills || []),
        ];

        const mustHaves = screening?.must_have_met || [];
        const matchedSkills = mustHaves.filter((m: any) => m.met).map((m: any) => m.skill);
        const missingSkills =
          screening?.critical_gaps || mustHaves.filter((m: any) => !m.met).map((m: any) => m.skill);

        const isRef =
          row.is_referral ||
          (row.referral_code && row.referral_code.toUpperCase() === 'EMP-001') ||
          row.status === 'Referred';

        return {
          id: row.id,
          jobId: row.job_id,
          title: jobTitle,
          name: row.candidate_name,
          email: row.candidate_email,
          phone: row.candidate_phone || '',
          location: row.candidate_location || '',
          linkedin: row.linkedin_url,
          portfolio: row.portfolio_url,
          resume: row.resume_raw_text || '',
          resume_file_path: row.resume_file_path,
          resume_file_name: row.resume_file_name,
          score: screening ? screening.score : 0,
          confidence: screening?.confidence || 'HIGH',
          decision:
            screening?.decision ||
            (row.status === 'Shortlisted' ? 'ADVANCE' : row.status === 'Rejected' ? 'REJECT' : 'ESCALATE'),
          decision_reason: screening?.decision_reason || '',
          critical_gaps: screening?.critical_gaps || [],
          must_have_met: screening?.must_have_met || [],
          nice_to_have_met: screening?.nice_to_have_met || [],
          experience_fit: screening?.experience_fit,
          education_fit: screening?.education_fit,
          step_details: screening?.step_details,
          fairness_audit: fairness
            ? {
                orig_score: fairness.original_score,
                max_delta: fairness.max_delta,
                bias_detected: fairness.bias_detected,
                audit_passed: fairness.audit_passed,
                variants: fairness.variants_evaluated,
              }
            : undefined,
          matched: matchedSkills.length > 0 ? matchedSkills : jobSkills.slice(0, 3),
          missing: missingSkills,
          date: new Date(row.created_at).toLocaleDateString('en-GB', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
          }),
          status: row.status,
          referral_code: row.referral_code,
          is_referral: isRef,
        };
      });

      setApplications(mappedApps);

      // Update counts on jobs dynamically based on real applications
      setJobs((currentJobs) =>
        currentJobs.map((j) => {
          const count = mappedApps.filter((a) => a.jobId === j.id).length;
          const shortlisted = mappedApps.filter(
            (a) => a.jobId === j.id && (a.status === 'Shortlisted' || a.decision === 'ADVANCE')
          ).length;
          const rejected = mappedApps.filter(
            (a) => a.jobId === j.id && (a.status === 'Rejected' || a.decision === 'REJECT')
          ).length;
          return { ...j, applications: count, shortlisted, rejected };
        })
      );
    } catch (err) {
      console.warn('Applications fetch notice:', err);
    }
  };

  useEffect(() => {
    Promise.all([refreshJobs(), refreshApplications()]).finally(() => {
      setLoading(false);
    });

    const channel = supabase
      .channel('schema-db-changes')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'applications' },
        () => refreshApplications()
      )
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'screening_results' },
        () => refreshApplications()
      )
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'jobs' },
        () => refreshJobs()
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const updateJobStatus = async (jobId: string, newStatus: 'Active' | 'Closed'): Promise<boolean> => {
    // Optimistic local update
    setJobs((prev) =>
      prev.map((j) => (j.id === jobId ? { ...j, status: newStatus } : j))
    );

    try {
      const { error } = await supabase
        .from('jobs')
        .update({ status: newStatus })
        .eq('id', jobId);

      if (error) {
        console.error('Failed to update job status in Supabase:', error.message);
        toast(`Error: ${error.message}`);
        await refreshJobs();
        return false;
      }

      toast(newStatus === 'Closed' ? 'Job closed.' : 'Job reopened as Active.');
      await refreshJobs();
      return true;
    } catch (err: any) {
      console.error('Exception updating job status:', err);
      toast('Failed to update job status.');
      await refreshJobs();
      return false;
    }
  };

  const deleteJob = async (jobId: string): Promise<boolean> => {
    try {
      // 1. Fetch any child applications for this job
      const { data: apps } = await supabase
        .from('applications')
        .select('id')
        .eq('job_id', jobId);

      const appIds = (apps || []).map((a: any) => a.id);

      if (appIds.length > 0) {
        // Cascade delete child relations in case FK does not cascade
        await supabase.from('screening_results').delete().in('application_id', appIds);
        await supabase.from('fairness_audits').delete().in('application_id', appIds);
        await supabase.from('recruiter_actions').delete().in('application_id', appIds);
        await supabase.from('applications').delete().eq('job_id', jobId);
      }

      // 2. Delete the job row itself
      const { error } = await supabase.from('jobs').delete().eq('id', jobId);

      if (error) {
        console.error('Failed to delete job from Supabase:', error.message);
        toast(`Error deleting job: ${error.message}`);
        await refreshJobs();
        return false;
      }

      // 3. Remove from local state
      setJobs((prev) => prev.filter((j) => j.id !== jobId));
      setApplications((prev) => prev.filter((a) => a.jobId !== jobId));
      toast('Job posting deleted.');
      return true;
    } catch (err: any) {
      console.error('Exception deleting job:', err);
      toast('Failed to delete job posting.');
      await refreshJobs();
      return false;
    }
  };

  const updateJobDetails = async (
    jobId: string,
    updates: { title?: string; summary?: string }
  ): Promise<boolean> => {
    setJobs((prev) =>
      prev.map((j) => (j.id === jobId ? { ...j, ...updates } : j))
    );

    try {
      const payload: { title?: string; description?: string } = {};
      if (updates.title !== undefined) payload.title = updates.title;
      if (updates.summary !== undefined) payload.description = updates.summary;

      const { error } = await supabase
        .from('jobs')
        .update(payload)
        .eq('id', jobId);

      if (error) {
        console.error('Failed to update job details in Supabase:', error.message);
        toast(`Error: ${error.message}`);
        await refreshJobs();
        return false;
      }

      toast('Job details updated.');
      await refreshJobs();
      return true;
    } catch (err: any) {
      console.error('Exception updating job details:', err);
      toast('Failed to update job details.');
      await refreshJobs();
      return false;
    }
  };

  const signOut = async () => {
    await supabase.auth.signOut();
    setUser(null);
    setSession(null);
    setCandidateProfile(null);
    setUserRole('candidate');
    toast('Signed out successfully.');
  };

  const isProfileComplete = Boolean(
    candidateProfile?.full_name && candidateProfile?.phone
  );

  return (
    <Context.Provider
      value={{
        jobs,
        setJobs,
        applications,
        setApplications,
        user,
        session,
        userRole,
        candidateProfile,
        isProfileComplete,
        showProfileModal,
        setShowProfileModal,
        saveCandidateProfile,
        loading,
        refreshJobs,
        refreshApplications,
        refreshProfile,
        updateJobStatus,
        deleteJob,
        updateJobDetails,
        signOut,
        toast,
      }}
    >
      {children}
      {message && (
        <div role="status" className="toast-bar">
          {message}
        </div>
      )}
    </Context.Provider>
  );
}

export function useTribe() {
  const store = useContext(Context);
  if (!store) throw new Error('TribeProvider is required');
  return store;
}
