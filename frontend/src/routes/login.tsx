import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { ArrowLeft, Eye, EyeOff, Clock, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Field } from '@/components/tribe-ui';
import { pageHead } from '@/lib/tribe-data';
import { photos } from '@/lib/photos';
import { supabase } from '@/lib/supabase';
import { useTribe } from '@/lib/tribe-store';

export const Route = createFileRoute('/login')({
  validateSearch: (s: Record<string, unknown>): { role?: string } =>
    s['role'] === 'hr' ? { role: 'hr' } : {},
  head: () =>
    pageHead(
      'Sign In',
      'Sign in as a candidate or a verified HR member for the Hunt Your Tribe placement drive.',
      photos[8]
    ),
  component: Login,
});

function Login() {
  const { role } = Route.useSearch();
  const navigate = useNavigate();
  const { toast } = useTribe();

  const [hr, setHr] = useState(role === 'hr');
  const [show, setShow] = useState(false);
  const [mode, setMode] = useState<'signin' | 'signup' | 'forgot' | 'otp'>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [otpToken, setOtpToken] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setNotice('');
    setBusy(true);

    try {
      if (mode === 'signin') {
        const { data, error: signInErr } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password,
        });

        if (signInErr) throw signInErr;

        toast('Signed in successfully.');
        const userRole = data.user?.user_metadata?.role || (hr ? 'recruiter' : 'candidate');

        if (userRole === 'recruiter' || hr) {
          navigate({ to: '/hr', search: { view: 'overview' } });
        } else {
          navigate({ to: '/openings' });
        }
      } else if (mode === 'signup') {
        const { data, error: signUpErr } = await supabase.auth.signUp({
          email: email.trim(),
          password,
          options: {
            data: {
              role: hr ? 'recruiter' : 'candidate',
              full_name: email.split('@')[0],
            },
          },
        });

        if (signUpErr) throw signUpErr;

        // Auto sign-in immediately with no email verification required
        const { error: autoSignInErr } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password,
        });

        if (autoSignInErr) {
          // Fallback if session already established
          if (!data.session) throw autoSignInErr;
        }

        toast(hr ? 'HR account created & signed in!' : 'Candidate account created & signed in!');
        if (hr) {
          navigate({ to: '/hr', search: { view: 'overview' } });
        } else {
          navigate({ to: '/openings' });
        }
      } else if (mode === 'otp') {
        if (!otpSent) {
          const { error: otpErr } = await supabase.auth.signInWithOtp({
            email: email.trim(),
          });
          if (otpErr) throw otpErr;
          setOtpSent(true);
          setNotice('OTP code sent to your email. Enter it below to complete sign in.');
        } else {
          const { data, error: verifyErr } = await supabase.auth.verifyOtp({
            email: email.trim(),
            token: otpToken.trim(),
            type: 'email',
          });
          if (verifyErr) throw verifyErr;
          toast('OTP verified. Signed in.');
          if (hr) {
            navigate({ to: '/hr', search: { view: 'overview' } });
          } else {
            navigate({ to: '/openings' });
          }
        }
      } else if (mode === 'forgot') {
        const { error: resetErr } = await supabase.auth.resetPasswordForEmail(email.trim());
        if (resetErr) throw resetErr;
        setNotice('Password reset instructions sent to your email.');
      }
    } catch (err: any) {
      setError(err?.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-layout">
      <section className="login-photo">
        <div className="hero-photos">
          {[8, 9, 10].map((i) => (
            <img
              key={i}
              src={photos[i]}
              alt={[
                'Hands typing on a laptop',
                'Printed documents on a wooden desk',
                'Office meeting room',
              ][i - 8]}
            />
          ))}
        </div>
        <div className="login-quote">
          <blockquote>“The right resume opens the right door.”</blockquote>
          <p>Hunt Your Tribe · Placement Drive 2025</p>
        </div>
      </section>

      <section className="login-form-panel">
        <div className="login-form-inner">
          <Link to="/" className="back-link">
            <ArrowLeft />
            Back to Home
          </Link>

          <h1>
            {mode === 'signup'
              ? 'Create an account'
              : mode === 'forgot'
              ? 'Reset password'
              : mode === 'otp'
              ? 'Email OTP'
              : 'Sign in'}
          </h1>
          <p className="muted text-sm">
            {mode === 'signin'
              ? 'Sign in to access your placement drive portal.'
              : 'Enter your credentials to continue.'}
          </p>

          <div className="tabs segmented" role="tablist" aria-label="Account type">
            <Button
              variant="ghost"
              type="button"
              role="tab"
              aria-selected={!hr}
              className={`tab-button ${!hr ? 'active' : ''}`}
              onClick={() => {
                setHr(false);
                setError('');
              }}
            >
              Candidate
            </Button>
            <Button
              variant="ghost"
              type="button"
              role="tab"
              aria-selected={hr}
              className={`tab-button ${hr ? 'active' : ''}`}
              onClick={() => {
                setHr(true);
                setError('');
              }}
            >
              HR / Recruiter
            </Button>
          </div>

          <form className="form-stack" onSubmit={handleSubmit}>
            <Field label="Email Address">
              <input
                type="email"
                required
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </Field>

            {(mode === 'signin' || mode === 'signup') && (
              <Field label="Password">
                <div className="password-wrap">
                  <input
                    type={show ? 'text' : 'password'}
                    minLength={6}
                    required
                    autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label={show ? 'Hide password' : 'Show password'}
                    onClick={() => setShow(!show)}
                  >
                    {show ? <EyeOff /> : <Eye />}
                  </Button>
                </div>
              </Field>
            )}

            {mode === 'otp' && otpSent && (
              <Field label="6-Digit OTP Token">
                <input
                  type="text"
                  required
                  placeholder="123456"
                  value={otpToken}
                  onChange={(e) => setOtpToken(e.target.value)}
                />
              </Field>
            )}

            {mode === 'signin' && (
              <div className="form-remember">
                <label className="checkbox-label">
                  <input type="checkbox" defaultChecked />
                  Remember me
                </label>
                <Button
                  type="button"
                  variant="link"
                  className="h-auto p-0 text-xs"
                  onClick={() => {
                    setMode('forgot');
                    setNotice('');
                    setError('');
                  }}
                >
                  Forgot password?
                </Button>
              </div>
            )}

            {error && (
              <div role="alert" className="notice border-l-rose-500 bg-rose-500/10 text-rose-300">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <p className="m-0 text-xs">{error}</p>
              </div>
            )}

            {notice && (
              <div role="status" className="notice">
                {notice}
              </div>
            )}

            <Button type="submit" disabled={busy}>
              {busy
                ? 'Processing…'
                : mode === 'signup'
                ? 'Create account'
                : mode === 'forgot'
                ? 'Send reset link'
                : mode === 'otp'
                ? otpSent
                  ? 'Verify OTP & Sign In'
                  : 'Send email OTP'
                : `Sign in as ${hr ? 'HR' : 'Candidate'}`}
            </Button>
          </form>

          {mode === 'signin' ? (
            <>
              <div className="form-divider">OR</div>
              <Button
                variant="outline"
                className="w-full"
                type="button"
                onClick={() => {
                  setMode('otp');
                  setOtpSent(false);
                  setError('');
                }}
              >
                Continue with Email OTP
              </Button>
              <p className="login-bottom">
                New here?{' '}
                <Button
                  variant="link"
                  className="h-auto p-0 text-xs"
                  type="button"
                  onClick={() => {
                    setMode('signup');
                    setError('');
                  }}
                >
                  Create an account
                </Button>
              </p>
            </>
          ) : (
            <Button
              variant="link"
              className="mt-4 w-full"
              type="button"
              onClick={() => {
                setMode('signin');
                setNotice('');
                setError('');
              }}
            >
              Back to sign in
            </Button>
          )}

          {hr && (
            <div className="notice mt-6">
              <Clock size={16} />
              <p>HR accounts are verified against authorized placement drive domains.</p>
            </div>
          )}

          <div className="mt-8 border-t border-border pt-5 text-center">
            <span className="micro">PREVIEW NAVIGATION</span>
            <div className="mt-2 flex justify-center gap-6">
              <Button variant="link" size="sm" onClick={() => navigate({ to: '/openings' })}>
                Candidate view
              </Button>
              <Button
                variant="link"
                size="sm"
                onClick={() => navigate({ to: '/hr', search: { view: 'overview' } })}
              >
                HR view
              </Button>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
