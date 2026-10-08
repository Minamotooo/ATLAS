import { useEffect, useMemo, useRef, useState } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth, authFetch, buildApiUrl } from '../context/AuthContext';
import {
  Search, BookOpen, TrendingUp, Clock, ArrowRight, BarChart3, AlertCircle,
  Atom, FlaskConical, Sigma, Award, LogOut,
} from 'lucide-react';
import { fetchProgress } from '../lib/progress';
import { formatStudyTime, getWeeklyStudySeconds } from '../lib/studyTime';
import CountUp from '../motion/CountUp';
import SplitText from '../motion/SplitText';
import useReveal from '../motion/useReveal';

// One look per subject, shared with the landing page's knowledge globe.
const SUBJECT_STYLE = {
  Physics: {
    icon: Atom,
    gradient: 'from-coral-400 to-coral-600',
    soft: 'bg-coral-50 text-coral-600',
    bar: 'bg-coral-500',
  },
  Chemistry: {
    icon: FlaskConical,
    gradient: 'from-atlas-500 to-atlas-700',
    soft: 'bg-atlas-50 text-atlas-700',
    bar: 'bg-atlas-600',
  },
  Mathematics: {
    icon: Sigma,
    gradient: 'from-gold-400 to-gold-600',
    soft: 'bg-gold-100 text-gold-600',
    bar: 'bg-gold-500',
  },
};
const FALLBACK_STYLE = {
  icon: BookOpen,
  gradient: 'from-ink-soft to-ink',
  soft: 'bg-paper-deep text-ink',
  bar: 'bg-ink',
};

const SUBJECT_LABEL_KEY = {
  Physics: 'courses.physics',
  Chemistry: 'courses.chemistry',
  Mathematics: 'courses.mathematics',
};

