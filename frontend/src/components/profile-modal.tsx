import { useState, useEffect } from 'react';
import { User, Phone, MapPin, Globe, Linkedin, Check, Sparkles, FileText } from 'lucide-react';
import { Modal, Field, UploadZone } from '@/components/tribe-ui';
import { Button } from '@/components/ui/button';
import { useTribe } from '@/lib/tribe-store';
import { supabase } from '@/lib/supabase';

export function ProfileModal() {
  const {
    showProfileModal,
    setShowProfileModal,
    candidateProfile,
    saveCandidateProfile,
    user,
    userRole,
  } = useTribe();

  // Only show for candidate accounts
  if (!showProfileModal || userRole === 'recruiter') return null;

  const [fullName, setFullName] = useState(candidateProfile?.full_name || '');
  const [phone, setPhone] = useState(candidateProfile?.phone || '');
  const [location, setLocation] = useState(candidateProfile?.location || 'Bengaluru');
  const [linkedin, setLinkedin] = useState(candidateProfile?.linkedin_url || '');
  const [portfolio, setPortfolio] = useState(candidateProfile?.portfolio_url || '');
  const [resumeText, setResumeText] = useState(candidateProfile?.resume_raw_text || '');
  const [resumeFile, setResumeFile] = useState<File>();
  const [resumeFileName, setResumeFileName] = useState(candidateProfile?.resume_file_name || '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (candidateProfile) {
      if (candidateProfile.full_name) setFullName(candidateProfile.full_name);
      if (candidateProfile.phone) setPhone(candidateProfile.phone);
      if (candidateProfile.location) setLocation(candidateProfile.location);
      if (candidateProfile.linkedin_url) setLinkedin(candidateProfile.linkedin_url);
      if (candidateProfile.portfolio_url) setPortfolio(candidateProfile.portfolio_url);
      if (candidateProfile.resume_file_name) setResumeFileName(candidateProfile.resume_file_name);
      if (candidateProfile.resume_raw_text) setResumeText(candidateProfile.resume_raw_text);
    }
  }, [candidateProfile]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!fullName.trim() || !phone.trim() || !location.trim()) {
      setError('Please provide your full name, phone number, and current location to proceed.');
      return;
    }

    setBusy(true);
    setError('');

    let filePath = candidateProfile?.resume_file_path;

    try {
      if (resumeFile && user) {
        const cleanName = resumeFile.name.replace(/[^a-zA-Z0-9.-]/g, '_');
        filePath = `profiles/${user.id}/${Date.now()}_${cleanName}`;
        await supabase.storage.from('resumes').upload(filePath, resumeFile, {
          upsert: true,
        });
      }

      await saveCandidateProfile({
        full_name: fullName.trim(),
        phone: phone.trim(),
        location: location.trim(),
        linkedin_url: linkedin.trim(),
        portfolio_url: portfolio.trim(),
        resume_file_path: filePath,
        resume_file_name: resumeFile ? resumeFile.name : resumeFileName,
        resume_raw_text: resumeText,
      });

      setShowProfileModal(false);
    } catch (err: any) {
      setError(err?.message || 'Failed saving candidate profile.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      title="Complete Your Candidate Profile"
      wide
      preventClose={true}
    >
      <div className="space-y-4">
        <p className="text-xs text-muted-foreground leading-relaxed">
          Please complete your candidate profile to continue. All details and your resume will be
          automatically pre-filled whenever you apply for open positions.
        </p>

        <form onSubmit={handleSave} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Field label="Full Name">
              <input
                required
                placeholder="Jane Doe"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </Field>
            <Field label="Phone Number">
              <input
                required
                type="tel"
                placeholder="+91 98765 43210"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
            </Field>
            <Field label="Current Location">
              <input
                required
                placeholder="City, State"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
              />
            </Field>
            <Field label="LinkedIn Profile (optional)">
              <input
                type="url"
                placeholder="https://linkedin.com/in/username"
                value={linkedin}
                onChange={(e) => setLinkedin(e.target.value)}
              />
            </Field>
            <Field label="Portfolio / GitHub (optional)" wide>
              <input
                type="url"
                placeholder="https://github.com/username or portfolio"
                value={portfolio}
                onChange={(e) => setPortfolio(e.target.value)}
              />
            </Field>
          </div>

          <div className="pt-2">
            <h4 className="text-xs font-mono uppercase text-muted-foreground mb-2 flex items-center gap-1.5">
              <FileText size={14} className="text-primary" />
              Default Resume (PDF or DOCX)
            </h4>
            <UploadZone
              label={
                resumeFileName
                  ? `Uploaded: ${resumeFileName} (Drop another to replace)`
                  : 'Upload your default resume for 1-click apply'
              }
              onParsed={(text, file) => {
                setResumeText(text);
                setResumeFile(file);
                setResumeFileName(file.name);
              }}
            />
            {resumeFileName && (
              <small className="text-emerald-400 text-[11px] block mt-1">
                ✔ Default resume attached: {resumeFileName}
              </small>
            )}
          </div>

          {error && <p className="text-xs text-rose-400 mt-2">{error}</p>}

          <div className="flex justify-end gap-3 pt-4 border-t border-border">
            <Button type="submit" disabled={busy} className="w-full sm:w-auto px-6">
              {busy ? 'Saving Profile…' : 'Save & Continue'}
            </Button>
          </div>
        </form>
      </div>
    </Modal>
  );
}
