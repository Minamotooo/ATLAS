import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useLanguage } from "../context/LanguageContext";
import { useAuth, buildApiUrl } from "../context/AuthContext";
import { AlertCircle, ArrowRight, BookOpen, RefreshCw } from "lucide-react";
import MasteryExplorer from "../components/MasteryExplorer";

/*
 * Learner-wide mastery: every diagnosed section in one table/map, with a
 * subject filter. Per-section pages stay reachable from the section cards.
 */
export default function MasteryPage() {
  const { lang } = useLanguage();
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  const [subject, setSubject] = useState("");
  const [payload, setPayload] = useState(null);
  const [pageLoading, setPageLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [pageError, setPageError] = useState("");

  useEffect(() => {
    if (!loading && !user) navigate("/login");
  }, [loading, user, navigate]);

  const loadData = useCallback(
    async (silent = false) => {
      if (!user) return;
      if (silent) setRefreshing(true);
      else setPageLoading(true);
      setPageError("");
      try {
        const query = subject ? `?subject=${encodeURIComponent(subject)}` : "";
        const response = await fetch(
          buildApiUrl(`/users/${encodeURIComponent(user.user_id)}/mastery${query}`),
        );
        if (!response.ok) throw new Error(`Mastery request failed (${response.status})`);
        setPayload(await response.json());
      } catch (error) {
        setPageError(error.message || "Failed to load mastery");
        setPayload(null);
      } finally {
        setPageLoading(false);
        setRefreshing(false);
      }
    },
    [user, subject],
  );

  useEffect(() => {
    loadData(payload !== null);
    // Switching subject keeps the page on screen instead of the full-page loader.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadData]);

  const sections = useMemo(() => payload?.sections || [], [payload]);
  const subjects = useMemo(() => payload?.subjects || [], [payload]);
  const rows = useMemo(() => payload?.table || [], [payload]);
  const edges = useMemo(() => payload?.map?.edges || [], [payload]);
  const visibleSections = subject
    ? sections.filter((s) => s.subject === subject)
    : sections;

  if (pageLoading) {
    return (
      <div className="min-h-screen bg-atlas-50/50 flex items-center justify-center">
        <div className="card p-10 text-center text-gray-600 flex items-center gap-2">
          <RefreshCw size={18} className="animate-spin" />
          Loading your mastery...
        </div>
      </div>
    );
  }

  if (pageError) {
    return (
      <div className="min-h-screen bg-atlas-50/50 flex items-center justify-center px-4">
        <div className="card p-10 max-w-xl text-center">
          <AlertCircle size={42} className="mx-auto text-red-400 mb-3" />
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Could not load mastery</h2>
          <p className="text-gray-600 mb-6">{pageError}</p>
          <button type="button" onClick={() => loadData()} className="btn-primary">
            <RefreshCw size={16} /> Retry
          </button>
        </div>
      </div>
    );
  }

  const tabClass = (active) =>
    `rounded-xl px-4 py-2 text-sm font-semibold transition-all ${
      active ? "bg-atlas-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
    }`;

  return (
    <div className="min-h-screen bg-atlas-50/50">
      <div className="hero-band">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="font-display text-2xl sm:text-3xl font-bold">Your mastery</h1>
              <p className="text-white/80 text-sm mt-2">
                Every section you have diagnosed, in one map. Dashed arrows are
                prerequisites taught in another section.
              </p>
            </div>
            <button
              type="button"
              onClick={() => loadData(true)}
              disabled={refreshing}
              className="btn-secondary"
            >
              <RefreshCw size={16} className={refreshing ? "animate-spin" : ""} />
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-5">
        {sections.length === 0 ? (
          <div className="card p-8 text-center">
            <BookOpen size={40} className="mx-auto text-atlas-400 mb-3" />
            <h2 className="text-xl font-semibold text-gray-800 mb-2">No mastery yet</h2>
            <p className="text-gray-600 mb-6 max-w-md mx-auto">
              Each section opens with a short diagnostic. Finish one and its skills
              appear here, coloured by how well you know them.
            </p>
            <Link to="/courses" className="btn-primary inline-flex">
              Choose a section <ArrowRight size={16} />
            </Link>
          </div>
        ) : (
          <>
            {subjects.length > 1 && (
              <div className="card p-3">
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={() => setSubject("")} className={tabClass(!subject)}>
                    All subjects
                  </button>
                  {subjects.map((s) => (
                    <button
                      key={s.subject}
                      type="button"
                      onClick={() => setSubject(s.subject)}
                      className={tabClass(subject === s.subject)}
                    >
                      {s.subject} · {s.skills}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {visibleSections.map((s) => (
                <Link
                  key={s.section_id}
                  to={`/courses/${s.course_id}/sections/${s.section_id}/mastery`}
                  className="card p-4 border border-atlas-100 hover:border-atlas-300 transition-colors group"
                >
                  <div className="text-xs text-gray-500 uppercase tracking-wide">{s.subject}</div>
                  <div className="font-semibold text-gray-900 mt-1">
                    {lang === "bn" && s.title_bn ? s.title_bn : s.title}
                  </div>
                  <div className="flex items-center gap-2 mt-3">
                    <div className="h-2 flex-1 rounded-full bg-gray-100 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-atlas-500"
                        style={{ width: `${Math.max(0, Math.min(100, s.mastery))}%` }}
                      />
                    </div>
                    <span className="text-sm font-semibold text-gray-800">{Math.round(s.mastery)}%</span>
                  </div>
                  <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
                    <span>
                      {s.skills_mastered}/{s.skills} skills mastered
                    </span>
                    <span className="inline-flex items-center gap-1 font-semibold text-atlas-700 group-hover:gap-1.5 transition-all">
                      Section map <ArrowRight size={12} />
                    </span>
                  </div>
                </Link>
              ))}
            </div>

            <MasteryExplorer
              rows={rows}
              edges={edges}
              emptyMapText="No skills to show for this subject yet."
            />
          </>
        )}
      </div>
    </div>
  );
}
