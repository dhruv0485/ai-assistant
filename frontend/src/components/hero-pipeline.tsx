import { Fragment, useEffect, useRef } from 'react';

const resumeSkills = ['python', 'docker', 'postgresql', 'faiss', 'langchain'];
const jobSkills = ['python', 'docker', 'faiss', 'langchain', 'kubernetes'];
const breakdown = [
  ['Skills Match', 1], ['Experience Match', .85],
  ['Education Match', .9], ['Keyword Density', .78],
] as const;
const LOOP = 16000;

// All motion shares one clock; only opacity and transforms are interpolated.
function reveal(at: number, finalOpacity = .6): Keyframe[] {
  return [
    { opacity: 0, offset: 0 }, { opacity: 0, offset: at / 16 },
    { opacity: 1, offset: (at + .4) / 16 },
    { opacity: 1, offset: Math.max(13.5, at + .4) / 16 },
    { opacity: finalOpacity, offset: 14 / 16 },
    { opacity: finalOpacity, offset: 15.5 / 16 }, { opacity: 0, offset: 1 },
  ];
}

export function HeroPipeline() {
  const stage = useRef<SVGSVGElement>(null);
  useEffect(() => {
    const svg = stage.current;
    if (!svg) return;
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
    let animations: Animation[] = [];
    let frame = 0;
    const score = svg.querySelector('[data-score]');
    function start() {
      animations.forEach(animation => animation.cancel());
      animations = [];
      cancelAnimationFrame(frame);
      if (!svg) return;
      svg.dataset['pairs'] = '5';
      if (score) score.textContent = '72%';
      if (preference.matches) return;
      const clock = document.timeline.currentTime;
      const animate = (selector: string, frames: Keyframe[]) => {
        svg.querySelectorAll(selector).forEach(element => {
          const animation = element.animate(frames, { duration: LOOP, iterations: Infinity, easing: 'linear' });
          animation.startTime = clock;
          animations.push(animation);
        });
      };
      animate('[data-input="resume"]', reveal(0).map((key, index) => ({ ...key, transform: index < 2 ? 'translateX(-40px)' : 'translateX(0)', easing: 'ease-out' })));
      animate('[data-input="jd"]', reveal(.3).map((key, index) => ({ ...key, transform: index < 2 ? 'translateX(40px)' : 'translateX(0)', easing: 'ease-out' })));
      animate('[data-connectors]', reveal(.9));
      animate('[data-zone="parser"]', reveal(1.5));
      animate('[data-zone="matcher"]', reveal(4.5));
      svg.querySelectorAll('[data-extract]').forEach((element, index) => {
        const at = 1.6 + index * .2;
        const animation = element.animate([
          { opacity: 0, transform: 'translateY(-45px)', offset: 0 },
          { opacity: 0, transform: 'translateY(-45px)', offset: at / 16 },
          { opacity: .7, transform: 'translateY(0)', offset: (at + .6) / 16 },
          { opacity: 0, transform: 'translateY(8px)', offset: (at + .8) / 16 },
          { opacity: 0, offset: 1 },
        ], { duration: LOOP, iterations: Infinity, easing: 'ease-in-out' });
        animation.startTime = clock;
        animations.push(animation);
      });
      [...resumeSkills, ...jobSkills].forEach((_, index) => {
        const row = index % 5;
        const targetRow = index < 5 ? [0, 1, 4, 2, 3][row] : row;
        const y = 145 + row * 14 - (233 + (targetRow ?? row) * 16);
        const at = 2.5 + row * .25;
        animate(`[data-chip="${index}"]`, [
          { opacity: 0, transform: `translateY(${y}px) scale(.9)`, offset: 0 },
          { opacity: 0, transform: `translateY(${y}px) scale(.9)`, offset: at / 16 },
          { opacity: 1, transform: `translateY(${y}px) scale(1)`, offset: (at + .25) / 16 },
          { opacity: 1, transform: `translateY(${y}px)`, offset: 4.5 / 16, easing: 'ease-in-out' },
          { opacity: 1, transform: 'translateY(0)', offset: 5.1 / 16 },
          { opacity: 1, offset: 13.5 / 16 }, { opacity: .6, offset: 14 / 16 },
          { opacity: .6, offset: 15.5 / 16 }, { opacity: 0, offset: 1 },
        ]);
      });
      for (let index = 0; index < 5; index++) {
        const at = 5.1 + index * .6;
        animate(`[data-pair="${index}"]`, reveal(at).map((key, i) => ({ ...key, transform: i < 2 ? 'scaleX(0)' : 'scaleX(1)', easing: 'ease-in-out' })));
      }
      animate('[data-zone="scorer"]', reveal(8));
      animate('[data-ring="first"]', [
        { transform: 'rotate(-180deg)', offset: 0 }, { transform: 'rotate(-180deg)', offset: 8 / 16, easing: 'ease-out' },
        { transform: 'rotate(0deg)', offset: 9.05 / 16 }, { transform: 'rotate(0deg)', offset: 1 },
      ]);
      animate('[data-ring="second"]', [
        { transform: 'rotate(-180deg)', offset: 0 }, { transform: 'rotate(-180deg)', offset: 9.05 / 16, easing: 'ease-out' },
        { transform: 'rotate(-100.8deg)', offset: 9.5 / 16 }, { transform: 'rotate(-100.8deg)', offset: 1 },
      ]);
      breakdown.forEach(([, value], index) => {
        const at = 9.5 + index * .2;
        animate(`[data-bar="${index}"]`, reveal(at).map((key, i) => ({ ...key, transform: `scaleX(${i < 2 ? 0 : value})`, easing: 'ease-in-out' })));
        animate(`[data-bar-label="${index}"]`, reveal(at));
      });
      animate('[data-keywords]', reveal(9.5));
      animate('[data-zone="decision"]', reveal(11, 1));
      animate('[data-complete]', reveal(13.5, 1));
      animate('[data-sweep]', [
        { opacity: 0, transform: 'scaleX(0)', offset: 0 },
        { opacity: 0, transform: 'scaleX(0)', offset: 13.5 / 16 },
        { opacity: .6, transform: 'scaleX(1)', offset: 14.3 / 16 },
        { opacity: 0, transform: 'scaleX(1)', offset: 15 / 16 }, { opacity: 0, offset: 1 },
      ]);
      const startTime = performance.now();
      const tick = (now: number) => {
        const time = ((now - startTime) % LOOP) / 1000;
        svg.dataset['pairs'] = String(Math.max(0, Math.min(5, Math.floor((time - 5.1) / .6) + 1)));
        const progress = Math.max(0, Math.min(1, (time - 8) / 1.5));
        if (score) score.textContent = `${String(Math.round(72 * (1 - (1 - progress) ** 3))).padStart(2, '0')}%`;
        frame = requestAnimationFrame(tick);
      };
      frame = requestAnimationFrame(tick);
    }
    start();
    preference.addEventListener('change', start);
    return () => {
      animations.forEach(animation => animation.cancel());
      cancelAnimationFrame(frame);
      preference.removeEventListener('change', start);
    };
  }, []);

  return <div className="hero-pipeline-wrap">
    <div className="hero-pipeline" aria-hidden="true">
      <svg ref={stage} viewBox="0 0 480 480" fill="none" data-pairs="5">
        <clipPath id="pipeline-ring-right"><path d="M98 318h50v98H98z" /></clipPath>
        <clipPath id="pipeline-ring-left"><path d="M48 318h50v98H48z" /></clipPath>
        <path data-input="resume" className="pipeline-document" d="M104 9h50l18 18v61h-68z M154 9v18h18 M117 41h40 M117 53h32 M117 65h36" />
        <text data-input="resume" x="138" y="104" textAnchor="middle">RESUME.PDF</text>
        <path data-input="jd" className="pipeline-document" d="M308 9h50l18 18v61h-68z M358 9v18h18 M321 53h40 M321 65h32 M320 33h19v12h-19z M325 33v-4h9v4 M320 38h19" />
        <text data-input="jd" x="342" y="104" textAnchor="middle">JD.DOCX</text>
        <path data-connectors className="pipeline-connectors" d="M138 110v12h102v6 M342 110v12H240 M240 205v8 M240 309v7 M240 420v7" />
        <g data-zone="parser" className="pipeline-zone">
          <path d="M28 128h424v77H28z" /><text x="40" y="143">PARSER</text>
          <path data-extract className="pipeline-extraction" d="M112 149h38 M112 156h32 M112 163h36 M112 170h28 M112 177h38 M322 149h38 M322 156h32 M322 163h36" />
        </g>
        <path data-zone="matcher" className="pipeline-zone-outline" d="M28 213h424v96H28z" /><text data-zone="matcher" className="pipeline-zone-label" x="40" y="227">MATCHER</text>
        {[...resumeSkills, ...jobSkills].map((skill, index) => {
          const row = index % 5;
          const targetRow = index < 5 ? [0, 1, 4, 2, 3][row] : row;
          const y = 233 + (targetRow ?? row) * 16;
          const x = index < 5 ? 104 : 300;
          const pair = skill === 'kubernetes' ? 4 : ['python', 'docker', 'faiss', 'langchain'].indexOf(skill);
          return <g key={`${index}-${skill}`} data-chip={index} className={`pipeline-chip pipeline-match-${pair}`}>
            <path d={`M${x} ${y - 10}h96v14h-96z`} /><text x={x + 48} y={y} textAnchor="middle">{skill}</text>
          </g>;
        })}
        {[0, 1, 2, 3, 4].map(index => <path key={index} data-pair={index} className={index === 4 ? 'pipeline-missing-link' : 'pipeline-match-link'} d={index === 4 ? 'M244 292h56' : `M200 ${230 + index * 16}h100 m-50 -2a2 2 0 1 0 0 4a2 2 0 1 0 0 -4`} />)}
        <g data-zone="scorer" className="pipeline-zone">
          <path d="M28 316h424v104H28z" /><text x="40" y="330">SCORER</text>
          <path className="pipeline-ring-track" d="M98 323a45 45 0 1 1 0 90a45 45 0 1 1 0 -90" />
          <g clipPath="url(#pipeline-ring-right)"><path data-ring="first" className="pipeline-ring-arc" d="M98 323a45 45 0 0 1 0 90" /></g>
          <g clipPath="url(#pipeline-ring-left)"><path data-ring="second" className="pipeline-ring-arc pipeline-ring-second" d="M98 413a45 45 0 0 1 0 -90" /></g>
          <text data-score className="pipeline-score" x="98" y="376" textAnchor="middle">72%</text>
          {breakdown.map(([label], index) => <Fragment key={label}>
            <text data-bar-label={index} x="162" y={340 + index * 19}>{label}</text>
            <path data-bar={index} className={index === 0 ? 'pipeline-skill-bar' : 'pipeline-bar'} d={`M162 ${345 + index * 19}h122`} />
          </Fragment>)}
          <text data-keywords x="308" y="345" className="pipeline-matched-copy">Matched<tspan x="308" dy="16">python · docker</tspan><tspan x="308" dy="14">faiss · langchain</tspan></text>
          <text data-keywords x="308" y="396" className="pipeline-missing-copy">Missing · kubernetes</text>
        </g>
        <g data-zone="decision" className="pipeline-zone pipeline-decision">
          <path d="M28 427h424v40H28z" /><text x="40" y="441">DECISION</text>
          <text x="256" y="440" textAnchor="middle" className="pipeline-confidence">SCORE 72 · CONFIDENCE HIGH</text>
          <path className="pipeline-advance" d="M193 445h126v18H193z M208 449a6 6 0 1 1 0 12a6 6 0 1 1 0 -12 M205 455l2 2 4-4" />
          <text x="263" y="460" textAnchor="middle" className="pipeline-advance">ADVANCE</text>
        </g>
        <path data-sweep className="pipeline-sweep" d="M28 424h424" />
        <text data-complete className="pipeline-complete" x="240" y="479" textAnchor="middle">3.2 seconds end-to-end · 100% explainable</text>
      </svg>
    </div>
    <p className="sr-only">Animated diagram showing resume and job description being parsed, matched, scored, and decided.</p>
  </div>;
}