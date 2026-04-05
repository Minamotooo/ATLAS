import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { useAuth, buildApiUrl } from '../context/AuthContext';
import {
  AlertCircle,
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  GitBranch,
  Lock,
  RefreshCw,
  Table2,
} from 'lucide-react';

function masteryColor(mastery) {
  if (mastery >= 95) {
    return 'bg-emerald-500';
  }
  if (mastery >= 70) {
    return 'bg-atlas-500';
  }
  if (mastery >= 40) {
    return 'bg-amber-500';
  }
  return 'bg-gray-400';
}

export default function SectionMasteryPage() {
  const { courseId, sectionId } = useParams();
  const { lang } = useLanguage();
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  const [sectionMeta, setSectionMeta] = useState(null);
  const [masteryPayload, setMasteryPayload] = useState(null);
  const [pageLoading, setPageLoading] = useState(true);
  const [pageError, setPageError] = useState('');
  const [viewMode, setViewMode] = useState('table');
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      navigate('/login');
    }
  }, [loading, user, navigate]);

  async function loadPageData(silent = false) {
    if (!user) {
      return;
    }

    if (silent) {
      setRefreshing(true);
      setPageError('');
    } else {
      setPageLoading(true);
      setPageError('');
    }

    try {
      const [catalogResponse, masteryResponse] = await Promise.all([
        fetch(buildApiUrl('/catalog')),
        fetch(buildApiUrl(`/users/${encodeURIComponent(user.user_id)}/sections/${encodeURIComponent(sectionId)}/mastery`)),
      ]);

      if (!catalogResponse.ok) {
        throw new Error(`Catalog request failed (${catalogResponse.status})`);
      }
      if (!masteryResponse.ok) {
        let detail = `Mastery request failed (${masteryResponse.status})`;
        try {
          const errorPayload = await masteryResponse.json();
          if (typeof errorPayload?.detail === 'string' && errorPayload.detail.trim()) {
            detail = errorPayload.detail;
          }
        } catch {
          // Ignore parse failures and keep HTTP status-based message.
        }
        throw new Error(detail);
      }

      const catalogPayload = await catalogResponse.json();
      const masteryData = await masteryResponse.json();

      const courses = Array.isArray(catalogPayload?.courses) ? catalogPayload.courses : [];
      const course = courses.find((item) => item.id === courseId) || null;
      const section = course?.sections?.find((item) => item.id === sectionId) || null;

      setSectionMeta(section);
      setMasteryPayload(masteryData);
    } catch (error) {
      setPageError(error.message || 'Failed to load section mastery');
      setMasteryPayload(null);
    } finally {
      setPageLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadPageData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId, sectionId, user]);

  const sectionTitle = useMemo(() => {
    if (!sectionMeta) {
      return sectionId;
    }
    return lang === 'bn' && sectionMeta.title_bn ? sectionMeta.title_bn : sectionMeta.title;
  }, [sectionMeta, lang, sectionId]);

  const tableRows = useMemo(() => {
    const rows = Array.isArray(masteryPayload?.table) ? masteryPayload.table : [];
    return [...rows].sort((a, b) => b.mastery - a.mastery);
  }, [masteryPayload]);

  const edgeRows = useMemo(() => {
    const edges = masteryPayload?.map?.edges;
    return Array.isArray(edges) ? edges : [];
  }, [masteryPayload]);

  const summary = useMemo(() => {
    const totalSkills = tableRows.length;
    const average = totalSkills > 0
      ? Math.round(tableRows.reduce((sum, row) => sum + row.mastery, 0) / totalSkills)
      : 0;
    const mastered = tableRows.filter((row) => row.mastery >= 95).length;

    return {
      totalSkills,
      average,
      mastered,
    };
  }, [tableRows]);

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
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Could not load mastery</h2>
          <p className="text-gray-600 mb-6">{pageError}</p>
          <div className="flex flex-wrap justify-center gap-3">
            <button type="button" onClick={() => loadPageData()} className="btn-primary">
              <RefreshCw size={16} />
              Retry
            </button>
            <Link to={`/courses/${courseId}/sections/${sectionId}`} className="btn-secondary">
              <ArrowLeft size={16} />
              Back to Section
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const isLocked = !!masteryPayload?.locked;

  return (
    <div className="min-h-screen bg-atlas-50/50">
      <div className="bg-gradient-to-r from-atlas-700 via-atlas-800 to-atlas-900 text-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
          <Link to={`/courses/${courseId}/sections/${sectionId}`} className="inline-flex items-center gap-1.5 text-white/80 hover:text-white text-sm mb-4 transition-colors">
            <ArrowLeft size={16} />
            Back to Section
          </Link>

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="font-display text-2xl sm:text-3xl font-bold">{sectionTitle}</h1>
              <p className="text-white/80 text-sm mt-2">Mastery map and table view</p>
            </div>
            <button type="button" onClick={() => loadPageData(true)} disabled={refreshing} className="btn-secondary">
              {refreshing ? <RefreshCw size={16} className="animate-spin" /> : <RefreshCw size={16} />}
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
                <h3 className="font-semibold text-amber-900">Mastery view is locked</h3>
                <p className="text-sm text-amber-800 mt-1">{masteryPayload?.lock_reason || 'Complete section diagnostic to unlock mastery views.'}</p>
                <p className="text-xs text-amber-800/90 mt-2">
                  Progress: {masteryPayload?.state?.diagnostic_answered_count || 0}/{masteryPayload?.state?.diagnostic_total_questions || 30}
                </p>
                <Link to={`/courses/${courseId}/sections/${sectionId}`} className="btn-primary mt-4 inline-flex">
                  Go to Diagnostic
                </Link>
              </div>
            </div>
          </div>
        ) : (
          <>
            <div className="grid sm:grid-cols-3 gap-4">
              <div className="card p-4 border border-atlas-100">
                <div className="text-xs text-gray-500 uppercase tracking-wide">Tracked Skills</div>
                <div className="text-2xl font-bold text-gray-900 mt-1">{summary.totalSkills}</div>
              </div>
              <div className="card p-4 border border-atlas-100">
                <div className="text-xs text-gray-500 uppercase tracking-wide">Average Mastery</div>
                <div className="text-2xl font-bold text-gray-900 mt-1">{summary.average}%</div>
              </div>
              <div className="card p-4 border border-atlas-100">
                <div className="text-xs text-gray-500 uppercase tracking-wide">Mastered (95%+)</div>
                <div className="text-2xl font-bold text-gray-900 mt-1">{summary.mastered}</div>
              </div>
            </div>

            <div className="card p-3">
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setViewMode('table')}
                  className={`inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm font-semibold transition-all ${
                    viewMode === 'table' ? 'bg-atlas-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <Table2 size={15} />
                  Mastery Table
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('map')}
                  className={`inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm font-semibold transition-all ${
                    viewMode === 'map' ? 'bg-atlas-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <GitBranch size={15} />
                  Dependency Map
                </button>
              </div>
            </div>

            {viewMode === 'table' && (
              <div className="card overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[880px]">
                    <thead>
                      <tr className="bg-gray-50 border-b border-gray-200 text-left text-xs uppercase tracking-wide text-gray-500">
                        <th className="px-4 py-3">Skill</th>
                        <th className="px-4 py-3">Description</th>
                        <th className="px-4 py-3">Topics</th>
                        <th className="px-4 py-3">Mastery</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tableRows.map((row) => (
                        <tr key={row.skill_id} className="border-b last:border-b-0 border-gray-100">
                          <td className="px-4 py-3 font-semibold text-gray-900">{row.skill_id}</td>
                          <td className="px-4 py-3 text-sm text-gray-700">{row.skill_description || '-'}</td>
                          <td className="px-4 py-3">
                            <div className="flex flex-wrap gap-1.5">
                              {(row.topics || []).map((topic) => (
                                <span key={`${row.skill_id}-${topic}`} className="rounded-full bg-atlas-50 border border-atlas-100 px-2 py-0.5 text-xs text-atlas-700">
                                  {topic}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-semibold text-gray-800 w-12">{Math.round(row.mastery)}%</span>
                              <div className="h-2 w-32 rounded-full bg-gray-100 overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${masteryColor(row.mastery)}`}
                                  style={{ width: `${Math.max(0, Math.min(100, row.mastery))}%` }}
                                />
                              </div>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {viewMode === 'map' && (
              <div className="grid lg:grid-cols-3 gap-4">
                <div className="lg:col-span-2 card p-4">
                  <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                    <BarChart3 size={16} />
                    Skill Nodes
                  </h3>
                  <div className="grid sm:grid-cols-2 gap-3 max-h-[520px] overflow-y-auto pr-1">
                    {tableRows.map((row) => (
                      <div key={`node-${row.skill_id}`} className="rounded-xl border border-gray-200 p-3 bg-white">
                        <div className="flex items-center justify-between gap-3 mb-2">
                          <span className="font-semibold text-gray-900 text-sm">{row.skill_id}</span>
                          <span className={`text-xs px-2 py-0.5 rounded-full text-white ${masteryColor(row.mastery)}`}>
                            {Math.round(row.mastery)}%
                          </span>
                        </div>
                        <p className="text-xs text-gray-600 line-clamp-3">{row.skill_description || '-'}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="card p-4">
                  <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                    <GitBranch size={16} />
                    Directed Edges
                  </h3>
                  <p className="text-xs text-gray-500 mb-3">{edgeRows.length} prerequisite relations in this section.</p>
                  <div className="max-h-[520px] overflow-y-auto space-y-2 pr-1">
                    {edgeRows.map((edge, idx) => (
                      <div key={`edge-${idx}-${edge.source}-${edge.target}`} className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-700">
                        <span className="font-semibold text-gray-900">{edge.source}</span>
                        <span className="mx-1 text-gray-400">→</span>
                        <span className="font-semibold text-gray-900">{edge.target}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {!isLocked && (
          <div className="card p-4 border border-emerald-200 bg-emerald-50 text-emerald-900 flex items-center gap-2">
            <CheckCircle2 size={18} />
            Mastery view is unlocked and synced with current backend state.
          </div>
        )}
      </div>
    </div>
  );
}
