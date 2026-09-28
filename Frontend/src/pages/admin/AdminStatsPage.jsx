import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { adminFetch } from './adminApi';
import {
  AlertCircle,
  ArrowLeft,
  Download,
  RefreshCw,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
  Users,
} from 'lucide-react';

const HISTOGRAM_ORDER = ['0-20', '20-40', '40-60', '60-80', '80-100'];
const HISTOGRAM_COLOR = ['#ef4444', '#f59e0b', '#eab308', '#84cc16', '#22c55e'];

function StatCard({ label, value, sub, icon: Icon }) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
        </div>
        {Icon && (
          <div className="p-2 rounded-lg bg-atlas-50 text-atlas-700">
            <Icon size={20} />
          </div>
        )}
      </div>
    </div>
  );
}

function SkillTable({ title, skills, icon: Icon, accent }) {
  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 mb-3">
        <Icon size={16} className={accent} />
        <h3 className="font-display font-semibold text-gray-900">{title}</h3>
      </div>
      {skills.length === 0 ? (
        <p className="text-sm text-gray-500">No mastery data yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-gray-500 border-b border-gray-200">
                <th className="pb-2 pr-3">Skill</th>
                <th className="pb-2 pr-3">Subject / Topic</th>
                <th className="pb-2 pr-3 text-right">Avg. mastery</th>
                <th className="pb-2 text-right">Students</th>
              </tr>
            </thead>
            <tbody>
              {skills.map((s) => (
                <tr key={s.skill_id} className="border-b border-gray-100 last:border-0">
                  <td className="py-2 pr-3">
                    <p className="text-gray-900">{s.skill_description}</p>
                    <p className="text-xs text-gray-400">{s.skill_id}</p>
                  </td>
                  <td className="py-2 pr-3 text-gray-600">
                    {s.subject}
                    <br />
                    <span className="text-xs text-gray-400">{s.topic_label}</span>
                  </td>
                  <td className="py-2 pr-3 text-right font-semibold text-gray-900">
                    {s.average_mastery.toFixed(1)}
                  </td>
                  <td className="py-2 text-right text-gray-600">{s.students_with_data}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function AdminStatsPage() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  const [authState, setAuthState] = useState('checking'); // checking | ok | forbidden
  const [overview, setOverview] = useState(null);
  const [overviewError, setOverviewError] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [exportingFormat, setExportingFormat] = useState(''); // '' | 'csv' | 'json'
  const [exportError, setExportError] = useState('');

  useEffect(() => {
    if (!loading && !user) {
      navigate('/login');
    }
  }, [loading, user, navigate]);

  const loadOverview = useCallback(async () => {
    if (!user) return;
    setOverviewError('');
    try {
      const response = await adminFetch('/admin/stats/overview', user.user_name);
      if (response.status === 403) {
        setAuthState('forbidden');
        return;
      }
      if (!response.ok) {
        throw new Error(`Request failed (${response.status})`);
      }
      const payload = await response.json();
      setOverview(payload);
      setAuthState('ok');
    } catch (error) {
      setOverviewError(error.message || 'Failed to load statistics');
    }
  }, [user]);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  async function handleRefresh() {
    setRefreshing(true);
    await loadOverview();
    setRefreshing(false);
  }

  async function handleExport(format) {
    if (!user) return;
    setExportError('');
    setExportingFormat(format);
    try {
      const response = await adminFetch(`/admin/stats/export?format=${format}`, user.user_name);
      if (!response.ok) {
        throw new Error(`Export failed (${response.status})`);
      }
      const blob = await response.blob();
      const disposition = response.headers.get('Content-Disposition') || '';
      const match = disposition.match(/filename="([^"]+)"/);
      const filename = match ? match[1] : `atlas_student_performance.${format}`;

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      setExportError(error.message || 'Export failed');
    } finally {
      setExportingFormat('');
    }
  }

  if (authState === 'forbidden') {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="card p-8 max-w-md text-center">
          <ShieldAlert size={40} className="mx-auto text-red-400 mb-4" />
          <h1 className="font-display text-xl font-bold text-gray-900 mb-2">Not authorized</h1>
          <p className="text-gray-500 text-sm">
            {user?.user_name} is not on the admin allow-list. Ask an existing admin to add your
            username to <code className="bg-gray-100 px-1 rounded">ADMIN_USERNAMES</code> in the backend.
          </p>
        </div>
      </div>
    );
  }

  const maxBucket = overview
    ? Math.max(1, ...HISTOGRAM_ORDER.map((k) => overview.mastery_distribution[k]))
    : 1;

  return (
    <div className="min-h-screen bg-atlas-50/50">
      <div className="bg-gradient-to-r from-atlas-700 via-atlas-800 to-atlas-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <h1 className="font-display text-2xl font-bold">Student Performance</h1>
              <p className="text-atlas-200 text-sm mt-1">
                Aggregate mastery statistics across every student, and a full export for offline analysis.
              </p>
            </div>
            <Link
              to="/admin/ontology"
              className="text-sm text-atlas-200 hover:text-white inline-flex items-center gap-1.5"
            >
              <ArrowLeft size={14} />
              Ontology Admin
            </Link>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        {overviewError && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 flex items-center gap-2">
            <AlertCircle size={16} />
            {overviewError}
          </div>
        )}

        {!overview && !overviewError && (
          <div className="card p-8 text-center text-gray-500">Loading statistics…</div>
        )}

        {overview && (
          <>
            <div className="flex items-center justify-between">
              <p className="text-xs text-gray-500">
                Generated {new Date(overview.generated_at).toLocaleString()}. Reflects the current mastery
                snapshot only — there is no historical per-question log (sessions are in-memory and reset on
                backend restart).
              </p>
              <button
                type="button"
                onClick={handleRefresh}
                disabled={refreshing}
                className="btn-secondary text-sm inline-flex items-center gap-1.5"
              >
                <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
                Refresh
              </button>
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                label="Total students"
                value={overview.total_students}
                sub={`${overview.students_with_mastery_data} with recorded mastery`}
                icon={Users}
              />
              <StatCard
                label="Overall average mastery"
                value={`${overview.overall_average_mastery.toFixed(1)}%`}
                sub={`${overview.total_mastery_rows} (student, skill) rows`}
              />
              <StatCard
                label="Skills in ontology"
                value={overview.total_skills_in_ontology}
                sub={`${overview.by_subject.length} subjects tracked`}
              />
              <StatCard
                label="Export"
                value=" "
                sub={null}
              />
            </div>

            {/* Export card, rendered as its own block so the two buttons have room */}
            <div className="card p-5">
              <h3 className="font-display font-semibold text-gray-900 mb-1">Export all student performance data</h3>
              <p className="text-sm text-gray-500 mb-3">
                One row per (student, skill) with mastery level, enriched with subject and topic — the
                complete dataset behind the summaries below, for use in a spreadsheet or a notebook.
              </p>
              {exportError && (
                <p className="text-sm text-red-600 mb-2 flex items-center gap-1.5">
                  <AlertCircle size={14} /> {exportError}
                </p>
              )}
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => handleExport('csv')}
                  disabled={exportingFormat !== ''}
                  className="btn-primary text-sm inline-flex items-center gap-1.5"
                >
                  <Download size={14} />
                  {exportingFormat === 'csv' ? 'Preparing…' : 'Download CSV'}
                </button>
                <button
                  type="button"
                  onClick={() => handleExport('json')}
                  disabled={exportingFormat !== ''}
                  className="btn-secondary text-sm inline-flex items-center gap-1.5"
                >
                  <Download size={14} />
                  {exportingFormat === 'json' ? 'Preparing…' : 'Download JSON'}
                </button>
              </div>
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
              <div className="card p-5">
                <h3 className="font-display font-semibold text-gray-900 mb-3">Average mastery by subject</h3>
                <div className="space-y-3">
                  {overview.by_subject.map((s) => (
                    <div key={s.subject}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="font-medium text-gray-700">{s.subject}</span>
                        <span className="text-gray-500">
                          {s.average_mastery.toFixed(1)}% avg · {s.students_with_data} students
                        </span>
                      </div>
                      <div className="h-2.5 rounded-full bg-gray-100 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-atlas-600"
                          style={{ width: `${Math.min(100, s.average_mastery)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="card p-5">
                <h3 className="font-display font-semibold text-gray-900 mb-3">
                  Mastery distribution across all (student, skill) rows
                </h3>
                <div className="flex items-end gap-3 h-40">
                  {HISTOGRAM_ORDER.map((bucket, i) => {
                    const count = overview.mastery_distribution[bucket];
                    const heightPct = (count / maxBucket) * 100;
                    return (
                      <div key={bucket} className="flex-1 flex flex-col items-center justify-end h-full">
                        <span className="text-xs text-gray-500 mb-1">{count}</span>
                        <div
                          className="w-full rounded-t-md"
                          style={{
                            height: `${Math.max(4, heightPct)}%`,
                            backgroundColor: HISTOGRAM_COLOR[i],
                          }}
                        />
                        <span className="text-xs text-gray-400 mt-1">{bucket}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
              <SkillTable
                title="Weakest skills cohort-wide"
                skills={overview.weakest_skills}
                icon={TrendingDown}
                accent="text-red-500"
              />
              <SkillTable
                title="Strongest skills cohort-wide"
                skills={overview.strongest_skills}
                icon={TrendingUp}
                accent="text-emerald-500"
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
