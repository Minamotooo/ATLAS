import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useLanguage } from "../context/LanguageContext";
import { useAuth, buildApiUrl } from "../context/AuthContext";
import { AlertCircle, ArrowLeft, Layers, Lock, RefreshCw } from "lucide-react";
import MasteryExplorer from "../components/MasteryExplorer";

// ─── Main component ───────────────────────────────────────────────────────────
export default function SectionMasteryPage() {
  const { courseId, sectionId } = useParams();
  const { lang } = useLanguage();
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  const [sectionMeta, setSectionMeta] = useState(null);
  const [masteryPayload, setMasteryPayload] = useState(null);
  const [pageLoading, setPageLoading] = useState(true);
  const [pageError, setPageError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (!loading && !user) navigate("/login");
  }, [loading, user, navigate]);

  const loadPageData = useCallback(
    async (silent = false) => {
      if (!user) return;
      if (silent) {
        setRefreshing(true);
        setPageError("");
      } else {
        setPageLoading(true);
        setPageError("");
      }

      try {
        const [catalogResponse, masteryResponse] = await Promise.all([
          fetch(buildApiUrl("/catalog")),
          fetch(
            buildApiUrl(
              `/users/${encodeURIComponent(user.user_id)}/sections/${encodeURIComponent(sectionId)}/mastery`,
            ),
          ),
        ]);

        if (!catalogResponse.ok)
          throw new Error(`Catalog request failed (${catalogResponse.status})`);
        if (!masteryResponse.ok) {
          let detail = `Mastery request failed (${masteryResponse.status})`;
          try {
            const errorPayload = await masteryResponse.json();
            if (
              typeof errorPayload?.detail === "string" &&
              errorPayload.detail.trim()
            ) {
              detail = errorPayload.detail;
            }
          } catch {
            /* ignore */
          }
          throw new Error(detail);
        }

        const catalogPayload = await catalogResponse.json();
        const masteryData = await masteryResponse.json();
        const courses = Array.isArray(catalogPayload?.courses)
          ? catalogPayload.courses
          : [];
        const course = courses.find((item) => item.id === courseId) || null;
        const section =
          course?.sections?.find((item) => item.id === sectionId) || null;

        setSectionMeta(section);
        setMasteryPayload(masteryData);
      } catch (error) {
        setPageError(error.message || "Failed to load section mastery");
        setMasteryPayload(null);
      } finally {
        setPageLoading(false);
        setRefreshing(false);
      }
    },
    [courseId, sectionId, user],
  );

  useEffect(() => {
    loadPageData();
  }, [loadPageData]);

  const sectionTitle = useMemo(() => {
    if (!sectionMeta) return sectionId;
    return lang === "bn" && sectionMeta.title_bn
      ? sectionMeta.title_bn
      : sectionMeta.title;
  }, [sectionMeta, lang, sectionId]);

  const tableRows = useMemo(
    () => (Array.isArray(masteryPayload?.table) ? masteryPayload.table : []),
    [masteryPayload],
  );

  const edgeRows = useMemo(() => {
    const edges = masteryPayload?.map?.edges;
    return Array.isArray(edges) ? edges : [];
  }, [masteryPayload]);

  // ── Loading / error screens ──────────────────────────────────────────────
  if (pageLoading) {
    return (
      <div className="min-h-screen bg-atlas-50/50 flex items-center justify-center">
        <div className="card p-10 text-center text-gray-600 flex items-center gap-2">
          <RefreshCw size={18} className="animate-spin" />
          Loading section mastery...
        </div>
      </div>
    );
  }

  if (pageError) {
    return (
      <div className="min-h-screen bg-atlas-50/50 flex items-center justify-center px-4">
        <div className="card p-10 max-w-xl text-center">
          <AlertCircle size={42} className="mx-auto text-red-400 mb-3" />
          <h2 className="text-xl font-semibold text-gray-800 mb-2">
            Could not load mastery
          </h2>
          <p className="text-gray-600 mb-6">{pageError}</p>
          <div className="flex flex-wrap justify-center gap-3">
            <button
              type="button"
              onClick={() => loadPageData()}
              className="btn-primary"
            >
              <RefreshCw size={16} /> Retry
            </button>
            <Link
              to={`/courses/${courseId}/sections/${sectionId}`}
              className="btn-secondary"
            >
              <ArrowLeft size={16} /> Back to Section
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const isLocked = !!masteryPayload?.locked;

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-atlas-50/50">
      {/* Page header */}
      <div className="hero-band">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
          <Link
            to={`/courses/${courseId}/sections/${sectionId}`}
            className="inline-flex items-center gap-1.5 text-white/80 hover:text-white text-sm mb-4 transition-colors"
          >
            <ArrowLeft size={16} />
            Back to Section
          </Link>

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="font-display text-2xl sm:text-3xl font-bold">
                {sectionTitle}
              </h1>
              <p className="text-white/80 text-sm mt-2">
                Mastery map and table view
              </p>
            </div>
            <button
              type="button"
              onClick={() => loadPageData(true)}
              disabled={refreshing}
              className="btn-secondary"
            >
              {refreshing ? (
                <RefreshCw size={16} className="animate-spin" />
              ) : (
                <RefreshCw size={16} />
              )}
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-5">
        {isLocked ? (
          <div className="card p-6 border border-amber-200 bg-amber-50">
            <div className="flex items-start gap-3">
              <Lock size={20} className="text-amber-600 mt-0.5" />
              <div>
                <h3 className="font-semibold text-amber-900">
                  Mastery view is locked
                </h3>
                <p className="text-sm text-amber-800 mt-1">
                  {masteryPayload?.lock_reason ||
                    "Complete section diagnostic to unlock mastery views."}
                </p>
                <p className="text-xs text-amber-800/90 mt-2">
                  Progress:{" "}
                  {masteryPayload?.state?.diagnostic_answered_count || 0}/
                  {masteryPayload?.state?.diagnostic_total_questions || 30}
                </p>
                <Link
                  to={`/courses/${courseId}/sections/${sectionId}`}
                  className="btn-primary mt-4 inline-flex"
                >
                  Go to Diagnostic
                </Link>
              </div>
            </div>
          </div>
        ) : (
          <MasteryExplorer
            rows={tableRows}
            edges={edgeRows}
            emptyMapText="No dependency graph data available for this section."
          />
        )}

        <Link
          to="/mastery"
          className="card p-4 border border-atlas-100 flex items-center gap-2 text-sm font-semibold text-atlas-700 hover:bg-atlas-50 transition-colors"
        >
          <Layers size={18} />
          See your mastery across every section you have diagnosed
        </Link>
      </div>
    </div>
  );
}
