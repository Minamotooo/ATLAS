import { Link, useLocation } from "react-router-dom";
import { useLanguage } from "../context/LanguageContext";
import { useAuth } from "../context/AuthContext";
import { Menu, X, Globe, Lock, LogOut } from "lucide-react";
import { useEffect, useLayoutEffect, useRef, useState } from "react";

const LOCKED_TITLE = "Complete diagnostic to unlock mastery";

/*
 * Floating glass capsule. The active link sits on an ink pill that slides
 * between items (transform + width, measured from the DOM), so the whole bar
 * reads as one object rather than a row of buttons.
 */
export default function Navbar() {
  const { t, lang, toggleLang } = useLanguage();
  const { user, signOut } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const location = useLocation();
  const isMasteryRoute = location.pathname.includes("/mastery");
  const isCoursesRoute =
    location.pathname.startsWith("/courses") && !isMasteryRoute;

  // Close the mobile sheet on navigation and on Escape.
  useEffect(() => setMobileOpen(false), [location.pathname]);
  useEffect(() => {
    if (!mobileOpen) return undefined;
    const onKey = (e) => e.key === "Escape" && setMobileOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mobileOpen]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const links = [
    { to: "/", label: t("nav.home"), active: location.pathname === "/" },
    { to: "/courses", label: t("nav.courses"), active: isCoursesRoute },
  ];
  if (user) {
    // /mastery shows every diagnosed section, with its own empty state.
    links.push({
      to: "/mastery",
      label: t("courses.mastery"),
      active: isMasteryRoute,
    });
  }
  if (user?.is_admin) {
    links.push({
      to: "/admin/ontology",
      label: "Admin",
      active: location.pathname.startsWith("/admin/ontology"),
    });
    links.push({
      to: "/admin/stats",
      label: "Performance",
      active: location.pathname.startsWith("/admin/stats"),
    });
  }

  // Sliding active pill.
  const listRef = useRef(null);
  const [pill, setPill] = useState({ x: 0, w: 0, visible: false });
  const activeIndex = links.findIndex((l) => l.active && !l.locked);
  useLayoutEffect(() => {
    const list = listRef.current;
    if (!list) return undefined;
    const measure = () => {
      const el = list.querySelector('[data-nav-active="true"]');
      if (!el) {
        setPill((p) => ({ ...p, visible: false }));
        return;
      }
      setPill({ x: el.offsetLeft, w: el.offsetWidth, visible: true });
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(list);
    return () => ro.disconnect();
  }, [activeIndex, lang, links.length]);

  const itemClass = (active) =>
    `relative z-10 rounded-full px-4 py-2 text-sm font-semibold transition-colors duration-300 ${
      active ? "text-white" : "text-ink-soft hover:text-ink"
    }`;

  return (
    <header className="sticky top-0 z-50 px-3 pt-3 sm:px-5">
      <nav aria-label="Main" className="container-wide !px-0">
        <div
          className={`glass flex h-16 items-center justify-between gap-3 rounded-full pl-3 pr-2 transition-shadow duration-500 sm:pl-4 ${
            scrolled ? "shadow-lift" : "shadow-soft"
          }`}
        >
          {/* Logo */}
          <Link
            to="/"
            className="flex shrink-0 items-center gap-2.5 rounded-full pr-2"
            data-cursor="Home"
          >
            {/* the logo artwork is white, so it sits on an ink tile */}
            <span className="grid h-10 w-10 place-items-center rounded-full bg-ink shadow-soft">
              <img src="/logo.png" alt="" className="h-7 w-7 object-contain" width="28" height="28" />
            </span>
            <span className="font-display text-xl font-bold tracking-tight text-ink">
              ATLAS<span className="text-coral">.</span>
            </span>
          </Link>

          {/* Desktop links */}
          <ul ref={listRef} className="relative hidden items-center gap-1 md:flex">
            <span
              aria-hidden="true"
              className="absolute left-0 top-0 h-full rounded-full bg-ink shadow-soft"
              style={{
                width: pill.w,
                transform: `translateX(${pill.x}px)`,
                opacity: pill.visible ? 1 : 0,
                transition:
                  "transform var(--dur-base) var(--ease-out), width var(--dur-base) var(--ease-out), opacity var(--dur-fast) linear",
              }}
            />
            {links.map((link) => (
              <li key={link.label}>
                {link.locked ? (
                  <button
                    type="button"
                    disabled
                    title={LOCKED_TITLE}
                    className="inline-flex cursor-not-allowed items-center gap-1.5 rounded-full px-4 py-2 text-sm font-semibold text-ink-muted"
                  >
                    <Lock size={14} aria-hidden="true" />
                    {link.label}
                    <span className="sr-only"> (locked: {LOCKED_TITLE})</span>
                  </button>
                ) : (
                  <Link
                    to={link.to}
                    data-nav-active={link.active ? "true" : undefined}
                    aria-current={link.active ? "page" : undefined}
                    className={itemClass(link.active)}
                  >
                    {link.label}
                  </Link>
                )}
              </li>
            ))}
          </ul>

          {/* Right actions */}
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={toggleLang}
              className="flex items-center gap-1.5 rounded-full px-3 py-2 text-sm font-semibold text-ink-soft transition-colors hover:bg-ink/5 hover:text-ink"
              title={lang === "en" ? "বাংলায় পরিবর্তন করুন" : "Switch to English"}
              aria-label={lang === "en" ? "বাংলায় পরিবর্তন করুন" : "Switch to English"}
            >
              <Globe size={16} aria-hidden="true" />
              <span className="hidden sm:inline">{lang === "en" ? "বাং" : "EN"}</span>
            </button>

            <div className="hidden items-center gap-1.5 md:flex">
              {user ? (
                <>
                  <span className="hidden items-center gap-2 rounded-full bg-paper-deep px-3 py-2 text-sm font-semibold text-ink lg:inline-flex">
                    <span
                      aria-hidden="true"
                      className="grid h-6 w-6 place-items-center rounded-full bg-gradient-to-br from-gold-300 to-coral-400 text-xs font-bold text-ink"
                    >
                      {user.user_name?.[0]?.toUpperCase()}
                    </span>
                    {t("nav.hello")}, {user.user_name}
                  </span>
                  <button
                    type="button"
                    onClick={signOut}
                    className="btn-primary !px-4 !py-2 text-sm"
                    data-magnetic="0.2"
                  >
                    <LogOut size={15} aria-hidden="true" />
                    {t("nav.logout")}
                  </button>
                </>
              ) : (
                <>
                  <Link
                    to="/login"
                    aria-current={location.pathname === "/login" ? "page" : undefined}
                    className="rounded-full px-4 py-2 text-sm font-semibold text-ink-soft transition-colors hover:bg-ink/5 hover:text-ink"
                  >
                    {t("nav.login")}
                  </Link>
                  <Link to="/signup" className="btn-primary !px-5 !py-2 text-sm" data-magnetic="0.25">
                    {t("nav.signup")}
                  </Link>
                </>
              )}
            </div>

            <button
              type="button"
              onClick={() => setMobileOpen((open) => !open)}
              aria-expanded={mobileOpen}
              aria-controls="mobile-menu"
              aria-label={mobileOpen ? "Close menu" : "Open menu"}
              className="grid h-11 w-11 place-items-center rounded-full bg-ink text-white md:hidden"
            >
              {mobileOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>

        {/* Mobile sheet */}
        {mobileOpen && (
          <div
            id="mobile-menu"
            className="glass mt-2 animate-fade-in rounded-4xl p-3 md:hidden"
          >
            <ul className="space-y-1">
              {links.map((link) => (
                <li key={link.label}>
                  {link.locked ? (
                    <span
                      title={LOCKED_TITLE}
                      className="flex cursor-not-allowed items-center gap-2 rounded-2xl px-4 py-3 text-sm font-semibold text-ink-muted"
                    >
                      <Lock size={14} aria-hidden="true" />
                      {link.label} (Locked)
                    </span>
                  ) : (
                    <Link
                      to={link.to}
                      onClick={() => setMobileOpen(false)}
                      aria-current={link.active ? "page" : undefined}
                      className={`block rounded-2xl px-4 py-3 text-sm font-semibold transition-colors ${
                        link.active ? "bg-ink text-white" : "text-ink hover:bg-ink/5"
                      }`}
                    >
                      {link.label}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
            <hr className="my-2 border-ink/10" />
            {user ? (
              <div className="space-y-1">
                <span className="block rounded-2xl bg-paper-deep px-4 py-3 text-sm font-semibold text-ink">
                  {t("nav.hello")}, {user.user_name}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    signOut();
                    setMobileOpen(false);
                  }}
                  className="btn-primary w-full"
                >
                  {t("nav.logout")}
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                <Link
                  to="/login"
                  onClick={() => setMobileOpen(false)}
                  className="btn-secondary"
                >
                  {t("nav.login")}
                </Link>
                <Link
                  to="/signup"
                  onClick={() => setMobileOpen(false)}
                  className="btn-primary"
                >
                  {t("nav.signup")}
                </Link>
              </div>
            )}
          </div>
        )}
      </nav>
    </header>
  );
}
