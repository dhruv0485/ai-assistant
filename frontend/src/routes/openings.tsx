import { createFileRoute, Link } from '@tanstack/react-router';
import { useState, useEffect } from 'react';
import { Search, ArrowRight, Briefcase, MapPin, Sparkles, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/tribe-ui';
import { useTribe } from '@/lib/tribe-store';
import { pageHead } from '@/lib/tribe-data';
import { photos } from '@/lib/photos';

export const Route = createFileRoute('/openings')({
  head: () =>
    pageHead(
      'Open Positions',
      'Roles currently accepting applications for the Hunt Your Tribe placement drive.',
      photos[11]
    ),
  component: Openings,
});

function getExcerpt(text: string, maxLen = 220): string {
  if (!text) return '';
  const clean = text.replace(/\s+/g, ' ').trim();
  if (clean.length <= maxLen) return clean;
  const truncated = clean.slice(0, maxLen);
  const lastSpace = truncated.lastIndexOf(' ');
  return (lastSpace > 0 ? truncated.slice(0, lastSpace) : truncated) + '...';
}

function Openings() {
  const { jobs, applications, user, candidateProfile, refreshJobs, refreshApplications } = useTribe();
  const [search, setSearch] = useState('');
  const [location, setLocation] = useState('');
  const [experience, setExperience] = useState('');

  useEffect(() => {
    void refreshJobs();
    void refreshApplications();
  }, []);

  const candidateEmail = (user?.email || candidateProfile?.email || '').trim().toLowerCase();

  const appliedJobIds = new Set(
    applications
      .filter((a) => {
        if (!candidateEmail) return false;
        return (a.email || '').trim().toLowerCase() === candidateEmail;
      })
      .map((a) => a.jobId)
  );

  const filtered = jobs.filter(
    (j) =>
      j.status === 'Active' &&
      `${j.title} ${j.department}`.toLowerCase().includes(search.toLowerCase()) &&
      (!location || j.location === location) &&
      (!experience || j.experience === experience)
  );

  return (
    <main className="container page-main page-narrow">
      <div className="page-banner">
        <img src={photos[11]} alt="A bright office desk ready for work" />
        <h1>Open Positions</h1>
        <p>Verified roles published by the hiring team currently accepting applications.</p>
      </div>

      <div className="section-row">
        <span className="micro">{filtered.length} ACTIVE HR OPENINGS</span>
        <div className="flex items-center gap-4">
          <Link
            to="/check-score"
            className="text-muted-foreground hover:text-foreground text-xs flex items-center gap-1 transition-colors"
          >
            <Sparkles size={13} className="text-emerald-400" />
            Check Benchmark Score
          </Link>
          <Link to="/applications" className="text-primary text-xs flex items-center gap-1 font-medium">
            My Applications <ArrowRight size={13} />
          </Link>
        </div>
      </div>

      <div className="filters">
        <div className="search-field">
          <Search />
          <input
            className="control"
            aria-label="Search positions"
            placeholder="Search job title or department..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          className="control"
          aria-label="Location"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
        >
          <option value="">All locations</option>
          {[...new Set(jobs.map((j) => j.location))].map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <select
          className="control"
          aria-label="Experience"
          value={experience}
          onChange={(e) => setExperience(e.target.value)}
        >
          <option value="">All experience levels</option>
          {[...new Set(jobs.map((j) => j.experience))].map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </div>

      <div className="job-list">
        {filtered.map((job) => {
          const hasApplied = appliedJobIds.has(job.id);
          const excerpt = getExcerpt(job.summary, 220);

          return (
            <article className="job-card" key={job.id}>
              <div className="flex-1 min-w-0 pr-4">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <h2 className="text-lg font-semibold tracking-tight">{job.title}</h2>
                  {hasApplied && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/25">
                      <CheckCircle2 size={12} />
                      Submitted
                    </span>
                  )}
                </div>

                <div className="job-meta mt-1">
                  {job.department} · {job.location} · {job.type} · {job.experience}
                </div>

                {excerpt && (
                  <div className="mt-2 text-sm text-muted-foreground leading-relaxed">
                    <p className="line-clamp-3">
                      {excerpt}
                    </p>
                    <Link
                      to="/jobs/$jobId"
                      params={{ jobId: job.id }}
                      className="inline-flex items-center gap-1 mt-1.5 text-xs font-semibold text-primary hover:underline"
                    >
                      View more
                      <ArrowRight size={12} />
                    </Link>
                  </div>
                )}
              </div>

              <div className="shrink-0 flex flex-col sm:items-end gap-2 self-start sm:self-center">
                {hasApplied ? (
                  <div className="flex flex-col sm:items-end gap-1.5">
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                      <CheckCircle2 size={13} />
                      Submitted
                    </span>
                    <Button asChild variant="outline" size="sm">
                      <Link to="/jobs/$jobId" params={{ jobId: job.id }}>
                        View Details
                        <ArrowRight size={13} />
                      </Link>
                    </Button>
                  </div>
                ) : (
                  <Button asChild variant="blue" size="sm">
                    <Link to="/jobs/$jobId" params={{ jobId: job.id }}>
                      View &amp; Apply
                      <ArrowRight size={14} />
                    </Link>
                  </Button>
                )}
              </div>
            </article>
          );
        })}
      </div>

      {!filtered.length && (
        <EmptyState text="No HR job postings match your criteria.">
          {search || location || experience ? (
            <Button
              variant="link"
              onClick={() => {
                setSearch('');
                setLocation('');
                setExperience('');
              }}
            >
              Clear filters
            </Button>
          ) : (
            <p className="text-xs text-muted-foreground mt-2">
              All positions created by HR in the hiring dashboard will automatically appear here.
            </p>
          )}
        </EmptyState>
      )}
    </main>
  );
}
