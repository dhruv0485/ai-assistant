import { Link, useNavigate } from '@tanstack/react-router';
import {
  LayoutDashboard,
  Briefcase,
  Users,
  UserRoundCheck,
  Settings,
  LogOut,
  ChevronDown,
} from 'lucide-react';
import { type ReactNode, useState } from 'react';
import { Button } from './ui/button';
import { Modal, Field } from './tribe-ui';
import { useTribe } from '@/lib/tribe-store';

export function HrShell({
  children,
  title = 'Dashboard',
  active = 'overview',
}: {
  children: ReactNode;
  title?: string;
  active?: string;
}) {
  const [profile, setProfile] = useState(false);
  const { user, candidateProfile, signOut } = useTribe();
  const navigate = useNavigate();

  const hrName =
    user?.user_metadata?.full_name ||
    candidateProfile?.full_name ||
    (user?.email ? user.email.split('@')[0] : 'HR Manager');

  const initials =
    hrName
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((n) => n[0].toUpperCase())
      .join('') || 'HR';

  const handleLogout = async () => {
    await signOut();
    navigate({ to: '/login', search: { role: 'hr' } });
  };

  const nav = [
    { label: 'Dashboard', view: 'overview', icon: LayoutDashboard },
    { label: 'Job Postings', view: 'jobs', icon: Briefcase },
    { label: 'Referrals', view: 'referrals', icon: UserRoundCheck },
    { label: 'Candidates', view: 'candidates', icon: Users },
    { label: 'Settings', view: 'settings', icon: Settings },
  ];

  return (
    <div className="hr-layout">
      <aside className="hr-sidebar">
        <Link to="/" className="flex items-center gap-2 mb-4 px-1 group">
          <img
            src="/brand-icon.png"
            alt="Hunt Your Tribe"
            className="w-6 h-6 rounded-full object-contain bg-white p-0.5 border border-border shadow-xs"
          />
          <span className="font-medium text-xs tracking-tight group-hover:text-primary transition-colors">
            Hunt Your Tribe
          </span>
        </Link>
        <div className="sidebar-label micro">HR WORKSPACE</div>
        <nav aria-label="HR navigation">
          {nav.map((n) => (
            <Link
              key={n.view}
              to="/hr"
              search={{ view: n.view }}
              className={active === n.view ? 'active' : ''}
            >
              <n.icon />
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="hr-profile">
          <div className="initials">{initials}</div>
          <div className="min-w-0 flex-1">
            <p className="text-xs truncate font-medium">{hrName}</p>
            <span className="status text-success mt-0.5 block text-[10px]">HR Verified</span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleLogout}
            aria-label="Logout"
            title="Logout"
          >
            <LogOut size={16} />
          </Button>
        </div>
      </aside>

      <div className="hr-content">
        <header className="hr-topbar">
          <span className="text-sm font-semibold">{title}</span>
          <Button
            variant="ghost"
            className="h-auto p-1.5 text-xs flex items-center gap-2"
            onClick={() => setProfile(true)}
          >
            <div className="initials">{initials}</div>
            <span className="max-w-[150px] truncate">{hrName}</span>
            <ChevronDown size={13} />
          </Button>
        </header>
        {children}
      </div>

      {profile && (
        <Modal title="HR Account Profile" onClose={() => setProfile(false)}>
          <div className="form-stack">
            <Field label="Recruiter Name">
              <input value={hrName} readOnly className="bg-secondary/50 cursor-not-allowed" />
            </Field>
            <Field label="Email Address">
              <input value={user?.email || 'hr@company.com'} readOnly className="bg-secondary/50 cursor-not-allowed" />
            </Field>
            <p className="status text-success text-xs">HR Verified Account · Supabase Authenticated</p>
            <Button variant="outline" onClick={handleLogout} className="w-full mt-2">
              Logout
              <LogOut size={14} className="ml-2" />
            </Button>
          </div>
        </Modal>
      )}
    </div>
  );
}
