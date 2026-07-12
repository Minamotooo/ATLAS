import { Link, useLocation } from "react-router-dom";
import { useLanguage } from "../context/LanguageContext";
import { useAuth, buildApiUrl } from "../context/AuthContext";
import { Menu, X, Globe, Lock } from "lucide-react";
import { useEffect, useState } from "react";

export default function Navbar() {
  const { t, lang, toggleLang } = useLanguage();
  const { user, signOut } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [masteryLinkPath, setMasteryLinkPath] = useState("");
  const location = useLocation();
  const isMasteryRoute = location.pathname.includes("/mastery");
  const isCoursesRoute =
    location.pathname.startsWith("/courses") && !isMasteryRoute;

  useEffect(() => {
    let ignore = false;

    async function resolveMasteryShortcut() {
      if (!user?.user_id) {
        setMasteryLinkPath("");
        return;
      }

      try {
        const catalogResponse = await fetch(buildApiUrl("/catalog"));
        if (!catalogResponse.ok) {
          throw new Error(`Catalog request failed (${catalogResponse.status})`);
        }

        const catalogPayload = await catalogResponse.json();
        const courses = Array.isArray(catalogPayload?.courses)
          ? catalogPayload.courses
          : [];
        const enabledSections = courses.flatMap((course) =>
          (Array.isArray(course?.sections) ? course.sections : [])
            .filter((section) => section?.enabled)
            .map((section) => ({ courseId: course.id, sectionId: section.id })),
        );

        if (enabledSections.length === 0) {
          if (!ignore) {
            setMasteryLinkPath("");
          }
          return;
        }

        const sectionStates = await Promise.all(
          enabledSections.map(async ({ courseId, sectionId }) => {
            try {
              const response = await fetch(
                buildApiUrl(
                  `/users/${encodeURIComponent(user.user_id)}/sections/${encodeURIComponent(sectionId)}/state`,
                ),
              );
              if (!response.ok) {
                return { courseId, sectionId, unlocked: false };
              }
              const payload = await response.json();
              return {
                courseId,
                sectionId,
                unlocked: !payload?.mastery_locked,
              };
            } catch {
              return { courseId, sectionId, unlocked: false };
            }
          }),
        );

        const firstUnlocked = sectionStates.find((entry) => entry.unlocked);
        if (!ignore) {
          setMasteryLinkPath(
            firstUnlocked
              ? `/courses/${firstUnlocked.courseId}/sections/${firstUnlocked.sectionId}/mastery`
              : "",
          );
        }
      } catch {
        if (!ignore) {
          setMasteryLinkPath("");
        }
      }
    }

    resolveMasteryShortcut();

    return () => {
      ignore = true;
    };
  }, [user?.user_id, location.pathname]);

  return (
    <nav className="sticky top-0 z-50 bg-atlas-700 shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5 shrink-0">
            <img src="/logo.png" alt="ATLAS" className="h-9 w-auto" />
            <span className="font-display font-bold text-xl text-white">
              ATLAS
            </span>
          </Link>

          {/* Desktop Nav Links */}
          <div className="hidden md:flex items-center gap-1">
            <Link
              to="/"
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                location.pathname === "/"
                  ? "text-white bg-white/15"
                  : "text-atlas-200 hover:text-white hover:bg-white/10"
              }`}
            >
              {t("nav.home")}
            </Link>
            <Link
              to="/courses"
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                isCoursesRoute
                  ? "text-white bg-white/15"
                  : "text-atlas-200 hover:text-white hover:bg-white/10"
              }`}
            >
              {t("nav.courses")}
            </Link>
            {user &&
              (masteryLinkPath ? (
                <Link
                  to={masteryLinkPath}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isMasteryRoute
                      ? "text-white bg-white/15"
                      : "text-atlas-200 hover:text-white hover:bg-white/10"
                  }`}
                >
                  {t("courses.mastery")}
                </Link>
              ) : (
                <button
                  type="button"
                  disabled
                  title="Complete diagnostic to unlock mastery"
                  className="px-4 py-2 rounded-lg text-sm font-medium text-atlas-300 bg-white/5 cursor-not-allowed inline-flex items-center gap-1.5"
                >
                  <Lock size={14} />
                  {t("courses.mastery")}
                </button>
              ))}
          </div>

          {/* Right Actions */}
          <div className="flex items-center gap-2">
            {/* Language Toggle */}
            <button
              onClick={toggleLang}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-atlas-200 hover:text-white hover:bg-white/10 transition-colors"
              title={
                lang === "en" ? "বাংলায় পরিবর্তন করুন" : "Switch to English"
              }
            >
              <Globe size={16} />
              <span className="hidden sm:inline">
                {lang === "en" ? "বাং" : "EN"}
              </span>
            </button>

            {/* Auth Buttons — desktop */}
            <div className="hidden md:flex items-center gap-2">
              {user ? (
                <>
                  <span className="px-4 py-2 rounded-lg text-sm font-medium text-white/90 bg-white/10">
                    {t("nav.hello")}, {user.user_name}
                  </span>
                  <button
                    onClick={signOut}
                    className="px-4 py-2 text-sm font-semibold text-atlas-700 bg-white rounded-xl hover:bg-atlas-100 transition-all shadow-md hover:shadow-lg"
                  >
                    {t("nav.logout")}
                  </button>
                </>
              ) : (
                <>
                  <Link
                    to="/login"
                    className="px-4 py-2 text-sm font-medium text-atlas-200 hover:text-white rounded-lg hover:bg-white/10 transition-colors"
                  >
                    {t("nav.login")}
                  </Link>
                  <Link
                    to="/signup"
                    className="px-4 py-2 text-sm font-semibold text-atlas-700 bg-white rounded-xl hover:bg-atlas-100 transition-all shadow-md hover:shadow-lg"
                  >
                    {t("nav.signup")}
                  </Link>
                </>
              )}
            </div>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="md:hidden p-2 rounded-lg text-atlas-200 hover:bg-white/10 transition-colors"
            >
              {mobileOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div className="md:hidden border-t border-white/10 bg-atlas-700 animate-fade-in">
          <div className="px-4 py-3 space-y-1">
            <Link
              to="/"
              onClick={() => setMobileOpen(false)}
              className="block px-4 py-3 rounded-xl text-sm font-medium text-atlas-200 hover:bg-white/10 hover:text-white transition-colors"
            >
              {t("nav.home")}
            </Link>
            <Link
              to="/courses"
              onClick={() => setMobileOpen(false)}
              className="block px-4 py-3 rounded-xl text-sm font-medium text-atlas-200 hover:bg-white/10 hover:text-white transition-colors"
            >
              {t("nav.courses")}
            </Link>
            {user &&
              (masteryLinkPath ? (
                <Link
                  to={masteryLinkPath}
                  onClick={() => setMobileOpen(false)}
                  className="block px-4 py-3 rounded-xl text-sm font-medium text-atlas-200 hover:bg-white/10 hover:text-white transition-colors"
                >
                  {t("courses.mastery")}
                </Link>
              ) : (
                <span
                  title="Complete diagnostic to unlock mastery"
                  className="block px-4 py-3 rounded-xl text-sm font-medium text-atlas-300 bg-white/5 cursor-not-allowed"
                >
                  {t("courses.mastery")} (Locked)
                </span>
              ))}
            <hr className="my-2 border-white/10" />
            {user ? (
              <>
                <span className="block px-4 py-3 rounded-xl text-sm font-medium text-atlas-200 bg-white/10">
                  {t("nav.hello")}, {user.user_name}
                </span>
                <button
                  onClick={() => {
                    signOut();
                    setMobileOpen(false);
                  }}
                  className="w-full text-left px-4 py-3 rounded-xl text-sm font-semibold text-atlas-700 bg-white"
                >
                  {t("nav.logout")}
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  onClick={() => setMobileOpen(false)}
                  className="block w-full text-left px-4 py-3 rounded-xl text-sm font-medium text-atlas-200 hover:bg-white/10 transition-colors"
                >
                  {t("nav.login")}
                </Link>
                <Link
                  to="/signup"
                  onClick={() => setMobileOpen(false)}
                  className="block w-full px-4 py-3 text-sm font-semibold text-atlas-700 bg-white rounded-xl"
                >
                  {t("nav.signup")}
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
