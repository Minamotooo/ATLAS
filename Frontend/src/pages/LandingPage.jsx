import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight, ArrowDown, Brain, MessageSquareText, GitBranch, Radar, Network, Languages,
  BookOpen, ClipboardCheck, MousePointerClick, Lightbulb, TrendingUp, Target,
  CheckCircle2, XCircle, Atom, FlaskConical, Sigma,
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { authFetch, buildApiUrl } from '../context/AuthContext';
import Footer from '../components/Footer';
import MathText from '../components/MathText';
import { fetchPublicStats } from '../lib/progress';
import { SAMPLE_QUESTION } from '../content/sampleQuestion';
import { gsap, ScrollTrigger, useGSAP } from '../motion/gsap';
import { DUR, EASE, STAGGER } from '../motion/tokens';
import SplitText from '../motion/SplitText';
import CountUp from '../motion/CountUp';
import useReveal from '../motion/useReveal';
import useReducedMotion from '../motion/useReducedMotion';
import { enterDelay } from '../motion/PageTransition';
import GlobeFallback from '../three/GlobeFallback';
import { canRunScene } from '../three/capability';
import { sceneState } from '../three/sceneStore';

// three.js + R3F live in their own chunk, fetched only on capable devices.
const HeroScene = lazy(() => import('../three/HeroScene'));

const DEFAULT_COUNTS = [356, 886, 446]; // Physics, Chemistry, Mathematics (matches /stats/public)

const STORY = [
  { key: 'Physics', icon: Atom, dot: 'bg-coral-500', tint: 'text-coral-600', desc: 'landing.storyPhysicsDesc', label: 'courses.physics', align: 'lg:justify-end' },
  { key: 'Chemistry', icon: FlaskConical, dot: 'bg-atlas-600', tint: 'text-atlas-700', desc: 'landing.storyChemistryDesc', label: 'courses.chemistry', align: 'lg:justify-start' },
  { key: 'Mathematics', icon: Sigma, dot: 'bg-gold-500', tint: 'text-gold-600', desc: 'landing.storyMathematicsDesc', label: 'courses.mathematics', align: 'lg:justify-start' },
];