export default function CoursesPage() {
  const { t, lang } = useLanguage();
  const { user, loading, signOut } = useAuth();
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState('All');
  const [catalogCourses, setCatalogCourses] = useState([]);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogError, setCatalogError] = useState('');
  const [progress, setProgress] = useState(null);
  const [studySeconds, setStudySeconds] = useState(0);
  const scopeRef = useRef(null);

  const locale = lang === 'bn' ? 'bn-BD' : 'en-US';

  useEffect(() => {
    if (!loading && !user) {
      navigate('/login');
    }
  }, [user, loading, navigate]);

  useEffect(() => {
    let ignore = false;

    async function loadCatalog() {
      setCatalogLoading(true);
      setCatalogError('');

      try {
        const response = await authFetch(buildApiUrl('/catalog'));
        if (!response.ok) {
          throw new Error(`Catalog request failed (${response.status})`);
        }

        const payload = await response.json();
        const rawCourses = Array.isArray(payload?.courses) ? payload.courses : [];
        if (!ignore) {
          setCatalogCourses(rawCourses);
        }
      } catch (error) {
        if (!ignore) {
          setCatalogError(error.message || 'Failed to load catalog');
          setCatalogCourses([]);
        }
      } finally {
        if (!ignore) {
          setCatalogLoading(false);
        }
      }
    }

    if (user) {
      loadCatalog();
    }

    return () => {
      ignore = true;
    };
  }, [user]);

  // Real per-learner figures: mastery from the database, study time from this device.
  useEffect(() => {
    if (!user?.user_id) return undefined;
    let ignore = false;
    fetchProgress(user.user_id)
      .then((payload) => {
        if (!ignore) setProgress(payload);
      })
      .catch(() => {
        if (!ignore) setProgress(null);
      });
    setStudySeconds(getWeeklyStudySeconds(user.user_id));
    return () => {
      ignore = true;
    };
  }, [user?.user_id]);

  const progressByCourse = useMemo(() => {
    const map = new Map();
    (progress?.courses || []).forEach((c) => map.set(c.course_id, c));
    return map;
  }, [progress]);

  const courses = useMemo(() => {
    return catalogCourses.map((course) => {
      const sections = Array.isArray(course.sections) ? course.sections : [];
      const enabledSections = sections.filter((section) => section.enabled);
      const title = lang === 'bn' && course.title_bn ? course.title_bn : course.title;
      const topicCount = enabledSections.reduce(
        (sum, s) => sum + (Array.isArray(s.topics) ? s.topics.length : 0),
        0,
      );
      const courseProgress = progressByCourse.get(course.id);
      const sectionProgress = new Map(
        (courseProgress?.sections || []).map((s) => [s.section_id, s]),
      );
      const diagnosed = courseProgress?.sections_diagnosed || 0;

      return {
        id: course.id,
        title,
        subject: course.subject || '',
        code: course.id?.toUpperCase() || 'COURSE',
        style: SUBJECT_STYLE[course.subject] || FALLBACK_STYLE,
        sectionCount: enabledSections.length,
        topicCount,
        diagnosed,
        mastery: courseProgress?.mastery ?? null,
        status: diagnosed > 0 ? 'in-progress' : 'not-started',
        enabled: !!course.enabled,
        // One segment per section, filled by that section's mastery.
        segments: enabledSections.map((s) => {
          const p = sectionProgress.get(s.id);
          return {
            id: s.id,
            title: lang === 'bn' && s.title_bn ? s.title_bn : s.title,
            diagnosed: !!p?.diagnosed,
            mastery: p?.mastery ?? 0,
          };
        }),
      };
    });
  }, [catalogCourses, lang, progressByCourse]);

  // Filters come from the subjects actually in the catalogue.
  const filters = useMemo(() => {
    const subjects = [...new Set(courses.map((c) => c.subject).filter(Boolean))];
    return [
      { key: 'All', label: t('courses.allSubjects') },
      ...subjects.map((s) => ({ key: s, label: SUBJECT_LABEL_KEY[s] ? t(SUBJECT_LABEL_KEY[s]) : s })),
    ];
  }, [courses, t]);

  const filteredCourses = useMemo(() => {
    const q = search.trim().toLowerCase();
    return courses.filter((c) => {
      const subjectLabel = SUBJECT_LABEL_KEY[c.subject] ? t(SUBJECT_LABEL_KEY[c.subject]) : c.subject;
      const matchesSearch =
        !q ||
        c.title.toLowerCase().includes(q) ||
        subjectLabel.toLowerCase().includes(q) ||
        c.segments.some((s) => (s.title || '').toLowerCase().includes(q));
      const matchesFilter = activeFilter === 'All' || c.subject === activeFilter;
      return matchesSearch && matchesFilter;
    });
  }, [courses, search, activeFilter, t]);

  const inProgressCourses = filteredCourses.filter((c) => c.status === 'in-progress');
  const otherCourses = filteredCourses.filter((c) => c.status !== 'in-progress');

  const activeCourses = progress?.active_courses ?? 0;
  const avgMastery = progress?.average_mastery ?? null;
  const skillsMastered = progress?.skills_mastered ?? 0;
  const totalCourses = courses.length || progress?.courses?.length || 0;

  useReveal(scopeRef, [catalogLoading, progress, filteredCourses.length, activeFilter]);

  return (
    <div ref={scopeRef} className="min-h-screen pb-16">
      {/* Header band */}
      <section className="container-wide pt-4">
        <div className="hero-band overflow-hidden rounded-4xl px-5 py-8 sm:px-10 sm:py-12">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="eyebrow !text-gold-300">{t('courses.dashboardSubtitle')}</p>
              <SplitText
                as="h1"
                trigger="load"
                className="mt-3 font-display text-display-md font-bold"
                parts={[
                  { text: `${t('courses.welcome')}, ` },
                  { text: user?.user_name || t('courses.studentName'), className: 'text-gold-300' },
                ]}
              />
            </div>
            <button
              type="button"
              onClick={() => {
                signOut();
                navigate('/login');
              }}
              className="btn self-start bg-white/10 !py-2.5 text-sm text-white ring-1 ring-white/25 hover:bg-white hover:text-ink sm:self-auto"
            >
              <LogOut size={15} aria-hidden="true" />
              {t('nav.logout')}
            </button>
          </div>
        </div>
      </section>

      {/* Bento stats */}
      <section aria-label="Your progress" className="container-wide mt-5">
        <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
          <MasteryStat
            value={avgMastery}
            locale={locale}
            label={t('courses.avgMastery')}
            caption={avgMastery == null ? t('courses.avgMasteryEmpty') : t('courses.avgMasteryCaption')}
          />
          <StatCard
            icon={BookOpen}
            tint="bg-coral-50 text-coral-600"
            label={t('courses.activeCourses')}
            caption={t('courses.activeCoursesCaption')}
          >
            <CountUp value={activeCourses} locale={locale} />
            <span className="text-ink-muted"> / {totalCourses.toLocaleString(locale)}</span>
          </StatCard>
          <StatCard
            icon={Award}
            tint="bg-mint-50 text-mint-600"
            label={t('courses.skillsMastered')}
            caption={t('courses.skillsMasteredCaption')}
          >
            <CountUp value={skillsMastered} locale={locale} />
          </StatCard>
          <StatCard
            icon={Clock}
            tint="bg-gold-100 text-gold-600"
            label={t('courses.weeklyTime')}
            caption={t('courses.weeklyTimeCaption')}
          >
            {formatStudyTime(studySeconds, lang)}
          </StatCard>
        </div>
      </section>

      <div className="container-wide mt-10">
        {/* Search & filter */}
        <div className="mb-8 flex flex-col gap-3 sm:flex-row" data-reveal="fade">
          <div className="relative flex-1">
            <label htmlFor="course-search" className="sr-only">{t('courses.searchCourses')}</label>
            <Search size={18} aria-hidden="true" className="absolute left-4 top-1/2 -translate-y-1/2 text-ink-muted" />
            <input
              id="course-search"
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t('courses.searchCourses')}
              className="input-field !rounded-full pl-11"
            />
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide sm:pb-0" role="group" aria-label="Filter by subject">
            {filters.map((f) => (
              <button
                key={f.key}
                type="button"
                aria-pressed={activeFilter === f.key}
                onClick={() => setActiveFilter(f.key)}
                className={`whitespace-nowrap rounded-full px-5 py-2.5 text-sm font-semibold transition-colors duration-300 ${
                  activeFilter === f.key
                    ? 'bg-ink text-white shadow-soft'
                    : 'border-2 border-ink/10 bg-white text-ink-soft hover:border-ink/40 hover:text-ink'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Continue learning */}
        {inProgressCourses.length > 0 && (
          <section className="mb-12" aria-labelledby="continue-heading">
            <h2 id="continue-heading" className="mb-5 flex items-center gap-2 font-display text-display-sm font-bold">
              <TrendingUp size={24} className="text-coral-500" aria-hidden="true" />
              {t('courses.continueLearning')}
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {inProgressCourses.map((course) => (
                <CourseCard key={course.id} course={course} t={t} locale={locale} highlight />
              ))}
            </div>
          </section>
        )}

        {/* All courses */}
        <section aria-labelledby="all-heading">
          <h2 id="all-heading" className="mb-5 flex items-center gap-2 font-display text-display-sm font-bold">
            <BookOpen size={24} className="text-atlas-600" aria-hidden="true" />
            {t('courses.allCourses')}
          </h2>
          {catalogError && (
            <div className="card mb-4 flex items-start gap-2 border-red-200 bg-red-50 p-4 text-red-800" role="alert">
              <AlertCircle size={18} className="mt-0.5" aria-hidden="true" />
              <div>
                <p className="text-sm font-semibold">Unable to load course catalog.</p>
                <p className="text-sm">{catalogError}</p>
              </div>
            </div>
          )}
          {catalogLoading ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" role="status" aria-label="Loading courses">
              {[0, 1, 2].map((i) => (
                <div key={i} className="card h-64 animate-pulse bg-paper-deep/60" />
              ))}
            </div>
          ) : filteredCourses.length === 0 ? (
            <div className="card p-12 text-center">
              <Search size={40} className="mx-auto mb-4 text-ink-muted/50" aria-hidden="true" />
              <p className="text-ink-muted">{t('courses.noResults')}</p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {(otherCourses.length > 0 ? otherCourses : filteredCourses).map((course) => (
                <CourseCard key={course.id} course={course} t={t} locale={locale} />
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, tint, label, caption, children }) {
  return (
    <div className="card flex flex-col justify-between gap-4 p-5 sm:p-6" data-reveal>
      <div className="flex items-center gap-3">
        <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-2xl ${tint}`}>
          <Icon size={19} aria-hidden="true" />
        </span>
        <span className="text-sm font-semibold leading-tight text-ink-soft">{label}</span>
      </div>
      <div>
        <div className="font-display text-display-sm font-bold text-ink">{children}</div>
        <p className="mt-1 text-xs font-medium text-ink-muted">{caption}</p>
      </div>
    </div>
  );
}

/* Average mastery with a progress ring. The ring is SVG stroke-dashoffset,
   animated by CSS so it respects reduced motion automatically. */
function MasteryStat({ value, locale, label, caption }) {
  const r = 30;
  const c = 2 * Math.PI * r;
  const pct = value == null ? 0 : Math.max(0, Math.min(100, value));
  const [drawn, setDrawn] = useState(0);
  useEffect(() => {
    const id = requestAnimationFrame(() => setDrawn(pct));
    return () => cancelAnimationFrame(id);
  }, [pct]);

  return (
    <div
      className="card relative col-span-2 flex items-center gap-5 overflow-hidden p-5 sm:p-6 lg:col-span-1"
      data-reveal
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-atlas-100/70 blur-2xl"
      />
      <svg viewBox="0 0 72 72" className="relative h-20 w-20 shrink-0 -rotate-90" aria-hidden="true">
        <circle cx="36" cy="36" r={r} fill="none" stroke="rgb(var(--ink) / 0.08)" strokeWidth="8" />
        <circle
          cx="36"
          cy="36"
          r={r}
          fill="none"
          stroke="url(#mastery-ring)"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - drawn / 100)}
          style={{ transition: 'stroke-dashoffset 1.6s var(--ease-out)' }}
        />
        <defs>
          <linearGradient id="mastery-ring" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#5533F0" />
            <stop offset="100%" stopColor="#FF5A36" />
          </linearGradient>
        </defs>
      </svg>
      <div className="relative min-w-0">
        <div className="flex items-center gap-2 text-sm font-semibold text-ink-soft">
          <BarChart3 size={16} aria-hidden="true" className="text-atlas-600" />
          {label}
        </div>
        <div className="font-display text-display-sm font-bold text-ink">
          {value == null ? '—' : <CountUp value={value} locale={locale} decimals={value % 1 ? 1 : 0} suffix="%" />}
        </div>
        <p className="mt-0.5 text-xs font-medium text-ink-muted">{caption}</p>
      </div>
    </div>
  );
}

