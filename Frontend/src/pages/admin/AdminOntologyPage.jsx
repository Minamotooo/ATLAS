import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';
import { useAuth } from '../../context/AuthContext';
import { adminFetch } from './adminApi';
import { AlertCircle, ChevronDown, Plus, Search, ShieldAlert, Trash2, X } from 'lucide-react';

cytoscape.use(dagre);

const BLOOM_LEVELS = ['Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create'];

// Same palette as Ontology/viz/build_dag_viewer.py, for visual continuity.
const ROLE_COLOR = {
  root: '#3987e5',
  intermediate: '#d95926',
  leaf: '#199e70',
  isolated: '#5b5b55',
};

export default function AdminOntologyPage() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  const [authState, setAuthState] = useState('checking'); // checking | ok | forbidden
  const [meta, setMeta] = useState(null);
  const [metaError, setMetaError] = useState('');

  const [subject, setSubject] = useState('');
  const [selectedTopics, setSelectedTopics] = useState([]);
  const [search, setSearch] = useState('');
  const [bloom, setBloom] = useState('');
  const [includeIsolated, setIncludeIsolated] = useState(true);

  const [graph, setGraph] = useState(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphError, setGraphError] = useState('');

  const [topicGraph, setTopicGraph] = useState(null);
  const [topicGraphLoading, setTopicGraphLoading] = useState(false);
  const [topicGraphError, setTopicGraphError] = useState('');

  // 'empty' (no subject yet), 'topics' (subject-level overview, the default
  // once a subject is picked), or 'skills' (one or more topics chosen, or a
  // free-text search across the subject).
  const viewMode = !subject ? 'empty' : (selectedTopics.length > 0 || search.trim()) ? 'skills' : 'topics';

  const [selectedNode, setSelectedNode] = useState(null);
  const [showAddSkill, setShowAddSkill] = useState(false);
  const [showAddTopic, setShowAddTopic] = useState(false);
  const [showAddEdge, setShowAddEdge] = useState(false);
  const [showRenameTopic, setShowRenameTopic] = useState(false);
  const [actionError, setActionError] = useState('');

  const cyRef = useRef(null);
  const cyContainerRef = useRef(null);

  useEffect(() => {
    if (!loading && !user) {
      navigate('/login');
    }
  }, [user, loading, navigate]);

  const loadMeta = useCallback(async () => {
    if (!user) return;
    setMetaError('');
    try {
      const response = await adminFetch('/admin/ontology/meta', user.user_name);
      if (response.status === 403) {
        setAuthState('forbidden');
        return;
      }
      if (!response.ok) {
        throw new Error(`Request failed (${response.status})`);
      }
      const payload = await response.json();
      setMeta(payload);
      setAuthState('ok');
    } catch (error) {
      setMetaError(error.message || 'Failed to load ontology metadata');
    }
  }, [user]);

  useEffect(() => {
    loadMeta();
  }, [loadMeta]);

  const loadTopicGraph = useCallback(async () => {
    if (!user || authState !== 'ok' || !subject) {
      setTopicGraph(null);
      return;
    }
    setTopicGraphLoading(true);
    setTopicGraphError('');
    try {
      const response = await adminFetch(`/admin/ontology/topic-graph?subject=${encodeURIComponent(subject)}`, user.user_name);
      if (!response.ok) throw new Error(`Request failed (${response.status})`);
      setTopicGraph(await response.json());
    } catch (error) {
      setTopicGraphError(error.message || 'Failed to load topic overview');
      setTopicGraph(null);
    } finally {
      setTopicGraphLoading(false);
    }
  }, [user, authState, subject]);

  useEffect(() => {
    if (viewMode === 'topics') loadTopicGraph();
  }, [viewMode, loadTopicGraph]);

  const loadGraph = useCallback(async () => {
    if (!user || authState !== 'ok') return;
    if (viewMode !== 'skills') {
      setGraph(null);
      return;
    }
    setGraphLoading(true);
    setGraphError('');
    try {
      const params = new URLSearchParams({ subject, include_isolated: String(includeIsolated) });
      if (selectedTopics.length > 0) params.set('topics', selectedTopics.join(','));
      if (search.trim()) params.set('search', search.trim());
      if (bloom) params.set('bloom', bloom);
      const response = await adminFetch(`/admin/ontology/graph?${params.toString()}`, user.user_name);
      if (!response.ok) throw new Error(`Request failed (${response.status})`);
      const payload = await response.json();
      setGraph(payload);
    } catch (error) {
      setGraphError(error.message || 'Failed to load ontology subset');
      setGraph(null);
    } finally {
      setGraphLoading(false);
    }
  }, [user, authState, viewMode, subject, selectedTopics, search, bloom, includeIsolated]);

  useEffect(() => {
    const handle = setTimeout(loadGraph, 250);
    return () => clearTimeout(handle);
  }, [loadGraph]);

  const topicsForSubject = useMemo(
    () => (meta?.topics || []).filter((t) => t.subject === subject),
    [meta, subject],
  );

  // Render whichever dataset is active. 'topics' shows one node per topic
  // (the default once a subject is picked, so we never lay out an entire
  // subject's skills at once); 'skills' shows one topic's DAG plus any
  // cross-topic neighbor skills, dimmed, for orientation.
  useEffect(() => {
    if (!cyContainerRef.current) return;

    const isTopics = viewMode === 'topics';
    const dataset = isTopics ? topicGraph : graph;
    const items = isTopics ? dataset?.topics : dataset?.nodes;
    if (!dataset || !items || items.length === 0) {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
      return;
    }

    const elements = isTopics
      ? [
          ...topicGraph.topics.map((t) => ({
            data: {
              id: t.topic_key,
              label: t.topic_label,
              size: Math.min(76, 26 + Math.sqrt(t.skill_count) * 6),
            },
          })),
          ...topicGraph.edges.map((e) => ({
            data: {
              id: `${e.from}__${e.to}`,
              source: e.from,
              target: e.to,
              width: Math.min(6, 1 + e.weight / 3),
            },
          })),
        ]
      : [
          ...graph.nodes.map((n) => ({
            data: {
              id: n.id,
              label: n.id,
              color: ROLE_COLOR[n.role] || ROLE_COLOR.isolated,
              role: n.role,
              external: !!n.external,
            },
          })),
          ...graph.edges.map((e) => ({ data: { id: `${e.from}__${e.to}`, source: e.from, target: e.to } })),
        ];

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const cy = cytoscape({
      container: cyContainerRef.current,
      elements,
      style: isTopics
        ? [
            {
              selector: 'node',
              style: {
                'background-color': '#4f46e5',
                label: 'data(label)',
                color: '#1f2937',
                'font-size': 10,
                'text-valign': 'bottom',
                'text-margin-y': 4,
                'text-wrap': 'wrap',
                'text-max-width': 90,
                width: 'data(size)',
                height: 'data(size)',
                'border-width': 2,
                'border-color': '#ffffff',
              },
            },
            {
              selector: 'edge',
              style: {
                width: 'data(width)',
                'line-color': '#c7d2fe',
                'target-arrow-color': '#c7d2fe',
                'target-arrow-shape': 'triangle',
                'curve-style': 'bezier',
              },
            },
          ]
        : [
            {
              selector: 'node',
              style: {
                'background-color': 'data(color)',
                label: 'data(label)',
                color: '#1f2937',
                'font-size': 9,
                'text-valign': 'bottom',
                'text-margin-y': 4,
                width: 22,
                height: 22,
                'border-width': 2,
                'border-color': '#ffffff',
              },
            },
            {
              selector: 'node[?external]',
              style: {
                opacity: 0.4,
                'border-width': 2,
                'border-style': 'dashed',
                'border-color': '#9ca3af',
              },
            },
            {
              selector: 'node:selected',
              style: { 'border-color': '#111827', 'border-width': 3, opacity: 1 },
            },
            {
              selector: 'edge',
              style: {
                width: 1.5,
                'line-color': '#c7ccd4',
                'target-arrow-color': '#c7ccd4',
                'target-arrow-shape': 'triangle',
                'curve-style': 'bezier',
              },
            },
          ],
      layout: { name: 'dagre', rankDir: 'TB', nodeSep: isTopics ? 30 : 18, rankSep: isTopics ? 70 : 55, fit: true, padding: 30 },
      wheelSensitivity: 0.2,
    });
    // The container's final height can settle after this runs, so re-fit
    // against the resized viewport instead of trusting the initial layout fit.
    cy.resize();
    cy.fit(cy.elements(), 40);
    cy.center();

    if (isTopics) {
      cy.on('tap', 'node', (evt) => setSelectedTopics([evt.target.id()]));
    } else {
      cy.on('tap', 'node', (evt) => {
        const nodeData = graph.nodes.find((n) => n.id === evt.target.id());
        setSelectedNode(nodeData || null);
      });
      cy.on('tap', (evt) => {
        if (evt.target === cy) setSelectedNode(null);
      });
    }

    cyRef.current = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [viewMode, graph, topicGraph]);

  const selectedNodePrereqs = useMemo(() => {
    if (!selectedNode || !graph) return [];
    return graph.edges.filter((e) => e.to === selectedNode.id).map((e) => e.from);
  }, [selectedNode, graph]);
  const selectedNodeDependents = useMemo(() => {
    if (!selectedNode || !graph) return [];
    return graph.edges.filter((e) => e.from === selectedNode.id).map((e) => e.to);
  }, [selectedNode, graph]);

  async function refreshAfterMutation() {
    setActionError('');
    await Promise.all([loadMeta(), loadGraph(), loadTopicGraph()]);
  }

  async function handleDeleteSkill(skillId, force = false) {
    setActionError('');
    const response = await adminFetch(`/admin/ontology/skills/${encodeURIComponent(skillId)}${force ? '?force=true' : ''}`, user.user_name, {
      method: 'DELETE',
    });
    if (response.status === 409 && !force) {
      const body = await response.json().catch(() => ({}));
      if (window.confirm(`${body.detail || 'This skill has dependents.'} Delete anyway and remove those edges?`)) {
        return handleDeleteSkill(skillId, true);
      }
      return;
    }
    if (!response.ok && response.status !== 204) {
      const body = await response.json().catch(() => ({}));
      setActionError(body.detail || `Delete failed (${response.status})`);
      return;
    }
    setSelectedNode(null);
    await refreshAfterMutation();
  }

  async function handleRemoveEdge(fromId, toId) {
    setActionError('');
    const response = await adminFetch('/admin/ontology/edges', user.user_name, {
      method: 'DELETE',
      body: JSON.stringify({ from_id: fromId, to_id: toId }),
    });
    if (!response.ok && response.status !== 204) {
      const body = await response.json().catch(() => ({}));
      setActionError(body.detail || `Failed to remove edge (${response.status})`);
      return;
    }
    await refreshAfterMutation();
  }

  if (loading || authState === 'checking') {
    return <div className="min-h-screen flex items-center justify-center text-gray-500">Loading admin panel...</div>;
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

  return (
    <div className="min-h-screen bg-atlas-50/50">
      <div className="bg-gradient-to-r from-atlas-700 via-atlas-800 to-atlas-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
          <h1 className="font-display text-2xl font-bold">Ontology Admin</h1>
          <p className="text-atlas-200 text-sm mt-1">
            Full-corpus rebuild dataset ({meta?.total_skills ?? '...'} skills, {meta?.total_edges ?? '...'} edges).
            Editing here does not change what students currently see.
          </p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 grid lg:grid-cols-[1fr_320px] gap-4">
        <div>
          {metaError && (
            <div className="card p-4 mb-4 border border-red-200 bg-red-50 text-red-700 flex items-start gap-2">
              <AlertCircle size={18} className="mt-0.5" />
              <p className="text-sm">{metaError}</p>
            </div>
          )}

          {/* Filter bar */}
          <div className="card p-4 mb-4 flex flex-wrap items-center gap-3 overflow-visible relative z-30">
            <select
              className="input-field w-auto"
              value={subject}
              onChange={(e) => {
                setSubject(e.target.value);
                setSelectedTopics([]);
                setSelectedNode(null);
              }}
            >
              <option value="">Choose a subject...</option>
              {(meta?.subjects || []).map((s) => (
                <option key={s.subject} value={s.subject}>
                  {s.subject} ({s.skill_count})
                </option>
              ))}
            </select>

            <TopicMultiSelect
              topics={topicsForSubject}
              selected={selectedTopics}
              disabled={!subject}
              onChange={setSelectedTopics}
            />

            {selectedTopics.length > 0 && (
              <button
                className="text-sm font-semibold text-atlas-600 hover:text-atlas-800"
                onClick={() => { setSelectedTopics([]); setSearch(''); setSelectedNode(null); }}
              >
                ← back to topics
              </button>
            )}

            <select className="input-field w-auto" value={bloom} onChange={(e) => setBloom(e.target.value)} disabled={viewMode !== 'skills'}>
              <option value="">All Bloom levels</option>
              {BLOOM_LEVELS.map((b) => (
                <option key={b} value={b}>{b}</option>
              ))}
            </select>

            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                className="input-field pl-9 w-56"
                placeholder="Search skill id / text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

            <label className={`flex items-center gap-2 text-sm ${viewMode === 'skills' ? 'text-gray-600' : 'text-gray-300'}`}>
              <input
                type="checkbox"
                checked={includeIsolated}
                disabled={viewMode !== 'skills'}
                onChange={(e) => setIncludeIsolated(e.target.checked)}
              />
              Show isolated skills
            </label>

            <div className="ml-auto flex gap-2">
              <button className="btn-secondary" disabled={selectedTopics.length !== 1} onClick={() => setShowRenameTopic(true)}>
                Edit topic
              </button>
              <button className="btn-secondary" disabled={!subject} onClick={() => setShowAddTopic(true)}>
                <Plus size={16} /> Add topic
              </button>
              <button className="btn-primary" disabled={!subject} onClick={() => setShowAddSkill(true)}>
                <Plus size={16} /> Add skill
              </button>
            </div>
          </div>

          {/* Graph / empty states */}
          {viewMode === 'empty' ? (
            <div className="card p-12 text-center text-gray-500">
              Pick a subject above to get a topic-level overview first — drill into a topic
              (or search) to see individual skills. The full skill graph is never rendered at once.
            </div>
          ) : viewMode === 'topics' ? (
            topicGraphError ? (
              <div className="card p-6 text-center text-red-600">{topicGraphError}</div>
            ) : topicGraphLoading ? (
              <div className="card p-12 text-center text-gray-500">Loading topic overview...</div>
            ) : !topicGraph || topicGraph.topics.length === 0 ? (
              <div className="card p-12 text-center text-gray-500">This subject has no topics yet.</div>
            ) : (
              <div className="card p-2">
                <div className="px-2 py-1 text-xs text-gray-400">
                  {topicGraph.topics.length} topic(s) in {subject} · click a topic to drill in
                </div>
                <div ref={cyContainerRef} style={{ width: '100%', height: 'min(65vh, 560px)' }} />
              </div>
            )
          ) : graphError ? (
            <div className="card p-6 text-center text-red-600">{graphError}</div>
          ) : graphLoading ? (
            <div className="card p-12 text-center text-gray-500">Loading subset...</div>
          ) : !graph || graph.nodes.length === 0 ? (
            <div className="card p-12 text-center text-gray-500">No skills match these filters.</div>
          ) : (
            <div className="card p-2">
              <div className="px-2 py-1 text-xs text-gray-400">
                {graph.core_count} skill(s)
                {selectedTopics.length > 1 ? ` across ${selectedTopics.length} selected topics` : ''}
                {graph.count > graph.core_count && ` · ${graph.count - graph.core_count} shown faded as cross-topic context`}
              </div>
              <div ref={cyContainerRef} style={{ width: '100%', height: 'min(65vh, 560px)' }} />
            </div>
          )}
        </div>

        {/* Side panel */}
        <div className="card p-4 h-fit sticky top-4">
          {actionError && (
            <div className="mb-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-2">{actionError}</div>
          )}
          {selectedNode ? (
            <div>
              <div className="flex items-start justify-between gap-2 mb-2">
                <h3 className="font-mono text-sm font-semibold text-atlas-700 break-all">{selectedNode.id}</h3>
                <button onClick={() => setSelectedNode(null)} className="text-gray-400 hover:text-gray-600">
                  <X size={16} />
                </button>
              </div>
              {selectedNode.external && (
                <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-2 mb-2">
                  Cross-topic context — this skill belongs to <b>{selectedNode.topic_label}</b>, shown
                  because it connects to one of the selected topics.
                </div>
              )}
              <p className="text-sm text-gray-700 mb-3">{selectedNode.label}</p>
              <div className="text-xs text-gray-500 mb-3 space-y-1">
                <div><b>Topic:</b> {selectedNode.topic_label}</div>
                <div><b>Subject:</b> {selectedNode.subject}</div>
                <div><b>Bloom:</b> {selectedNode.bloom}</div>
                <div><b>Role:</b> {selectedNode.role}</div>
              </div>

              <div className="mb-3">
                <div className="text-xs font-semibold text-gray-600 mb-1">Prerequisites ({selectedNodePrereqs.length})</div>
                {selectedNodePrereqs.length === 0 && <div className="text-xs text-gray-400">None in this view</div>}
                {selectedNodePrereqs.map((pid) => (
                  <div key={pid} className="flex items-center justify-between text-xs font-mono bg-gray-50 rounded px-2 py-1 mb-1">
                    <span className="truncate">{pid}</span>
                    <button onClick={() => handleRemoveEdge(pid, selectedNode.id)} className="text-red-400 hover:text-red-600 shrink-0 ml-2">
                      <X size={12} />
                    </button>
                  </div>
                ))}
                <button
                  className="text-xs text-atlas-600 hover:text-atlas-800 font-semibold mt-1"
                  onClick={() => setShowAddEdge(true)}
                >
                  + add prerequisite
                </button>
              </div>

              <div className="mb-4">
                <div className="text-xs font-semibold text-gray-600 mb-1">Dependents ({selectedNodeDependents.length})</div>
                {selectedNodeDependents.length === 0 && <div className="text-xs text-gray-400">None in this view</div>}
                {selectedNodeDependents.map((cid) => (
                  <div key={cid} className="text-xs font-mono bg-gray-50 rounded px-2 py-1 mb-1 truncate">{cid}</div>
                ))}
              </div>

              <button
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-semibold text-red-600 border-2 border-red-200 rounded-xl hover:bg-red-50"
                onClick={() => handleDeleteSkill(selectedNode.id)}
              >
                <Trash2 size={14} /> Delete skill
              </button>
            </div>
          ) : (
            <div className="text-sm text-gray-400 text-center py-8">
              Click a node in the graph to see its details, edit prerequisites, or delete it.
            </div>
          )}
        </div>
      </div>

      {showAddSkill && (
        <AddSkillModal
          meta={meta}
          defaultSubject={subject}
          defaultTopic={selectedTopics.length === 1 ? selectedTopics[0] : ''}
          username={user.user_name}
          onClose={() => setShowAddSkill(false)}
          onCreated={async () => {
            setShowAddSkill(false);
            await refreshAfterMutation();
          }}
        />
      )}

      {showAddTopic && (
        <AddTopicModal
          existingTopicKeys={topicsForSubject.map((t) => t.topic_key)}
          subject={subject}
          username={user.user_name}
          onClose={() => setShowAddTopic(false)}
          onCreated={async (newTopicKey) => {
            setShowAddTopic(false);
            setSelectedTopics([newTopicKey]);
            await refreshAfterMutation();
          }}
        />
      )}

      {showAddEdge && selectedNode && (
        <AddEdgeModal
          username={user.user_name}
          targetSkill={selectedNode}
          onClose={() => setShowAddEdge(false)}
          onCreated={async () => {
            setShowAddEdge(false);
            await refreshAfterMutation();
          }}
        />
      )}

      {showRenameTopic && selectedTopics.length === 1 && (
        <RenameTopicModal
          username={user.user_name}
          topicKey={selectedTopics[0]}
          currentTopic={topicsForSubject.find((t) => t.topic_key === selectedTopics[0])}
          onClose={() => setShowRenameTopic(false)}
          onSaved={async () => {
            setShowRenameTopic(false);
            await refreshAfterMutation();
          }}
        />
      )}
    </div>
  );
}

function TopicMultiSelect({ topics, selected, disabled, onChange }) {
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState('');
  const containerRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (disabled) setOpen(false);
  }, [disabled]);

  const visibleTopics = topics.filter((t) =>
    t.topic_label.toLowerCase().includes(filter.toLowerCase()) || t.topic_key.toLowerCase().includes(filter.toLowerCase()),
  );

  function toggle(topicKey) {
    onChange(selected.includes(topicKey) ? selected.filter((k) => k !== topicKey) : [...selected, topicKey]);
  }

  const label = selected.length === 0
    ? 'Topic overview (select to drill in)'
    : selected.length === 1
    ? topics.find((t) => t.topic_key === selected[0])?.topic_label || selected[0]
    : `${selected.length} topics selected`;

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        className="input-field w-64 flex items-center justify-between text-left disabled:opacity-50"
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="truncate">{label}</span>
        <ChevronDown size={16} className="shrink-0 ml-2 text-gray-400" />
      </button>

      {open && (
        <div className="absolute z-40 mt-1 w-80 bg-white border border-gray-200 rounded-xl shadow-lg p-2">
          <div className="flex items-center gap-2 mb-2">
            <input
              className="input-field py-1.5 text-sm flex-1"
              placeholder="Filter topics..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              autoFocus
            />
            {selected.length > 0 && (
              <button type="button" className="text-xs text-atlas-600 hover:text-atlas-800 font-semibold shrink-0" onClick={() => onChange([])}>
                Clear
              </button>
            )}
          </div>
          <div className="max-h-64 overflow-y-auto">
            {visibleTopics.length === 0 && <div className="text-xs text-gray-400 px-2 py-2">No topics match.</div>}
            {visibleTopics.map((t) => (
              <label key={t.topic_key} className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-50 cursor-pointer text-sm">
                <input type="checkbox" checked={selected.includes(t.topic_key)} onChange={() => toggle(t.topic_key)} />
                <span className="flex-1 truncate">{t.topic_label}</span>
                <span className="text-xs text-gray-400 shrink-0">{t.skill_count}</span>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ModalShell({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-lg p-6 max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-display text-lg font-bold text-gray-900">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function AddSkillModal({ meta, defaultSubject, defaultTopic, username, onClose, onCreated }) {
  const [skillId, setSkillId] = useState('');
  const [skillFull, setSkillFull] = useState('');
  const [subject, setSubject] = useState(defaultSubject || '');
  const [useNewTopic, setUseNewTopic] = useState(!defaultTopic);
  const [topicKey, setTopicKey] = useState(defaultTopic || '');
  const [topicLabel, setTopicLabel] = useState('');
  const [bloom, setBloom] = useState('Remember');
  const [prereqInput, setPrereqInput] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const topicsForSubject = (meta?.topics || []).filter((t) => t.subject === subject);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    if (!skillId.trim() || !skillFull.trim() || !subject || !topicKey.trim()) {
      setError('Skill id, description, subject, and topic are required.');
      return;
    }
    setSubmitting(true);
    try {
      const response = await adminFetch('/admin/ontology/skills', username, {
        method: 'POST',
        body: JSON.stringify({
          skill_id: skillId.trim(),
          skill_full: skillFull.trim(),
          topic_key: topicKey.trim(),
          topic_label: (useNewTopic ? topicLabel.trim() : topicsForSubject.find((t) => t.topic_key === topicKey)?.topic_label) || topicKey.trim(),
          subject,
          bloom,
          prerequisite_ids: prereqInput.split(',').map((s) => s.trim()).filter(Boolean),
        }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed (${response.status})`);
      }
      onCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <ModalShell title="Add skill" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-3">
        {error && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-2">{error}</div>}
        <div>
          <label className="text-xs font-semibold text-gray-600">Skill ID</label>
          <input className="input-field" value={skillId} onChange={(e) => setSkillId(e.target.value)} placeholder="e.g. CHE1_NEW_SKILL0" />
        </div>
        <div>
          <label className="text-xs font-semibold text-gray-600">Description</label>
          <textarea className="input-field" rows={3} value={skillFull} onChange={(e) => setSkillFull(e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-semibold text-gray-600">Subject</label>
            <select className="input-field" value={subject} onChange={(e) => { setSubject(e.target.value); setTopicKey(''); }}>
              <option value="">Choose...</option>
              {(meta?.subjects || []).map((s) => (
                <option key={s.subject} value={s.subject}>{s.subject}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-600">Bloom level</label>
            <select className="input-field" value={bloom} onChange={(e) => setBloom(e.target.value)}>
              {BLOOM_LEVELS.map((b) => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>
        </div>

        <div>
          <label className="flex items-center gap-2 text-xs font-semibold text-gray-600 mb-1">
            <input type="checkbox" checked={useNewTopic} onChange={(e) => setUseNewTopic(e.target.checked)} />
            Create a new topic
          </label>
          {useNewTopic ? (
            <div className="grid grid-cols-2 gap-3">
              <input className="input-field" placeholder="Topic key (e.g. CHE1_NEW_TOPIC)" value={topicKey} onChange={(e) => setTopicKey(e.target.value)} />
              <input className="input-field" placeholder="Topic label" value={topicLabel} onChange={(e) => setTopicLabel(e.target.value)} />
            </div>
          ) : (
            <select className="input-field" value={topicKey} onChange={(e) => setTopicKey(e.target.value)} disabled={!subject}>
              <option value="">Choose a topic...</option>
              {topicsForSubject.map((t) => (
                <option key={t.topic_key} value={t.topic_key}>{t.topic_label}</option>
              ))}
            </select>
          )}
        </div>

        <div>
          <label className="text-xs font-semibold text-gray-600">Prerequisite skill IDs (comma separated, optional)</label>
          <input className="input-field" value={prereqInput} onChange={(e) => setPrereqInput(e.target.value)} placeholder="CHE1_IONIC_BOND0, CHE1_COVALENT_BOND0" />
        </div>

        <button className="btn-primary w-full" type="submit" disabled={submitting}>
          {submitting ? 'Creating...' : 'Create skill'}
        </button>
      </form>
    </ModalShell>
  );
}

function AddTopicModal({ existingTopicKeys, subject, username, onClose, onCreated }) {
  const [topicKey, setTopicKey] = useState('');
  const [topicLabel, setTopicLabel] = useState('');
  const [skillId, setSkillId] = useState('');
  const [skillFull, setSkillFull] = useState('');
  const [bloom, setBloom] = useState('Remember');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    const key = topicKey.trim();
    if (!key || !topicLabel.trim() || !skillId.trim() || !skillFull.trim()) {
      setError('All fields are required.');
      return;
    }
    if (existingTopicKeys.includes(key)) {
      setError(`${key} already exists in ${subject} — use "Add skill" to add to it instead.`);
      return;
    }
    setSubmitting(true);
    try {
      const response = await adminFetch('/admin/ontology/skills', username, {
        method: 'POST',
        body: JSON.stringify({
          skill_id: skillId.trim(),
          skill_full: skillFull.trim(),
          topic_key: key,
          topic_label: topicLabel.trim(),
          subject,
          bloom,
          prerequisite_ids: [],
        }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed (${response.status})`);
      }
      onCreated(key);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <ModalShell title={`Add topic to ${subject}`} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-3">
        {error && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-2">{error}</div>}
        <p className="text-xs text-gray-500">
          A topic only exists here as long as it has at least one skill, so creating a topic means
          creating its first skill too — add more skills to it afterward from the topic view.
        </p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-semibold text-gray-600">Topic key</label>
            <input className="input-field" value={topicKey} onChange={(e) => setTopicKey(e.target.value)} placeholder="e.g. PHY1_NEW_TOPIC" />
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-600">Topic label</label>
            <input className="input-field" value={topicLabel} onChange={(e) => setTopicLabel(e.target.value)} placeholder="Display name" />
          </div>
        </div>

        <hr className="border-gray-100" />

        <div>
          <label className="text-xs font-semibold text-gray-600">First skill ID</label>
          <input className="input-field" value={skillId} onChange={(e) => setSkillId(e.target.value)} placeholder="e.g. PHY1_NEW_TOPIC0" />
        </div>
        <div>
          <label className="text-xs font-semibold text-gray-600">First skill description</label>
          <textarea className="input-field" rows={3} value={skillFull} onChange={(e) => setSkillFull(e.target.value)} />
        </div>
        <div>
          <label className="text-xs font-semibold text-gray-600">Bloom level</label>
          <select className="input-field" value={bloom} onChange={(e) => setBloom(e.target.value)}>
            {BLOOM_LEVELS.map((b) => <option key={b} value={b}>{b}</option>)}
          </select>
        </div>

        <button className="btn-primary w-full" type="submit" disabled={submitting}>
          {submitting ? 'Creating...' : 'Create topic'}
        </button>
      </form>
    </ModalShell>
  );
}

function AddEdgeModal({ username, targetSkill, onClose, onCreated }) {
  const [prereqId, setPrereqId] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    if (!prereqId.trim()) {
      setError('Enter a skill id.');
      return;
    }
    setSubmitting(true);
    try {
      const response = await adminFetch('/admin/ontology/edges', username, {
        method: 'POST',
        body: JSON.stringify({ from_id: prereqId.trim(), to_id: targetSkill.id }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed (${response.status})`);
      }
      onCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <ModalShell title={`Add prerequisite for ${targetSkill.id}`} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-3">
        {error && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-2">{error}</div>}
        <div>
          <label className="text-xs font-semibold text-gray-600">Prerequisite skill ID</label>
          <input className="input-field" value={prereqId} onChange={(e) => setPrereqId(e.target.value)} placeholder="Exact skill id" autoFocus />
        </div>
        <button className="btn-primary w-full" type="submit" disabled={submitting}>
          {submitting ? 'Adding...' : 'Add prerequisite'}
        </button>
      </form>
    </ModalShell>
  );
}

function RenameTopicModal({ username, topicKey, currentTopic, onClose, onSaved }) {
  const [label, setLabel] = useState(currentTopic?.topic_label || '');
  const [subject, setSubject] = useState(currentTopic?.subject || '');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const response = await adminFetch(`/admin/ontology/topics/${encodeURIComponent(topicKey)}`, username, {
        method: 'PATCH',
        body: JSON.stringify({ topic_label: label.trim(), subject }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed (${response.status})`);
      }
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <ModalShell title={`Edit topic: ${topicKey}`} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-3">
        {error && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-2">{error}</div>}
        <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-2">
          This relabels every skill filed under this topic. It will not update
          the shared label copy in Backend/tree_data/ontology_config.json, so
          _validate_ontology.py may report a label-drift warning afterwards
          (expected, non-fatal).
        </p>
        <div>
          <label className="text-xs font-semibold text-gray-600">Topic label</label>
          <input className="input-field" value={label} onChange={(e) => setLabel(e.target.value)} />
        </div>
        <div>
          <label className="text-xs font-semibold text-gray-600">Subject</label>
          <input className="input-field" value={subject} onChange={(e) => setSubject(e.target.value)} />
        </div>
        <button className="btn-primary w-full" type="submit" disabled={submitting}>
          {submitting ? 'Saving...' : 'Save topic'}
        </button>
      </form>
    </ModalShell>
  );
}