export default function LandingPage() {
  const { t, lang } = useLanguage();
  const reduced = useReducedMotion();
  const locale = lang === 'bn' ? 'bn-BD' : 'en-US';
  const [delay] = useState(() => enterDelay());

  const [stats, setStats] = useState(null);
  const [statsSettled, setStatsSettled] = useState(false);
  const [sections, setSections] = useState([]);
  const [webgl, setWebgl] = useState(false);
  const [focus, setFocus] = useState(-1); // mirrors sceneState.focus for the static fallback

  const pageRef = useRef(null);
  const storyRef = useRef(null);
  const heroRef = useRef(null);
  const workflowRef = useRef(null);

  // ---- data: public stats + catalogue section titles ------------------------
  useEffect(() => {
    let ignore = false;
    fetchPublicStats()
      .then((s) => !ignore && setStats(s))
      .catch(() => {})
      .finally(() => !ignore && setStatsSettled(true));
    authFetch(buildApiUrl('/catalog'))
      .then((r) => (r.ok ? r.json() : null))
      .then((payload) => {
        if (ignore || !payload) return;
        const list = (payload.courses || []).flatMap((c) =>
          (c.sections || [])
            .filter((s) => s.enabled)
            .map((s) => ({ id: s.id, subject: c.subject, en: s.title, bn: s.title_bn || s.title })),
        );
        setSections(list);
      })
      .catch(() => {});
    return () => {
      ignore = true;
    };
  }, []);

  // ---- WebGL: only on capable devices, after first paint, once counts are known
  useEffect(() => {
    if (reduced || !canRunScene()) return undefined;
    let cancelled = false;
    const start = () => !cancelled && setWebgl(true);
    const wait = window.setTimeout(start, 2500); // do not hold the scene hostage to a slow API
    let idle;
    if (statsSettled) {
      idle = window.requestIdleCallback
        ? window.requestIdleCallback(start, { timeout: 1200 })
        : window.setTimeout(start, 300);
    }
    return () => {
      cancelled = true;
      window.clearTimeout(wait);
      if (idle && window.cancelIdleCallback) window.cancelIdleCallback(idle);
      else if (idle) window.clearTimeout(idle);
    };
  }, [reduced, statsSettled]);

  const counts = useMemo(() => {
    const by = stats?.skills_by_subject;
    if (!by) return DEFAULT_COUNTS;
    return [by.Physics || 0, by.Chemistry || 0, by.Mathematics || 0];
  }, [stats]);
  // Freeze the counts the scene was built with, so it is never torn down and rebuilt.
  const sceneCounts = useRef(null);
  if (webgl && !sceneCounts.current) sceneCounts.current = counts;

  // ---- motion ---------------------------------------------------------------
  useGSAP(
    () => {
      // hero entrance: copy lands just as the page curtain lifts
      if (!reduced) {
        gsap.from('[data-hero]', {
          y: 28,
          opacity: 0,
          duration: DUR.slow,
          ease: EASE.out,
          stagger: STAGGER.base,
          delay: delay + 0.35,
          clearProps: 'transform,opacity',
        });
        gsap.to('[data-scroll-cue]', { y: 8, duration: 1.1, ease: 'sine.inOut', repeat: -1, yoyo: true });
      }

      // scroll progress through hero + story drives the globe -> map morph
      ScrollTrigger.create({
        trigger: storyRef.current,
        start: 'top top',
        end: 'bottom bottom',
        onUpdate: (self) => {
          sceneState.progress = self.progress;
        },
      });

      // each story step lights its subject
      gsap.utils.toArray('[data-step]').forEach((el) => {
        const i = Number(el.dataset.step);
        ScrollTrigger.create({
          trigger: el,
          start: 'top 55%',
          end: 'bottom 45%',
          onToggle: (self) => {
            if (self.isActive) {
              sceneState.focus = i;
              setFocus(i);
            } else if (sceneState.focus === i) {
              sceneState.focus = -1;
              setFocus(-1);
            }
          },
        });
      });

      // hero copy drifts up and fades as the story takes over
      if (!reduced) {
        gsap.to('[data-hero-copy]', {
          yPercent: -18,
          opacity: 0.1,
          ease: 'none',
          scrollTrigger: { trigger: heroRef.current, start: 'top top', end: 'bottom 20%', scrub: true },
        });
      }

      // workflow: the progress line fills as you read, badges light up in turn
      const wf = workflowRef.current;
      if (wf) {
        const lineTrigger = { trigger: wf.querySelector('ol'), start: 'top 70%', end: 'bottom 60%', scrub: reduced ? false : 0.6 };
        gsap.fromTo(wf.querySelectorAll('[data-line-x]'), { scaleX: reduced ? 1 : 0 }, { scaleX: 1, ease: 'none', scrollTrigger: lineTrigger });
        gsap.fromTo(wf.querySelectorAll('[data-line-y]'), { scaleY: reduced ? 1 : 0 }, { scaleY: 1, ease: 'none', scrollTrigger: lineTrigger });
        wf.querySelectorAll('[data-badge]').forEach((badge) => {
          ScrollTrigger.create({ trigger: badge, start: 'top 68%', toggleClass: { targets: badge, className: 'is-active' } });
        });
      }

      // BKT curve: the line is uncovered left to right, the answers pop in
      const curve = pageRef.current.querySelector('[data-curve]');
      if (curve && !reduced) {
        const tl = gsap.timeline({ scrollTrigger: { trigger: curve, start: 'top 80%', once: true } });
        tl.fromTo(curve.querySelector('[data-curve-clip]'), { scaleX: 0 }, { scaleX: 1, duration: 1.6, ease: 'power2.inOut', transformOrigin: '0% 50%' })
          .from(curve.querySelectorAll('[data-curve-dot]'), { scale: 0, opacity: 0, transformOrigin: '50% 50%', duration: 0.5, ease: EASE.spring, stagger: 0.12 }, 0.15);
      }

      return () => {
        sceneState.progress = 0;
        sceneState.focus = -1;
      };
    },
    { scope: pageRef, dependencies: [reduced] },
  );

  useReveal(pageRef, [stats, sections.length, lang]);

  const statCards = [
    { value: stats?.skills, label: t('landing.statsSkills'), accent: 'from-atlas-500 to-atlas-700', icon: Brain },
    { value: stats?.prerequisite_edges, label: t('landing.statsEdges'), accent: 'from-coral-400 to-coral-600', icon: GitBranch },
    { value: stats?.sections, label: t('landing.statsSections'), accent: 'from-gold-400 to-gold-600', icon: BookOpen },
    { value: stats?.questions, label: t('landing.statsQuestions'), accent: 'from-mint-400 to-mint-600', icon: CheckCircle2 },
  ];

  const steps = [
    { icon: BookOpen, title: t('landing.step1'), desc: t('landing.step1Desc') },
    { icon: ClipboardCheck, title: t('landing.step2'), desc: t('landing.step2Desc') },
    { icon: MousePointerClick, title: t('landing.step3'), desc: t('landing.step3Desc') },
    { icon: Lightbulb, title: t('landing.step4'), desc: t('landing.step4Desc') },
    { icon: TrendingUp, title: t('landing.step5'), desc: t('landing.step5Desc') },
    { icon: Target, title: t('landing.step6'), desc: t('landing.step6Desc') },
  ];

  return (
    // overflow-x-clip (not hidden) so the pinned scene's position: sticky keeps working
    <div ref={pageRef} className="relative overflow-x-clip">
      {/* ============ HERO + STORY (one scroll scene) ============ */}
      <div ref={storyRef} className="relative">
        {/* The scene sits behind the copy and stays pinned while the story scrolls. */}
        <div className="pointer-events-none sticky top-0 -mb-[100svh] h-[100svh] overflow-hidden" aria-hidden="true">
          <GlobeFallback className="absolute inset-0" still={webgl} focus={webgl ? -1 : focus} />
          {webgl && (
            <Suspense fallback={null}>
              <HeroScene className="absolute inset-0 animate-fade-in" counts={sceneCounts.current || counts} />
            </Suspense>
          )}
        </div>

        {/* Hero */}
        <section ref={heroRef} className="relative z-10 flex min-h-[calc(100svh-5rem)] items-center" aria-labelledby="hero-title">
          <div className="container-wide py-12">
            <div data-hero-copy className="relative isolate max-w-3xl lg:max-w-[50%] 2xl:max-w-[56%]">
              <div aria-hidden="true" className="absolute -inset-x-8 -inset-y-12 -z-10 rounded-[3rem] bg-paper/75 blur-2xl lg:bg-paper/50" />
              <p data-hero className="chip mb-6 text-ink">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="absolute inset-0 rounded-full bg-mint-500 motion-safe:animate-[pulse-ring_1.8s_ease-out_infinite]" />
                  <span className="relative h-2.5 w-2.5 rounded-full bg-mint-500" />
                </span>
                {t('landing.badge')}
              </p>
              <SplitText
                as="h1"
                id="hero-title"
                trigger="load"
                delay={delay}
                className="font-display text-display-lg font-bold text-ink"
                parts={[
                  { text: `${t('landing.heroTitleA')} ` },
                  { text: t('landing.heroTitleB'), className: 'text-shine italic' },
                ]}
              />
              <p data-hero className="mt-6 max-w-lg text-lg leading-relaxed text-ink-soft">
                {t('landing.heroSubtitle')}
              </p>
              <div data-hero className="mt-8 flex flex-wrap gap-3">
                <Link to="/courses" className="btn-primary px-8 py-4 text-base" data-magnetic="0.35" data-cursor="Start">
                  {t('landing.heroCta')}
                  <ArrowRight size={18} aria-hidden="true" />
                </Link>
                <a href="#workflow" className="btn-secondary px-8 py-4 text-base" data-magnetic="0.25">
                  {t('landing.heroSecondaryCta')}
                </a>
              </div>
              <ul data-hero className="mt-8 flex flex-wrap gap-2 text-sm" aria-label="ATLAS at a glance">
                <li className="chip">
                  <span className="font-display text-base font-bold text-atlas-700">
                    {stats ? <CountUp value={stats.skills} locale={locale} /> : '—'}
                  </span>
                  {t('landing.heroChipSkills')}
                </li>
                <li className="chip">
                  <span className="flex -space-x-1" aria-hidden="true">
                    <span className="h-3 w-3 rounded-full bg-coral-500 ring-2 ring-white" />
                    <span className="h-3 w-3 rounded-full bg-atlas-600 ring-2 ring-white" />
                    <span className="h-3 w-3 rounded-full bg-gold-500 ring-2 ring-white" />
                  </span>
                  {(3).toLocaleString(locale)} {t('landing.heroChipSubjects')}
                </li>
                <li className="chip">
                  <Languages size={15} aria-hidden="true" className="text-coral-600" />
                  {t('landing.heroChipBilingual')}
                </li>
              </ul>
            </div>
          </div>
          <a
            href="#story"
            className="scroll-cue absolute bottom-6 left-1/2 -translate-x-1/2 flex-col items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-ink-muted"
          >
            {t('landing.scrollHint')}
            <span data-scroll-cue className="grid h-9 w-9 place-items-center rounded-full border-2 border-ink/15 bg-white/70">
              <ArrowDown size={16} aria-hidden="true" />
            </span>
          </a>
        </section>

        {/* Story: the globe unfolds into one disc per subject */}
        <section id="story" className="relative z-10" aria-labelledby="story-title">
          <div className="container-wide flex min-h-[95svh] items-start pt-[14svh]">
            <div className="glass max-w-2xl rounded-4xl p-7 sm:p-10" data-reveal>
              <p className="eyebrow">{t('landing.storyEyebrow')}</p>
              <SplitText as="h2" id="story-title" className="mt-3 font-display text-display-md font-bold text-ink" text={t('landing.storyTitle')} />
              <p className="mt-5 text-lg leading-relaxed text-ink-soft">
                {t('landing.storyIntroA')}{' '}
                <strong className="font-display text-ink">{stats ? <CountUp value={stats.skills} locale={locale} /> : '—'}</strong>{' '}
                {t('landing.storyIntroB')}{' '}
                <strong className="font-display text-ink">{stats ? <CountUp value={stats.prerequisite_edges} locale={locale} /> : '—'}</strong>{' '}
                {t('landing.storyIntroC')}
              </p>
            </div>
          </div>

          {STORY.map((s, i) => {
            const Icon = s.icon;
            const count = stats?.skills_by_subject?.[s.key] ?? DEFAULT_COUNTS[i];
            return (
              <div key={s.key} data-step={i} className={`container-wide flex min-h-[90svh] items-center ${webgl ? s.align : 'lg:justify-start'}`}>
                <article className="glass w-full max-w-md rounded-4xl p-7 sm:p-9" data-reveal>
                  <div className="flex items-center gap-3">
                    <span className={`grid h-12 w-12 place-items-center rounded-2xl bg-white shadow-soft ${s.tint}`}>
                      <Icon size={24} aria-hidden="true" />
                    </span>
                    <span className="flex items-center gap-2 text-sm font-bold uppercase tracking-[0.14em] text-ink-soft">
                      <span className={`h-2.5 w-2.5 rounded-full ${s.dot}`} aria-hidden="true" />
                      {(i + 1).toLocaleString(locale)} / {(3).toLocaleString(locale)}
                    </span>
                  </div>
                  <h3 className="mt-5 font-display text-display-sm font-bold text-ink">{t(s.label)}</h3>
                  <p className="mt-2 font-display text-4xl font-bold">
                    <CountUp value={count} locale={locale} className={s.tint} />
                    <span className="ml-2 font-sans text-base font-semibold text-ink-muted">{t('landing.storySkills')}</span>
                  </p>
                  <p className="mt-4 leading-relaxed text-ink-soft">{t(s.desc)}</p>
                </article>
              </div>
            );
          })}
        </section>
      </div>

      {/* ============ LIVE STATS ============ */}
      <section className="relative z-10 pb-8 pt-[var(--section-y)]" aria-labelledby="stats-title">
        <div className="container-wide">
          <p id="stats-title" className="eyebrow mb-6" data-reveal="fade">
            <span className="h-2 w-2 rounded-full bg-mint-500" aria-hidden="true" />
            {t('landing.statsEyebrow')}
          </p>
          <dl className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
            {statCards.map(({ value, label, accent, icon: Icon }) => (
              <div key={label} className="card relative flex flex-col overflow-hidden p-5 sm:p-7" data-reveal>
                <div aria-hidden="true" className={`absolute -right-6 -top-6 h-24 w-24 rounded-full bg-gradient-to-br opacity-20 blur-xl ${accent}`} />
                <span className={`grid h-10 w-10 place-items-center rounded-2xl bg-gradient-to-br text-white ${accent}`}>
                  <Icon size={19} aria-hidden="true" />
                </span>
                <dd className="order-2 mt-5 font-display text-display-md font-bold text-ink">
                  <CountUp value={value} locale={locale} />
                </dd>
                <dt className="order-3 mt-1 text-sm font-semibold text-ink-soft">{label}</dt>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* ============ SECTION MARQUEE (real catalogue) ============ */}
      {sections.length > 0 && (
        <div className="relative z-10 overflow-hidden border-y border-ink/10 bg-white/60 py-5" aria-hidden="true">
          <div className="flex w-max gap-3 hover:[animation-play-state:paused]" style={{ animation: 'marquee 90s linear infinite' }}>
            {[0, 1].map((copy) => (
              <div key={copy} className="flex gap-3">
                {sections.map((s) => (
                  <span key={`${copy}-${s.id}`} className="chip whitespace-nowrap text-ink">
                    <span
                      className={`h-2 w-2 rounded-full ${
                        s.subject === 'Physics' ? 'bg-coral-500' : s.subject === 'Chemistry' ? 'bg-atlas-600' : 'bg-gold-500'
                      }`}
                    />
                    {lang === 'bn' ? s.bn : s.en}
                  </span>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ============ FEATURES (bento) ============ */}
      <section id="features" className="relative z-10 py-[var(--section-y)]" aria-labelledby="features-title">
        <div className="container-wide">
          <div className="mb-12 max-w-3xl">
            <p className="eyebrow" data-reveal="fade">{t('landing.featuresEyebrow')}</p>
            <SplitText as="h2" id="features-title" className="mt-3 font-display text-display-lg font-bold text-ink" text={t('landing.featuresTitle')} />
            <p className="mt-5 text-lg text-ink-soft" data-reveal>{t('landing.featuresSubtitle')}</p>
          </div>

          <div className="grid gap-4 lg:grid-cols-12">
            {/* 1. BKT */}
            <article className="card-hover p-7 sm:p-9 lg:col-span-7" data-reveal>
              <FeatureHead icon={Brain} tint="from-atlas-500 to-atlas-700" title={t('landing.feature1Title')} />
              <p className="mt-3 max-w-xl leading-relaxed text-ink-soft">{t('landing.feature1Desc')}</p>
              <BktCurve t={t} locale={locale} />
            </article>

            {/* 2. Sample question: explanations + missing prerequisite */}
            <article className="card p-7 sm:p-9 lg:col-span-5 lg:row-span-2" data-reveal>
              <FeatureHead icon={MessageSquareText} tint="from-coral-400 to-coral-600" title={t('landing.feature2Title')} />
              <p className="mt-3 leading-relaxed text-ink-soft">{t('landing.feature2Desc')}</p>
              <SampleQuestion t={t} lang={lang} />
            </article>

            {/* 3. Diagnostic */}
            <article className="card-hover p-7 lg:col-span-3" data-reveal>
              <FeatureHead icon={Radar} tint="from-mint-400 to-mint-600" title={t('landing.feature4Title')} />
              <p className="mt-3 text-sm leading-relaxed text-ink-soft">{t('landing.feature4Desc')}</p>
              <div className="mt-6 flex items-end gap-1.5" aria-hidden="true">
                {[1, 1, 0, 1, 0, 1, 1].map((ok, i) => (
                  <span
                    key={i}
                    className={`w-full rounded-lg ${ok ? 'bg-mint-500' : 'bg-coral-500'}`}
                    style={{ height: `${18 + [2, 3, 2, 3, 2, 3, 4][i] * 9}px`, opacity: 0.5 + i * 0.07 }}
                  />
                ))}
              </div>
            </article>

            {/* 4. Spillover */}
            <article className="card-hover p-7 lg:col-span-4" data-reveal>
              <FeatureHead icon={GitBranch} tint="from-gold-400 to-gold-600" title={t('landing.feature3Title')} />
              <p className="mt-3 text-sm leading-relaxed text-ink-soft">{t('landing.feature3Desc')}</p>
              <ol className="mt-6 flex flex-wrap items-center gap-2 text-xs font-bold">
                <li className="rounded-full bg-coral-50 px-3 py-1.5 text-coral-600">✗ {t('landing.spillWrong')}</li>
                <li aria-hidden="true" className="text-ink-muted">→</li>
                <li className="rounded-full bg-gold-100 px-3 py-1.5 text-gold-600">{t('landing.spillFocus')}</li>
                <li aria-hidden="true" className="text-ink-muted">→</li>
                <li className="rounded-full bg-mint-50 px-3 py-1.5 text-mint-600">↩ {t('landing.spillBack')}</li>
              </ol>
            </article>

            {/* 5. Mastery map */}
            <article className="card-hover overflow-hidden p-7 sm:p-9 lg:col-span-7" data-reveal>
              <div className="grid items-center gap-6 sm:grid-cols-2">
                <div>
                  <FeatureHead icon={Network} tint="from-atlas-500 to-coral-500" title={t('landing.feature5Title')} />
                  <p className="mt-3 leading-relaxed text-ink-soft">{t('landing.feature5Desc')}</p>
                </div>
                <MiniMasteryGraph />
              </div>
            </article>

            {/* 6. Bilingual */}
            <BilingualCard t={t} />
          </div>
        </div>
      </section>

      {/* ============ WORKFLOW ============ */}
      <section id="workflow" ref={workflowRef} className="relative z-10 pb-[var(--section-y)]" aria-labelledby="workflow-title">
        <div className="container-wide">
          <div className="mb-14 max-w-3xl">
            <p className="eyebrow" data-reveal="fade">{t('landing.workflowEyebrow')}</p>
            <SplitText as="h2" id="workflow-title" className="mt-3 font-display text-display-lg font-bold text-ink" text={t('landing.workflowTitle')} />
            <p className="mt-4 text-lg text-ink-soft" data-reveal>{t('landing.workflowSubtitle')}</p>
          </div>

          <ol className="relative grid gap-8 lg:grid-cols-6 lg:gap-5">
            {/* progress line: horizontal on desktop, vertical on smaller screens */}
            <span aria-hidden="true" className="absolute left-7 right-7 top-7 hidden h-[3px] overflow-hidden rounded-full bg-ink/10 lg:block">
              <span data-line-x className="block h-full w-full origin-left bg-gradient-to-r from-atlas-600 via-coral-500 to-gold-500" />
            </span>
            <span aria-hidden="true" className="absolute bottom-7 left-7 top-7 w-[3px] overflow-hidden rounded-full bg-ink/10 lg:hidden">
              <span data-line-y className="block h-full w-full origin-top bg-gradient-to-b from-atlas-600 via-coral-500 to-gold-500" />
            </span>
            {steps.map((step, idx) => {
              const Icon = step.icon;
              return (
                <li key={idx} className="relative flex gap-5 lg:flex-col lg:gap-6" data-reveal>
                  <span
                    data-badge
                    className="relative z-10 grid h-14 w-14 shrink-0 place-items-center rounded-2xl border-2 border-ink/10 bg-white text-ink-soft shadow-soft transition-colors duration-500 [&.is-active]:border-transparent [&.is-active]:bg-ink [&.is-active]:text-gold-300"
                  >
                    <Icon size={22} aria-hidden="true" />
                    <span className="absolute -right-2 -top-2 grid h-6 w-6 place-items-center rounded-full bg-gold-300 text-[0.7rem] font-bold text-ink">
                      {(idx + 1).toLocaleString(locale)}
                    </span>
                  </span>
                  <div className="pt-1 lg:pt-0">
                    <h3 className="font-display text-xl font-bold text-ink">{step.title}</h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-ink-muted">{step.desc}</p>
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      </section>

      {/* ============ CTA ============ */}
      <section className="relative z-10 pb-[var(--section-y)]" aria-labelledby="cta-title">
        <div className="container-wide">
          <div className="hero-band overflow-hidden rounded-[2.5rem] px-6 py-16 text-center sm:px-12 sm:py-24" data-reveal="scale">
            <SplitText as="h2" id="cta-title" className="mx-auto max-w-3xl font-display text-display-lg font-bold" text={t('landing.ctaTitle')} />
            <p className="mx-auto mt-5 max-w-xl text-lg text-white/85">{t('landing.ctaSubtitle')}</p>
            <Link to="/courses" className="btn-accent mt-10 px-10 py-4 text-lg" data-magnetic="0.4" data-cursor="Go">
              {t('landing.ctaButton')}
              <ArrowRight size={20} aria-hidden="true" />
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}

function FeatureHead({ icon: Icon, tint, title }) {
  return (
    <div className="flex items-center gap-3">
      <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-gradient-to-br text-white shadow-soft ${tint}`}>
        <Icon size={21} aria-hidden="true" />
      </span>
      <h3 className="font-display text-2xl font-bold leading-tight text-ink">{title}</h3>
    </div>
  );
}

/*
 * A real BKT trace: the standard update (posterior, then learning transition)
 * with the engine's Apply-level guess/slip (0.18 / 0.12), P(L0) = 0.30 and
 * P(T) = 0.10, over a short run of answers.
 */
const BKT_ANSWERS = [1, 1, 0, 1, 1, 1, 0, 1];
function bktTrace(answers, { l0 = 0.3, t = 0.1, g = 0.18, s = 0.12 } = {}) {
  const out = [l0];
  let p = l0;
  answers.forEach((ok) => {
    const post = ok ? (p * (1 - s)) / (p * (1 - s) + (1 - p) * g) : (p * s) / (p * s + (1 - p) * (1 - g));
    p = post + (1 - post) * t;
    out.push(p);
  });
  return out;
}

function BktCurve({ t, locale }) {
  const values = useMemo(() => bktTrace(BKT_ANSWERS), []);
  const W = 520;
  const H = 170;
  const pad = { l: 46, r: 14, t: 18, b: 26 };
  const x = (i) => pad.l + (i / (values.length - 1)) * (W - pad.l - pad.r);
  const y = (v) => pad.t + (1 - v) * (H - pad.t - pad.b);
  const d = values.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  const area = `${d} L${x(values.length - 1)},${H - pad.b} L${x(0)},${H - pad.b} Z`;
  const pct = (v) => `${Math.round(v * 100).toLocaleString(locale)}%`;

  return (
    <figure className="mt-7" data-curve>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={`${t('landing.bktCaption')} ${values.map(pct).join(', ')}`}>
        <defs>
          <linearGradient id="bkt-line" x1="0" x2="1">
            <stop offset="0" stopColor="#5533F0" />
            <stop offset="1" stopColor="#FF5A36" />
          </linearGradient>
          <linearGradient id="bkt-area" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="#5533F0" stopOpacity="0.18" />
            <stop offset="1" stopColor="#5533F0" stopOpacity="0" />
          </linearGradient>
          <clipPath id="bkt-clip">
            <rect data-curve-clip x="0" y="0" width={W} height={H} />
          </clipPath>
        </defs>
        {[0, 0.5, 1].map((g) => (
          <g key={g}>
            <line x1={pad.l} x2={W - pad.r} y1={y(g)} y2={y(g)} stroke="rgba(23,19,46,0.08)" />
            <text x={pad.l - 8} y={y(g) + 4} textAnchor="end" fontSize="11" fill="#58537A" fontWeight="600">
              {pct(g)}
            </text>
          </g>
        ))}
        <line x1={pad.l} x2={W - pad.r} y1={y(0.95)} y2={y(0.95)} stroke="#0EA57D" strokeDasharray="4 5" strokeWidth="1.5" />
        <text x={pad.l + 6} y={y(0.95) - 6} textAnchor="start" fontSize="11" fill="#0A7F60" fontWeight="700">
          {pct(0.95)}
        </text>
        <g clipPath="url(#bkt-clip)">
          <path d={area} fill="url(#bkt-area)" />
          <path d={d} fill="none" stroke="url(#bkt-line)" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
        </g>
        {values.slice(1).map((v, i) => (
          <circle
            key={i}
            data-curve-dot
            cx={x(i + 1)}
            cy={y(v)}
            r="6"
            fill={BKT_ANSWERS[i] ? '#0EA57D' : '#FF5A36'}
            stroke="#fff"
            strokeWidth="2.5"
          />
        ))}
      </svg>
      <figcaption className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs font-medium text-ink-muted">
        <span>{t('landing.bktCaption')}</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-mint-500" />{t('landing.bktCorrect')}</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-coral-500" />{t('landing.bktWrong')}</span>
      </figcaption>
    </figure>
  );
}

/* The real question-bank item, answerable in place. */
function SampleQuestion({ t, lang }) {
  const [picked, setPicked] = useState(null);
  const q = SAMPLE_QUESTION;
  const option = q.options.find((o) => o.label === picked);

  return (
    <div className="mt-7 rounded-3xl border border-ink/10 bg-paper p-5 sm:p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <span className="rounded-full bg-atlas-50 px-3 py-1 text-xs font-bold text-atlas-700">
          {t('landing.sampleLabel')} · {t('courses.chemistry')}
        </span>
        <span className="font-mono text-xs text-ink-muted">#{q.id}</span>
      </div>
      <p className="text-lg font-semibold leading-relaxed text-ink" lang="bn">
        <MathText text={q.stem} />
      </p>
      <div className="mt-5 grid grid-cols-2 gap-2.5" role="group" aria-label={t('landing.sampleHint')}>
        {q.options.map((o) => {
          const isPicked = picked === o.label;
          const state = !isPicked ? '' : o.correct ? 'border-mint-500 bg-mint-50' : 'border-coral-500 bg-coral-50';
          return (
            <button
              key={o.label}
              type="button"
              aria-pressed={isPicked}
              onClick={() => setPicked(o.label)}
              className={`flex items-center gap-3 rounded-2xl border-2 px-4 py-3 text-left font-semibold text-ink transition-[border-color,background-color,transform] duration-300 hover:-translate-y-0.5 ${
                state || 'border-ink/10 bg-white hover:border-ink/40'
              }`}
            >
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-ink text-xs font-bold text-white">{o.label}</span>
              <MathText text={o.text} />
            </button>
          );
        })}
      </div>

      <div aria-live="polite" className="mt-4 min-h-[5.5rem]">
        {!option ? (
          <p className="pt-2 text-sm font-medium text-ink-muted">{t('landing.sampleHint')}</p>
        ) : (
          <div key={option.label} className="animate-fade-in space-y-3">
            <p className={`flex items-center gap-2 text-sm font-bold ${option.correct ? 'text-mint-600' : 'text-coral-600'}`}>
              {option.correct ? <CheckCircle2 size={17} aria-hidden="true" /> : <XCircle size={17} aria-hidden="true" />}
              {option.correct ? t('landing.sampleCorrect') : t('landing.sampleWrong')}
            </p>
            <p className="text-sm leading-relaxed text-ink-soft" lang="bn">
              <MathText text={option.explanation} />
            </p>
            {!option.correct && (
              <div className="rounded-2xl border border-gold-300 bg-gold-100/60 p-3.5">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-gold-600">{t('landing.sampleMissing')}</p>
                <p className="mt-1 flex items-start gap-2 text-sm font-semibold text-ink">
                  <Sigma size={16} className="mt-0.5 shrink-0 text-gold-600" aria-hidden="true" />
                  <span>
                    {q.missingSkill[lang] || q.missingSkill.en}{' '}
                    <span className="font-mono text-xs font-medium text-ink-muted">{q.missingSkill.id}</span>
                  </span>
                </p>
                <p className="mt-1.5 text-xs font-medium text-ink-muted">{t('landing.sampleTrace')}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* A small layered skill graph in the mastery map's colours (decorative). */
const GRAPH_NODES = [
  { x: 30, y: 40, m: 2 }, { x: 30, y: 100, m: 2 }, { x: 30, y: 160, m: 1 },
  { x: 110, y: 20, m: 2 }, { x: 110, y: 80, m: 1 }, { x: 110, y: 140, m: 0 }, { x: 110, y: 190, m: 1 },
  { x: 190, y: 50, m: 1 }, { x: 190, y: 120, m: 0 }, { x: 190, y: 175, m: 3 },
  { x: 260, y: 90, m: 3 }, { x: 260, y: 150, m: 3 },
];
const GRAPH_EDGES = [[0, 3], [0, 4], [1, 4], [1, 5], [2, 5], [2, 6], [3, 7], [4, 7], [4, 8], [5, 8], [6, 9], [7, 10], [8, 10], [8, 11], [9, 11]];
const GRAPH_COLORS = ['#FF5A36', '#F5A800', '#0EA57D', '#CBC6BD']; // weak, developing, mastered, not yet

function MiniMasteryGraph() {
  return (
    <svg viewBox="0 0 290 210" className="w-full" aria-hidden="true">
      {GRAPH_EDGES.map(([a, b]) => {
        const A = GRAPH_NODES[a];
        const B = GRAPH_NODES[b];
        const mx = (A.x + B.x) / 2;
        return (
          <path
            key={`${a}-${b}`}
            d={`M${A.x},${A.y} C${mx},${A.y} ${mx},${B.y} ${B.x},${B.y}`}
            fill="none"
            stroke="rgba(23,19,46,0.18)"
            strokeWidth="1.6"
          />
        );
      })}
      {GRAPH_NODES.map((n, i) => (
        <g key={i}>
          <circle cx={n.x} cy={n.y} r="13" fill={GRAPH_COLORS[n.m]} opacity="0.18" />
          <circle cx={n.x} cy={n.y} r="8" fill={GRAPH_COLORS[n.m]} stroke="#fff" strokeWidth="2.5" />
        </g>
      ))}
    </svg>
  );
}

function BilingualCard({ t }) {
  const { toggleLang } = useLanguage();
  return (
    <article className="hero-band relative overflow-hidden rounded-[var(--radius-md)] p-7 sm:p-9 lg:col-span-5" data-reveal>
      <div className="flex items-center gap-3">
        <span className="grid h-11 w-11 place-items-center rounded-2xl bg-white/15 text-gold-300">
          <Languages size={21} aria-hidden="true" />
        </span>
        <span className="text-xs font-bold uppercase tracking-[0.16em] text-gold-300">{t('landing.bilingualEyebrow')}</span>
      </div>
      <h3 className="mt-5 font-display text-display-sm font-bold">{t('landing.bilingualTitle')}</h3>
      <p className="mt-3 leading-relaxed text-white/85">{t('landing.bilingualDesc')}</p>
      <button type="button" onClick={toggleLang} className="btn mt-7 bg-white text-ink hover:bg-gold-300" data-magnetic="0.25">
        <Languages size={17} aria-hidden="true" />
        {t('landing.bilingualToggle')}
      </button>
      <span
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-6 right-4 select-none font-display text-[7rem] font-bold leading-none text-white/10"
      >
        অ A
      </span>
    </article>
  );
}