function CourseCard({ course, t, locale, highlight }) {
  const hasLessons = course.enabled;
  const Icon = course.style.icon;
  const subjectLabel = SUBJECT_LABEL_KEY[course.subject] ? t(SUBJECT_LABEL_KEY[course.subject]) : course.subject;
  const mastery = course.mastery ?? 0;
  const fmt = (n) => Number(n).toLocaleString(locale);

  return (
    <Link
      to={hasLessons ? `/courses/${course.id}` : '#'}
      className={`card-hover group flex flex-col ${!hasLessons ? 'cursor-default' : ''} ${highlight ? 'ring-2 ring-atlas-600/20' : ''}`}
      onClick={(e) => !hasLessons && e.preventDefault()}
      aria-disabled={!hasLessons || undefined}
      data-reveal
      data-cursor={hasLessons ? 'Open' : undefined}
    >
      <div className={`h-1.5 bg-gradient-to-r ${course.style.gradient}`} />
      <div className="relative flex flex-1 flex-col p-5 sm:p-6">
        <div className="mb-4 flex items-start gap-4">
          <div
            className={`grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-gradient-to-br ${course.style.gradient} text-white shadow-soft transition-transform duration-500 ease-spring group-hover:-rotate-6 group-hover:scale-105`}
          >
            <Icon size={26} aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-bold ${course.style.soft}`}>
              {subjectLabel}
            </span>
            <h3 className="mt-1.5 font-display text-xl font-bold leading-snug text-ink">{course.title}</h3>
          </div>
        </div>

        <p className="mb-5 text-sm font-medium text-ink-muted">
          {fmt(course.sectionCount)} {t('courses.sectionsLabel')} · {fmt(course.topicCount)} {t('courses.topicsLabel')}
        </p>

        {/* Section strip: one bar per section, height = mastery */}
        <div className="mt-auto">
          <div className="mb-2 flex items-center justify-between text-xs font-semibold">
            <span className="text-ink-soft">
              {fmt(course.diagnosed)}/{fmt(course.sectionCount)} {t('courses.sectionsDiagnosed')}
            </span>
            {course.status === 'in-progress' ? (
              <span className="text-ink">{fmt(Math.round(mastery))}% {t('courses.mastery')}</span>
            ) : (
              <span className="text-ink-muted">{t('courses.notStarted')}</span>
            )}
          </div>
          <div className="flex h-10 items-end gap-[3px]" aria-hidden="true">
            {course.segments.map((s) => (
              <span
                key={s.id}
                title={`${s.title}: ${s.diagnosed ? `${Math.round(s.mastery)}%` : t('courses.notStarted')}`}
                className="relative flex h-full flex-1 items-end overflow-hidden rounded-[3px] bg-ink/[0.07]"
              >
                <span
                  className={`block w-full origin-bottom rounded-[3px] ${course.style.bar} transition-transform duration-slow ease-out-expo`}
                  style={{
                    height: '100%',
                    transform: `scaleY(${s.diagnosed ? Math.max(0.08, s.mastery / 100) : 0})`,
                  }}
                />
              </span>
            ))}
          </div>
        </div>

        <div className="mt-5">
          {hasLessons ? (
            <span className="inline-flex items-center gap-1.5 text-sm font-bold text-atlas-700">
              {course.status === 'in-progress' ? t('courses.continueBtn') : t('courses.startCourse')}
              <ArrowRight size={15} aria-hidden="true" className="transition-transform duration-300 group-hover:translate-x-1" />
            </span>
          ) : (
            <span className="text-sm text-ink-muted">{t('courses.startCourse')}</span>
          )}
        </div>
      </div>
    </Link>
  );
}
