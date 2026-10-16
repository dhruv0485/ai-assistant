import { useEffect, useState, type ReactNode } from 'react';
import { Link, useRouterState, useNavigate } from '@tanstack/react-router';
import {
  Shield,
  Moon,
  Sun,
  Menu,
  X,
  ChevronDown,
  User as UserIcon,
  Briefcase,
  ShieldCheck,
  LogOut,
} from 'lucide-react';
import { Button } from './ui/button';
import { photos } from '@/lib/photos';
import { useTribe } from '@/lib/tribe-store';

export function Brand() {
  return (
    <Link to="/" className="brand flex items-center gap-2.5">
      <img
        src="/brand-icon.png"
        alt="Hunt Your Tribe Logo"
        className="brand-logo"
      />
      <span className="font-medium text-base tracking-tight">
        Hunt Your Tribe<span className="text-primary">.</span>
      </span>
      <span className="hidden sm:inline-flex items-center text-[10px] font-mono uppercase tracking-wider text-primary bg-primary/10 border border-primary/25 px-2 py-0.5 rounded-full font-semibold">
        Job Portal
      </span>
    </Link>
  );
}

export function SiteShell({ children }: { children: ReactNode }) {
  const [light, setLight] = useState(false);
  const [menu, setMenu] = useState(false);
  const [login, setLogin] = useState(false);
  const path = useRouterState({ select: (s) => s.location.pathname });
  const navigate = useNavigate();
  const { user, userRole, signOut } = useTribe();

  useEffect(() => {
    setMenu(false);
    setLogin(false);
  }, [path]);

  useEffect(() => {
    document.documentElement.dataset['theme'] = light ? 'light' : 'dark';
  }, [light]);

  const handleLogout = async () => {
    await signOut();
    navigate({ to: '/login' });
  };

  const nav = (
    <>
      <Link to="/" activeOptions={{ exact: true }}>
        Home
      </Link>
    </>
  );

  return (
    <>
      <header className="site-nav">
        <div className="container nav-inner">
          <Brand />
          <nav className="nav-links" aria-label="Main navigation">
            {nav}
          </nav>
          <div className="nav-actions">
            <Button
              variant="ghost"
              size="icon"
              aria-label={light ? 'Switch to dark theme' : 'Switch to light theme'}
              title={light ? 'Dark theme' : 'Light theme'}
              onClick={() => setLight(!light)}
            >
              {light ? <Moon size={18} /> : <Sun size={18} />}
            </Button>

            {user ? (
              <div className="dropdown">
                <Button
                  variant="blue"
                  className="nav-login"
                  onClick={() => setLogin(!login)}
                  aria-expanded={login}
                >
                  <span className="max-w-[120px] truncate text-xs">
                    {userRole === 'recruiter' ? 'HR Workspace' : 'Candidate'}
                  </span>
                  <ChevronDown size={13} />
                </Button>
                {login && (
                  <>
                    <div className="fixed inset-0" onClick={() => setLogin(false)} />
                    <div className="dropdown-panel">
                      {userRole === 'recruiter' ? (
                        <>
                          <Link to="/hr">
                            <Briefcase size={16} />
                            HR Dashboard
                          </Link>
                          <Link to="/hr" search={{ view: 'jobs' }}>
                            <Briefcase size={16} />
                            Job Postings
                          </Link>
                          <Link to="/hr" search={{ view: 'referrals' }}>
                            <Briefcase size={16} />
                            Referrals
                          </Link>
                        </>
                      ) : (
                        <>
                          <Link to="/openings">
                            <Briefcase size={16} />
                            Browse Jobs
                          </Link>
                          <Link to="/applications">
                            <UserIcon size={16} />
                            My Applications
                          </Link>
                        </>
                      )}
                      <button
                        onClick={handleLogout}
                        className="flex items-center gap-2 text-danger text-xs px-3 py-2 w-full text-left hover:bg-secondary/50 rounded transition-colors"
                      >
                        <LogOut size={14} />
                        Logout ({user.email?.split('@')[0]})
                      </button>
                    </div>
                  </>
                )}
              </div>
            ) : (
              <div className="dropdown">
                <Button
                  variant="blue"
                  className="nav-login"
                  onClick={() => setLogin(!login)}
                  aria-expanded={login}
                >
                  Login
                  <ChevronDown size={13} />
                </Button>
                {login && (
                  <>
                    <div className="fixed inset-0" onClick={() => setLogin(false)} />
                    <div className="dropdown-panel">
                      <Link to="/login" search={{ role: 'candidate' }}>
                        <UserIcon size={16} />
                        Candidate Login
                      </Link>
                      <Link to="/login" search={{ role: 'hr' }}>
                        <Briefcase size={16} />
                        HR Login
                      </Link>
                    </div>
                  </>
                )}
              </div>
            )}

            <Button
              variant="ghost"
              size="icon"
              className="mobile-menu-trigger"
              aria-label={menu ? 'Close menu' : 'Open menu'}
              aria-expanded={menu}
              onClick={() => setMenu(!menu)}
            >
              {menu ? <X /> : <Menu />}
            </Button>
          </div>
        </div>
      </header>

      <div className="nav-spacer" />

      {menu && (
        <nav className="mobile-drawer" aria-label="Mobile navigation">
          {nav}
          {user ? (
            <>
              {userRole === 'recruiter' ? (
                <>
                  <Link to="/hr">HR Dashboard</Link>
                  <Link to="/hr" search={{ view: 'jobs' }}>
                    Job Postings
                  </Link>
                  <Link to="/hr" search={{ view: 'referrals' }}>
                    Referrals
                  </Link>
                </>
              ) : (
                <>
                  <Link to="/openings">Browse Jobs</Link>
                  <Link to="/applications">My Applications</Link>
                </>
              )}
              <button
                onClick={handleLogout}
                className="text-left text-danger text-sm py-2"
              >
                Logout ({user.email})
              </button>
            </>
          ) : (
            <>
              <Link to="/login" search={{ role: 'candidate' }}>
                Candidate Login
              </Link>
              <Link to="/login" search={{ role: 'hr' }}>
                HR Login
              </Link>
            </>
          )}
        </nav>
      )}

      {children}
      {!path.startsWith('/hr') && path !== '/login' && <Footer />}
    </>
  );
}

export function Footer() {
  return (
    <footer className="footer">
      <div className="container footer-grid">
        <div>
          <Brand />
          <div className="footer-desc">
            <img
              src={photos[7]}
              alt="Notebook and work documents on a desk"
              loading="lazy"
            />
            <p>
              A clearer path from your resume to the right opportunity with evidence-grounded screening.
            </p>
          </div>
        </div>
        <div>
          <h4>Quick Links</h4>
          <div className="footer-links">
            <Link to="/">Home</Link>
            <Link to="/check-score">Check Resume Score</Link>
            <Link to="/login" search={{ role: 'candidate' }}>
              Candidate Login
            </Link>
            <Link to="/login" search={{ role: 'hr' }}>
              HR Login
            </Link>
          </div>
        </div>
        <div>
          <h4>Legal</h4>
          <div className="footer-links">
            <Link to="/privacy">Privacy</Link>
            <Link to="/terms">Terms</Link>
          </div>
        </div>
      </div>
      <div className="container footer-bottom">
        <span>© 2026 Hunt Your Tribe. All rights reserved.</span>
        <span className="flex items-center gap-1.5">
          <ShieldCheck size={12} />
          Made in India
        </span>
      </div>
    </footer>
  );
}
