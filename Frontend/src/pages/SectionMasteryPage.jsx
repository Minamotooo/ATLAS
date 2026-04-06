import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useLanguage } from "../context/LanguageContext";
import { useAuth, buildApiUrl } from "../context/AuthContext";
import {
  AlertCircle,
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  GitBranch,
  Lock,
  RefreshCw,
  Table2,
} from "lucide-react";

function masteryColor(mastery) {
  if (mastery >= 95) {
    return "bg-emerald-500";
  }
  if (mastery >= 70) {
    return "bg-atlas-500";
  }
  if (mastery >= 40) {
    return "bg-amber-500";
  }
  return "bg-gray-400";
}

function masteryColorHex(mastery) {
  if (mastery >= 95) {
    return "#10b981";
  }
  if (mastery >= 70) {
    return "#2f7ff8";
  }
  if (mastery >= 40) {
    return "#f59e0b";
  }
  return "#9ca3af";
}

function buildDependencyGraphLayout(nodes, edges) {
  const nodeIds = nodes.map((node) => node.skill_id);
  const outgoing = new Map(nodeIds.map((id) => [id, []]));
  const incoming = new Map(nodeIds.map((id) => [id, []]));
  const indegree = new Map(nodeIds.map((id) => [id, 0]));
  const level = new Map(nodeIds.map((id) => [id, 0]));

  for (const edge of edges) {
    if (!outgoing.has(edge.source) || !indegree.has(edge.target)) {
      continue;
    }
    outgoing.get(edge.source).push(edge.target);
    incoming.get(edge.target).push(edge.source);
    indegree.set(edge.target, (indegree.get(edge.target) || 0) + 1);
  }

  const queue = nodeIds.filter((id) => (indegree.get(id) || 0) === 0);
  if (queue.length === 0 && nodeIds.length > 0) {
    queue.push(nodeIds[0]);
  }

  const visited = new Set();
  for (let i = 0; i < queue.length; i += 1) {
    const current = queue[i];
    visited.add(current);
    const currentLevel = level.get(current) || 0;

    for (const next of outgoing.get(current) || []) {
      level.set(next, Math.max(level.get(next) || 0, currentLevel + 1));
      indegree.set(next, (indegree.get(next) || 0) - 1);
      if ((indegree.get(next) || 0) === 0) {
        queue.push(next);
      }
    }
  }

  // Ensure nodes in cyclic/isolated subgraphs still appear.
  for (const id of nodeIds) {
    if (!visited.has(id)) {
      level.set(id, level.get(id) || 0);
    }
  }

  const maxLevel = Math.max(0, ...Array.from(level.values()));
  const rows = Array.from({ length: maxLevel + 1 }, () => []);
  const nodeById = new Map(nodes.map((node) => [node.skill_id, node]));

  for (const id of nodeIds) {
    rows[level.get(id) || 0].push(id);
  }

  // Root row: higher fan-out and mastery appear more central/early.
  rows[0].sort((a, b) => {
    const fanOutDiff =
      (outgoing.get(b)?.length || 0) - (outgoing.get(a)?.length || 0);
    if (fanOutDiff !== 0) {
      return fanOutDiff;
    }
    const masteryDiff =
      (nodeById.get(b)?.mastery || 0) - (nodeById.get(a)?.mastery || 0);
    if (masteryDiff !== 0) {
      return masteryDiff;
    }
    return a.localeCompare(b);
  });

  const orderById = new Map(rows[0].map((id, idx) => [id, idx]));

  // Child rows: sort by average parent order to preserve tree-like branching.
  for (let rowIndex = 1; rowIndex < rows.length; rowIndex += 1) {
    const row = rows[rowIndex];
    row.sort((a, b) => {
      const parentA = incoming.get(a) || [];
      const parentB = incoming.get(b) || [];

      const scoreA = parentA.length
        ? parentA.reduce((sum, pid) => sum + (orderById.get(pid) ?? 0), 0) /
          parentA.length
        : Number.MAX_SAFE_INTEGER;
      const scoreB = parentB.length
        ? parentB.reduce((sum, pid) => sum + (orderById.get(pid) ?? 0), 0) /
          parentB.length
        : Number.MAX_SAFE_INTEGER;

      if (scoreA !== scoreB) {
        return scoreA - scoreB;
      }

      const masteryDiff =
        (nodeById.get(b)?.mastery || 0) - (nodeById.get(a)?.mastery || 0);
      if (masteryDiff !== 0) {
        return masteryDiff;
      }
      return a.localeCompare(b);
    });

    row.forEach((id, idx) => {
      if (!orderById.has(id)) {
        orderById.set(id, idx);
      }
    });
  }

  const nodeRadius = 44;
  const nodeDiameter = nodeRadius * 2;
  const siblingGap = 64;
  const levelGap = 110;
  const paddingX = 56;
  const paddingY = 52;

  const maxColumns = Math.max(1, ...rows.map((row) => row.length));
  const contentWidth =
    maxColumns * nodeDiameter + (maxColumns - 1) * siblingGap;

  const contentHeight =
    rows.length * nodeDiameter + Math.max(0, rows.length - 1) * levelGap;

  const width = Math.max(980, paddingX * 2 + contentWidth);
  const height = Math.max(500, paddingY * 2 + contentHeight);

  const positions = new Map();

  rows.forEach((row, rowIndex) => {
    const y = paddingY + rowIndex * (nodeDiameter + levelGap);
    const rowWidth =
      row.length * nodeDiameter + Math.max(0, row.length - 1) * siblingGap;
    const startX = paddingX + Math.max(0, (contentWidth - rowWidth) / 2);

    row.forEach((id, columnIndex) => {
      positions.set(id, {
        x: startX + columnIndex * (nodeDiameter + siblingGap),
        y,
      });
    });
  });

  return {
    width,
    height,
    nodeRadius,
    nodeDiameter,
    positions,
  };
}

