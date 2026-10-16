import { Link } from '@tanstack/react-router';
import { ArrowRight, Upload } from 'lucide-react';
import { Button } from './ui/button';
import { photos } from '@/lib/photos';
import { HeroPipeline } from './hero-pipeline';
import { ScoringWalkthrough } from './scoring-walkthrough';

export function HowSteps() {
  return <ScoringWalkthrough />;
}

export function HomeContent() {
  return (
    <main className="animate-page">
      <section className="hero">
        <div className="hero-photos" aria-hidden="true">
          <img src={photos[0]} alt="Printed resumes on a desk" />
          <img src={photos[1]} alt="Handwritten notes and documents" />
          <img src={photos[2]} alt="Laptop on an office desk" />
        </div>
        <div className="container hero-inner">
          <div>
            <div className="eyebrow">AI RESUME SCREENING ENGINE</div>
            <h1>
              See how well your resume fits the role — <em>before you apply.</em>
            </h1>
            <p className="hero-copy">
              Select your target role from 130 benchmark JD templates, upload your resume, and get
              an evidence-grounded screening score powered by our 9-stage backend AI pipeline.
            </p>
            <div className="hero-cta">
              <Button asChild size="lg" className="shadow-lg">
                <Link to="/check-score">
                  <Upload size={18} />
                  Upload Resume &amp; Check Score
                  <ArrowRight size={17} />
                </Link>
              </Button>
            </div>
            <div className="hero-stats">
              {[
                ['130', 'Role Benchmarks'],
                ['9-Stage', 'AI Scrutiny Pipeline'],
                ['100%', 'Verbatim Evidence Grounding'],
              ].map(([n, l]) => (
                <div className="hero-stat" key={n}>
                  <strong>{n}</strong>
                  <span>{l}</span>
                </div>
              ))}
            </div>
          </div>
          <HeroPipeline />
        </div>
      </section>
      <HowSteps />
    </main>
  );
}
