/*
 * Shared frame for the log-in and sign-up pages: copy and two benefit cards
 * on the left, the form card on the right. Pages keep their own form logic.
 */
import SplitText from '../motion/SplitText';

export default function AuthShell({ badgeIcon: BadgeIcon, badge, title, subtitle, benefits, children }) {
  return (
    <div className="relative isolate min-h-[calc(100vh-5rem)] overflow-hidden">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          background:
            'radial-gradient(40% 50% at 12% 20%, rgba(177,163,255,0.35), transparent 70%),' +
            'radial-gradient(35% 45% at 90% 75%, rgba(255,179,158,0.3), transparent 70%),' +
            'radial-gradient(30% 40% at 60% 0%, rgba(255,209,92,0.28), transparent 70%)',
        }}
      />
      <div className="container-wide py-14 sm:py-20">
        <div className="grid items-center gap-12 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="space-y-7">
            <p className="chip text-ink">
              <BadgeIcon size={17} aria-hidden="true" className="text-atlas-600" />
              {badge}
            </p>
            <div>
              <SplitText as="h1" trigger="load" delay={0.35} className="font-display text-display-lg font-bold text-ink" text={title} />
              <p className="mt-5 max-w-xl text-lg leading-relaxed text-ink-soft">{subtitle}</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              {benefits.map((b, i) => (
                <div
                  key={b.title}
                  className={i === 1 ? 'hero-band rounded-[var(--radius-md)] p-6 shadow-soft' : 'card p-6'}
                >
                  <h2 className={`mb-2 font-display text-xl font-bold ${i === 1 ? 'text-white' : 'text-ink'}`}>{b.title}</h2>
                  <p className={`text-sm leading-relaxed ${i === 1 ? 'text-white/85' : 'text-ink-soft'}`}>{b.desc}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="glass rounded-[2rem] p-7 sm:p-9">{children}</section>
        </div>
      </div>
    </div>
  );
}