export default function SectionMasteryPage() {
  const { courseId, sectionId } = useParams();
  const { lang } = useLanguage();
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  const [sectionMeta, setSectionMeta] = useState(null);
  const [masteryPayload, setMasteryPayload] = useState(null);
  const [pageLoading, setPageLoading] = useState(true);
  const [pageError, setPageError] = useState("");
  const [viewMode, setViewMode] = useState("table");
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      navigate("/login");
    }
  }, [loading, user, navigate]);

  async function loadPageData(silent = false) {
    if (!user) {
      return;
    }

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

      if (!catalogResponse.ok) {
        throw new Error(`Catalog request failed (${catalogResponse.status})`);
      }
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
          // Ignore parse failures and keep HTTP status-based message.
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
  }

  useEffect(() => {
    loadPageData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId, sectionId, user]);

  const sectionTitle = useMemo(() => {
    if (!sectionMeta) {
      return sectionId;
    }
    return lang === "bn" && sectionMeta.title_bn
      ? sectionMeta.title_bn
      : sectionMeta.title;
  }, [sectionMeta, lang, sectionId]);

  const tableRows = useMemo(() => {
    const rows = Array.isArray(masteryPayload?.table)
      ? masteryPayload.table
      : [];
    return [...rows].sort((a, b) => b.mastery - a.mastery);
  }, [masteryPayload]);

  const edgeRows = useMemo(() => {
    const edges = masteryPayload?.map?.edges;
    return Array.isArray(edges) ? edges : [];
  }, [masteryPayload]);

  const mapNodes = useMemo(() => {
    const nodes = masteryPayload?.map?.nodes;
    return Array.isArray(nodes) ? nodes : [];
  }, [masteryPayload]);

  const graphLayout = useMemo(() => {
    if (mapNodes.length === 0) {
      return null;
    }
    return buildDependencyGraphLayout(mapNodes, edgeRows);
  }, [mapNodes, edgeRows]);

  const summary = useMemo(() => {
    const totalSkills = tableRows.length;
    const average =
      totalSkills > 0
        ? Math.round(
            tableRows.reduce((sum, row) => sum + row.mastery, 0) / totalSkills,
          )
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
              <RefreshCw size={16} />
              Retry
            </button>
            <Link
              to={`/courses/${courseId}/sections/${sectionId}`}
              className="btn-secondary"
            >
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
          <>
            <div className="grid sm:grid-cols-3 gap-4">
              <div className="card p-4 border border-atlas-100">
                <div className="text-xs text-gray-500 uppercase tracking-wide">
                  Tracked Skills
                </div>
                <div className="text-2xl font-bold text-gray-900 mt-1">
                  {summary.totalSkills}
                </div>
              </div>
              <div className="card p-4 border border-atlas-100">
                <div className="text-xs text-gray-500 uppercase tracking-wide">
                  Average Mastery
                </div>
                <div className="text-2xl font-bold text-gray-900 mt-1">
                  {summary.average}%
                </div>
              </div>
              <div className="card p-4 border border-atlas-100">
                <div className="text-xs text-gray-500 uppercase tracking-wide">
                  Mastered (95%+)
                </div>
                <div className="text-2xl font-bold text-gray-900 mt-1">
                  {summary.mastered}
                </div>
              </div>
            </div>

            <div className="card p-3">
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setViewMode("table")}
                  className={`inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm font-semibold transition-all ${
                    viewMode === "table"
                      ? "bg-atlas-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  <Table2 size={15} />
                  Mastery Table
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode("map")}
                  className={`inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm font-semibold transition-all ${
                    viewMode === "map"
                      ? "bg-atlas-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  <GitBranch size={15} />
                  Dependency Map
                </button>
              </div>
            </div>

            {viewMode === "table" && (
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
                        <tr
                          key={row.skill_id}
                          className="border-b last:border-b-0 border-gray-100"
                        >
                          <td className="px-4 py-3 font-semibold text-gray-900">
                            {row.skill_id}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-700">
                            {row.skill_description || "-"}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex flex-wrap gap-1.5">
                              {(row.topics || []).map((topic) => (
                                <span
                                  key={`${row.skill_id}-${topic}`}
                                  className="rounded-full bg-atlas-50 border border-atlas-100 px-2 py-0.5 text-xs text-atlas-700"
                                >
                                  {topic}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-semibold text-gray-800 w-12">
                                {Math.round(row.mastery)}%
                              </span>
                              <div className="h-2 w-32 rounded-full bg-gray-100 overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${masteryColor(row.mastery)}`}
                                  style={{
                                    width: `${Math.max(0, Math.min(100, row.mastery))}%`,
                                  }}
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

            {viewMode === "map" && (
              <div className="card p-4">
                <h3 className="font-semibold text-gray-900 mb-1 flex items-center gap-2">
                  <BarChart3 size={16} />
                  Dependency Graph Preview
                </h3>
                <p className="text-xs text-gray-500 mb-3">
                  {mapNodes.length} skills and {edgeRows.length} prerequisite
                  relations.
                </p>

                {graphLayout ? (
                  <div className="overflow-auto rounded-2xl border border-slate-200 bg-gradient-to-br from-slate-50 via-indigo-50/40 to-white">
                    <svg
                      width={graphLayout.width}
                      height={graphLayout.height}
                      viewBox={`0 0 ${graphLayout.width} ${graphLayout.height}`}
                      role="img"
                      aria-label="Skill dependency graph"
                      className="block"
                    >
                      <defs>
                        <linearGradient
                          id="graph-background"
                          x1="0"
                          y1="0"
                          x2="1"
                          y2="1"
                        >
                          <stop offset="0%" stopColor="#f8fafc" />
                          <stop offset="100%" stopColor="#eef2ff" />
                        </linearGradient>

                        <pattern
                          id="graph-dot-grid"
                          width="24"
                          height="24"
                          patternUnits="userSpaceOnUse"
                        >
                          <circle
                            cx="1.2"
                            cy="1.2"
                            r="1.2"
                            fill="#cbd5e1"
                            opacity="0.55"
                          />
                        </pattern>

                        <filter
                          id="node-glow"
                          x="-50%"
                          y="-50%"
                          width="200%"
                          height="200%"
                        >
                          <feDropShadow
                            dx="0"
                            dy="3"
                            stdDeviation="4"
                            floodColor="#0f172a"
                            floodOpacity="0.28"
                          />
                        </filter>

                        <marker
                          id="dependency-arrow"
                          markerWidth="10"
                          markerHeight="10"
                          refX="8"
                          refY="5"
                          orient="auto"
                          markerUnits="strokeWidth"
                        >
                          <path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b" />
                        </marker>
                      </defs>

                      <rect
                        width={graphLayout.width}
                        height={graphLayout.height}
                        fill="url(#graph-background)"
                      />
                      <rect
                        width={graphLayout.width}
                        height={graphLayout.height}
                        fill="url(#graph-dot-grid)"
                        opacity="0.35"
                      />

                      {edgeRows.map((edge, idx) => {
                        const sourcePos = graphLayout.positions.get(
                          edge.source,
                        );
                        const targetPos = graphLayout.positions.get(
                          edge.target,
                        );
                        if (!sourcePos || !targetPos) {
                          return null;
                        }

                        const sourceCenterX =
                          sourcePos.x + graphLayout.nodeRadius;
                        const sourceCenterY =
                          sourcePos.y + graphLayout.nodeRadius;
                        const targetCenterX =
                          targetPos.x + graphLayout.nodeRadius;
                        const targetCenterY =
                          targetPos.y + graphLayout.nodeRadius;

                        const startX = sourceCenterX;
                        const startY = sourceCenterY + graphLayout.nodeRadius;
                        const endX = targetCenterX;
                        const endY = targetCenterY - graphLayout.nodeRadius;

                        const branchDepth = Math.max(
                          28,
                          (endY - startY) * 0.44,
                        );
                        const control1X = startX;
                        const control1Y = startY + branchDepth;
                        const control2X = endX;
                        const control2Y = endY - branchDepth;

                        return (
                          <path
                            key={`graph-edge-${idx}-${edge.source}-${edge.target}`}
                            d={`M ${startX} ${startY} C ${control1X} ${control1Y}, ${control2X} ${control2Y}, ${endX} ${endY}`}
                            fill="none"
                            stroke="#64748b"
                            strokeOpacity="0.82"
                            strokeWidth="1.8"
                            markerEnd="url(#dependency-arrow)"
                          />
                        );
                      })}

                      {mapNodes.map((node) => {
                        const pos = graphLayout.positions.get(node.skill_id);
                        if (!pos) {
                          return null;
                        }

                        const mastery = Math.round(node.mastery || 0);
                        const fill = masteryColorHex(mastery);
                        const centerX = pos.x + graphLayout.nodeRadius;
                        const centerY = pos.y + graphLayout.nodeRadius;

                        return (
                          <g key={`graph-node-${node.skill_id}`}>
                            <circle
                              cx={centerX}
                              cy={centerY}
                              r={graphLayout.nodeRadius + 8}
                              fill={fill}
                              opacity="0.18"
                            />
                            <circle
                              cx={centerX}
                              cy={centerY}
                              r={graphLayout.nodeRadius}
                              fill={fill}
                              stroke="#ffffff"
                              strokeWidth="2.2"
                              filter="url(#node-glow)"
                            />
                            <circle
                              cx={centerX}
                              cy={centerY}
                              r={graphLayout.nodeRadius - 6}
                              fill="#ffffff"
                              opacity="0.08"
                            />
                            <text
                              x={centerX}
                              y={centerY - 5}
                              textAnchor="middle"
                              fontSize="13"
                              fontWeight="700"
                              fill="#ffffff"
                            >
                              {node.skill_id}
                            </text>
                            <text
                              x={centerX}
                              y={centerY + 14}
                              textAnchor="middle"
                              fontSize="11"
                              fill="#f8fafc"
                            >
                              {mastery}%
                            </text>
                            <title>{`${node.skill_id} - ${mastery}% mastery`}</title>
                          </g>
                        );
                      })}
                    </svg>
                  </div>
                ) : (
                  <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-5 text-sm text-gray-600">
                    No dependency graph data available for this section.
                  </div>
                )}
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
