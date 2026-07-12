import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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

// ─── Mastery colour helpers ──────────────────────────────────────────────────
// Mirrors the HTML's per-topic palette: light bg + coloured border + dark fg.
function masteryPalette(mastery) {
  if (mastery >= 95) return { bg: "#D5F5E3", bd: "#1E8449", fg: "#145A32" }; // green
  if (mastery >= 70) return { bg: "#D6EAF8", bd: "#2E86C1", fg: "#1A5276" }; // blue
  if (mastery >= 40) return { bg: "#FDEBD0", bd: "#CA6F1E", fg: "#784212" }; // orange
  return { bg: "#EAECEE", bd: "#717D7E", fg: "#424949" }; // gray
}

function masteryColor(mastery) {
  if (mastery >= 95) return "bg-emerald-500";
  if (mastery >= 70) return "bg-atlas-500";
  if (mastery >= 40) return "bg-amber-500";
  return "bg-gray-400";
}

// ─── Cytoscape script loader ─────────────────────────────────────────────────
function loadScript(src) {
  return new Promise((resolve) => {
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve();
      return;
    }
    const s = document.createElement("script");
    s.src = src;
    s.onload = resolve;
    document.head.appendChild(s);
  });
}

// ─── Legend tiers ─────────────────────────────────────────────────────────────
const MASTERY_TIERS = [
  { label: "Mastered (95%+)", ...masteryPalette(95) },
  { label: "Proficient (70–94%)", ...masteryPalette(70) },
  { label: "Developing (40–69%)", ...masteryPalette(40) },
  { label: "Beginning (<40%)", ...masteryPalette(0) },
];

const GRAPH_FONT_FAMILY = 'Inter, "Noto Sans Bengali", system-ui, sans-serif';

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
  const [viewMode, setViewMode] = useState("table");
  const [refreshing, setRefreshing] = useState(false);

  // ── Cytoscape state ──────────────────────────────────────────────────────
  const cyRef = useRef(null);
  const cyInstance = useRef(null);
  const cyDagreRegistered = useRef(false);
  const [selectedNode, setSelectedNode] = useState(null); // { id, mastery, description, topics, prereqs, leadsTo }
  const [searchQuery, setSearchQuery] = useState("");

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

  const summary = useMemo(() => {
    const totalSkills = tableRows.length;
    const average =
      totalSkills > 0
        ? Math.round(
            tableRows.reduce((sum, row) => sum + row.mastery, 0) / totalSkills,
          )
        : 0;
    const mastered = tableRows.filter((row) => row.mastery >= 95).length;
    return { totalSkills, average, mastered };
  }, [tableRows]);

  // ── Cytoscape initialisation ─────────────────────────────────────────────
  useEffect(() => {
    if (viewMode !== "map") {
      if (cyInstance.current) {
        cyInstance.current.destroy();
        cyInstance.current = null;
      }
      return;
    }
    if (mapNodes.length === 0) return;

    const initCy = () => {
      if (!cyRef.current) return;
      if (cyInstance.current) {
        cyInstance.current.destroy();
        cyInstance.current = null;
      }

      // Register dagre layout extension once
      if (
        !cyDagreRegistered.current &&
        window.cytoscape &&
        window.cytoscapeDagre
      ) {
        try {
          window.cytoscape.use(window.cytoscapeDagre);
        } catch {
          // ignore duplicate registration attempts
        }
        cyDagreRegistered.current = true;
      }

      const elements = [
        ...mapNodes.map((node) => {
          const m = Math.round(node.mastery || 0);
          const pal = masteryPalette(m);
          return {
            data: {
              id: node.skill_id,
              mastery: m,
              description: node.skill_description || "",
              topics: node.topics || [],
              label: `${node.skill_id}\n${m}%`,
              bg: pal.bg,
              bd: pal.bd,
              fg: pal.fg,
            },
          };
        }),
        ...edgeRows.map((edge, i) => ({
          data: { id: `e${i}`, source: edge.source, target: edge.target },
        })),
      ];

      const cy = window.cytoscape({
        container: cyRef.current,
        elements,
        layout: {
          name: "dagre",
          rankDir: "TB",
          nodeSep: 22,
          rankSep: 50,
          edgeSep: 8,
          padding: 40,
          animate: false,
        },
        minZoom: 0.05,
        maxZoom: 4,
        wheelSensitivity: 0.25,
        style: [
          {
            selector: "node",
            style: {
              shape: "roundrectangle",
              width: 118,
              height: 50,
              label: "data(label)",
              "text-valign": "center",
              "text-halign": "center",
              "font-size": "8.5px",
              "font-family": GRAPH_FONT_FAMILY,
              "text-wrap": "wrap",
              "text-max-width": "106px",
              "border-width": 1.5,
              "font-weight": 500,
              "background-color": (n) => n.data("bg"),
              "border-color": (n) => n.data("bd"),
              color: (n) => n.data("fg"),
            },
          },
          {
            selector: "edge",
            style: {
              width: 1.4,
              "line-color": "#7a8bbd",
              "target-arrow-color": "#7a8bbd",
              "target-arrow-shape": "triangle",
              "curve-style": "bezier",
              "arrow-scale": 0.85,
              opacity: 0.75,
            },
          },
          // Selection / highlight / dim — exact match to HTML
          {
            selector: "node.hl",
            style: {
              "border-width": 3,
              "border-color": "#1c1c2e",
              "z-index": 10,
            },
          },
          {
            selector: "node.sel",
            style: {
              "border-width": 3,
              "border-color": "#e74c3c",
              "z-index": 20,
            },
          },
          { selector: "node.dim", style: { opacity: 0.18 } },
          {
            selector: "edge.hl",
            style: {
              "line-color": "#e74c3c",
              "target-arrow-color": "#e74c3c",
              width: 2.2,
              opacity: 1,
              "z-index": 10,
            },
          },
          { selector: "edge.dim", style: { opacity: 0.04 } },
        ],
      });

      function clearSel() {
        cy.nodes().removeClass("dim hl sel");
        cy.edges().removeClass("dim hl");
      }

      cy.on("tap", "node", (e) => {
        const n = e.target;
        clearSel();
        cy.nodes().addClass("dim");
        cy.edges().addClass("dim");
        n.neighborhood().nodes().removeClass("dim").addClass("hl");
        n.neighborhood().edges().removeClass("dim").addClass("hl");
        n.removeClass("dim").addClass("sel");

        const d = n.data();
        setSelectedNode({
          id: d.id,
          mastery: d.mastery,
          description: d.description,
          topics: d.topics,
          prereqs: n.incomers("edge").map((edge) => ({
            id: edge.source().id(),
            mastery: edge.source().data("mastery"),
            bg: edge.source().data("bd"),
          })),
          leadsTo: n.outgoers("edge").map((edge) => ({
            id: edge.target().id(),
            mastery: edge.target().data("mastery"),
            bg: edge.target().data("bd"),
          })),
        });
      });

      cy.on("tap", (e) => {
        if (e.target === cy) {
          clearSel();
          setSelectedNode(null);
        }
      });

      cyInstance.current = cy;
    };

    loadScript(
      "https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.26.0/cytoscape.min.js",
    )
      .then(() =>
        loadScript(
          "https://cdn.jsdelivr.net/npm/dagre@0.8.5/dist/dagre.min.js",
        ),
      )
      .then(() =>
        loadScript(
          "https://cdn.jsdelivr.net/npm/cytoscape-dagre@2.5.0/cytoscape-dagre.min.js",
        ),
      )
      .then(initCy);

    return () => {
      if (cyInstance.current) {
        cyInstance.current.destroy();
        cyInstance.current = null;
      }
    };
  }, [viewMode, mapNodes, edgeRows]);

  // ── Search handler (wired to topbar input) ───────────────────────────────
  useEffect(() => {
    const cy = cyInstance.current;
    if (!cy) return;
    cy.nodes().removeClass("dim hl sel");
    cy.edges().removeClass("dim hl");
    if (!searchQuery) return;
    const q = searchQuery.toLowerCase();
    cy.nodes().addClass("dim");
    cy.edges().addClass("dim");
    cy.nodes()
      .filter((n) => {
        const d = n.data();
        return (
          d.id.toLowerCase().includes(q) ||
          (d.description || "").toLowerCase().includes(q)
        );
      })
      .forEach((n) => {
        n.removeClass("dim").addClass("hl");
        n.neighborhood().edges().removeClass("dim").addClass("hl");
      });
  }, [searchQuery]);

  // ── Helpers for detail-panel node navigation ─────────────────────────────
  function jumpToNode(id) {
    const cy = cyInstance.current;
    if (!cy) return;
    const n = cy.getElementById(id);
    if (n && n.length) n.trigger("tap");
  }

  function clearSelection() {
    const cy = cyInstance.current;
    if (cy) {
      cy.nodes().removeClass("dim hl sel");
      cy.edges().removeClass("dim hl");
    }
    setSelectedNode(null);
    setSearchQuery("");
  }

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
            {/* Summary cards */}
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

            {/* View toggle */}
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
                  <Table2 size={15} /> Mastery Table
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
                  <GitBranch size={15} /> Dependency Map
                </button>
              </div>
            </div>

            {/* ── TABLE VIEW ─────────────────────────────────────────────── */}
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

            {/* ── MAP VIEW ───────────────────────────────────────────────── */}
            {viewMode === "map" && (
              <div className="card overflow-hidden">
                {/* ── Atlas topbar (aligned with navbar theme) ── */}
                <div
                  style={{
                    background: "#4338ca",
                    color: "#ffffff",
                    padding: "9px 16px",
                    display: "flex",
                    alignItems: "center",
                    gap: "12px",
                    flexWrap: "wrap",
                    boxShadow: "0 2px 8px rgba(49, 46, 129, .35)",
                    fontFamily: GRAPH_FONT_FAMILY,
                  }}
                >
                  <span
                    style={{
                      fontSize: "13px",
                      fontWeight: 600,
                      whiteSpace: "nowrap",
                    }}
                  >
                    <BarChart3
                      size={14}
                      style={{
                        display: "inline",
                        marginRight: 6,
                        verticalAlign: "text-bottom",
                      }}
                    />
                    Dependency Graph
                  </span>
                  <span style={{ color: "#c7d2fe", fontSize: "18px" }}>|</span>
                  <span
                    style={{
                      fontSize: "11px",
                      color: "#e0e7ff",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {mapNodes.length} nodes · {edgeRows.length} edges
                  </span>

                  <input
                    type="text"
                    placeholder="Search ID or keyword…"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    style={{
                      padding: "5px 10px",
                      borderRadius: "5px",
                      border: "1px solid rgba(224,231,255,0.45)",
                      background: "rgba(255,255,255,0.14)",
                      color: "#ffffff",
                      fontSize: "11px",
                      width: "190px",
                      outline: "none",
                      fontFamily: GRAPH_FONT_FAMILY,
                    }}
                  />

                  {[
                    {
                      label: "⊡ Fit all",
                      action: () => cyInstance.current?.fit(null, 40),
                    },
                    {
                      label: "+ Zoom",
                      action: () => {
                        const cy = cyInstance.current;
                        if (cy) cy.zoom(cy.zoom() * 1.35);
                      },
                    },
                    {
                      label: "− Zoom",
                      action: () => {
                        const cy = cyInstance.current;
                        if (cy) cy.zoom(cy.zoom() * 0.75);
                      },
                    },
                    { label: "✕ Clear", action: clearSelection },
                  ].map(({ label, action }) => (
                    <button
                      key={label}
                      type="button"
                      onClick={action}
                      style={{
                        background: "rgba(255,255,255,0.16)",
                        border: "1px solid rgba(224,231,255,0.4)",
                        color: "#ffffff",
                        padding: "4px 10px",
                        borderRadius: "4px",
                        cursor: "pointer",
                        fontSize: "11px",
                        whiteSpace: "nowrap",
                        fontFamily: GRAPH_FONT_FAMILY,
                      }}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                {mapNodes.length === 0 ? (
                  <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-5 text-sm text-gray-600 m-4">
                    No dependency graph data available for this section.
                  </div>
                ) : (
                  /* ── Main 3-column area ── */
                  <div
                    style={{
                      display: "flex",
                      height: "600px",
                      fontFamily: GRAPH_FONT_FAMILY,
                    }}
                  >
                    {/* ── Left sidebar: legend ── */}
                    <div
                      style={{
                        width: "200px",
                        background: "#fff",
                        borderRight: "1px solid #e0e4ea",
                        overflowY: "auto",
                        flexShrink: 0,
                        display: "flex",
                        flexDirection: "column",
                      }}
                    >
                      <div
                        style={{
                          padding: "10px 12px 6px",
                          fontSize: "11px",
                          fontWeight: 700,
                          color: "#555",
                          textTransform: "uppercase",
                          letterSpacing: "0.5px",
                          borderBottom: "1px solid #eee",
                        }}
                      >
                        Mastery Levels
                      </div>
                      <div style={{ padding: "8px 10px", flex: 1 }}>
                        {MASTERY_TIERS.map((tier) => (
                          <div
                            key={tier.label}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: "7px",
                              padding: "5px 6px",
                              borderRadius: "5px",
                            }}
                          >
                            <div
                              style={{
                                width: "13px",
                                height: "13px",
                                borderRadius: "3px",
                                background: tier.bg,
                                flexShrink: 0,
                                border: `1.5px solid ${tier.bd}`,
                              }}
                            />
                            <span
                              style={{
                                fontSize: "11px",
                                color: "#3a3a3a",
                                lineHeight: "1.35",
                              }}
                            >
                              {tier.label}
                            </span>
                          </div>
                        ))}
                      </div>
                      <div
                        style={{
                          fontSize: "10px",
                          color: "#bbb",
                          padding: "4px 10px 10px",
                          lineHeight: "1.5",
                        }}
                      >
                        Click a node to see its prerequisites and connections
                      </div>
                    </div>

                    {/* ── Cytoscape canvas ── */}
                    <div
                      ref={cyRef}
                      style={{ flex: 1, background: "#fafbfc", minWidth: 0 }}
                    />

                    {/* ── Right detail panel (mirrors HTML's #detail) ── */}
                    {selectedNode && (
                      <div
                        style={{
                          width: "260px",
                          background: "#fff",
                          borderLeft: "1px solid #e0e4ea",
                          overflowY: "auto",
                          flexShrink: 0,
                          position: "relative",
                        }}
                      >
                        {/* Close button */}
                        <button
                          type="button"
                          onClick={clearSelection}
                          style={{
                            position: "absolute",
                            top: "8px",
                            right: "10px",
                            background: "none",
                            border: "none",
                            fontSize: "18px",
                            cursor: "pointer",
                            color: "#bbb",
                            lineHeight: 1,
                          }}
                        >
                          ×
                        </button>

                        <div style={{ padding: "14px 14px 20px" }}>
                          {/* Node ID */}
                          <div
                            style={{
                              fontSize: "16px",
                              fontWeight: 700,
                              color: "#1c1c2e",
                              marginBottom: "4px",
                            }}
                          >
                            {selectedNode.id}
                          </div>

                          {/* Mastery badge */}
                          <span
                            style={{
                              fontSize: "10px",
                              fontWeight: 600,
                              padding: "3px 9px",
                              borderRadius: "12px",
                              display: "inline-block",
                              marginBottom: "10px",
                              background: masteryPalette(selectedNode.mastery)
                                .bg,
                              color: masteryPalette(selectedNode.mastery).fg,
                              border: `1px solid ${masteryPalette(selectedNode.mastery).bd}`,
                            }}
                          >
                            {selectedNode.mastery}% mastery
                          </span>

                          {/* Description */}
                          {selectedNode.description && (
                            <div
                              style={{
                                fontSize: "12px",
                                color: "#333",
                                lineHeight: "1.65",
                                marginBottom: "14px",
                                padding: "8px 10px",
                                background: "#f8f9fa",
                                borderRadius: "6px",
                                borderLeft: `3px solid ${masteryPalette(selectedNode.mastery).bd}`,
                              }}
                            >
                              {selectedNode.description}
                            </div>
                          )}

                          {/* Topics */}
                          {selectedNode.topics?.length > 0 && (
                            <div style={{ marginBottom: "12px" }}>
                              <div
                                style={{
                                  fontSize: "10px",
                                  fontWeight: 700,
                                  color: "#999",
                                  textTransform: "uppercase",
                                  letterSpacing: "0.5px",
                                  marginBottom: "5px",
                                }}
                              >
                                Topics
                              </div>
                              <div
                                style={{
                                  display: "flex",
                                  flexWrap: "wrap",
                                  gap: "4px",
                                }}
                              >
                                {selectedNode.topics.map((t) => (
                                  <span
                                    key={t}
                                    style={{
                                      fontSize: "10px",
                                      padding: "2px 7px",
                                      borderRadius: "10px",
                                      background: "#eef2ff",
                                      color: "#4338ca",
                                      border: "1px solid #c7d2fe",
                                    }}
                                  >
                                    {t}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Prerequisites */}
                          <div
                            style={{
                              fontSize: "10px",
                              fontWeight: 700,
                              color: "#999",
                              textTransform: "uppercase",
                              letterSpacing: "0.5px",
                              marginBottom: "5px",
                            }}
                          >
                            Prerequisites — incoming
                          </div>
                          <ul
                            style={{ listStyle: "none", marginBottom: "14px" }}
                          >
                            {selectedNode.prereqs.length === 0 ? (
                              <li
                                style={{
                                  fontSize: "11px",
                                  color: "#bbb",
                                  padding: "5px 8px",
                                  background: "#f8f9fb",
                                  borderRadius: "4px",
                                  borderLeft: "3px solid #eee",
                                }}
                              >
                                None — root skill
                              </li>
                            ) : (
                              selectedNode.prereqs.map((p) => (
                                <li
                                  key={p.id}
                                  onClick={() => jumpToNode(p.id)}
                                  style={{
                                    fontSize: "11px",
                                    color: "#444",
                                    padding: "5px 8px",
                                    background: "#f8f9fb",
                                    borderRadius: "4px",
                                    marginBottom: "3px",
                                    cursor: "pointer",
                                    borderLeft: `3px solid ${masteryPalette(p.mastery).bd}`,
                                    lineHeight: "1.4",
                                    transition: "background .12s",
                                  }}
                                  onMouseEnter={(e) =>
                                    (e.currentTarget.style.background =
                                      "#eef2ff")
                                  }
                                  onMouseLeave={(e) =>
                                    (e.currentTarget.style.background =
                                      "#f8f9fb")
                                  }
                                >
                                  <span
                                    style={{
                                      fontWeight: 700,
                                      marginRight: "4px",
                                    }}
                                  >
                                    {p.id}
                                  </span>
                                  {p.mastery}%
                                </li>
                              ))
                            )}
                          </ul>

                          {/* Leads to */}
                          <div
                            style={{
                              fontSize: "10px",
                              fontWeight: 700,
                              color: "#999",
                              textTransform: "uppercase",
                              letterSpacing: "0.5px",
                              marginBottom: "5px",
                            }}
                          >
                            Leads to — outgoing
                          </div>
                          <ul style={{ listStyle: "none" }}>
                            {selectedNode.leadsTo.length === 0 ? (
                              <li
                                style={{
                                  fontSize: "11px",
                                  color: "#bbb",
                                  padding: "5px 8px",
                                  background: "#f8f9fb",
                                  borderRadius: "4px",
                                  borderLeft: "3px solid #eee",
                                }}
                              >
                                None — terminal skill
                              </li>
                            ) : (
                              selectedNode.leadsTo.map((l) => (
                                <li
                                  key={l.id}
                                  onClick={() => jumpToNode(l.id)}
                                  style={{
                                    fontSize: "11px",
                                    color: "#444",
                                    padding: "5px 8px",
                                    background: "#f8f9fb",
                                    borderRadius: "4px",
                                    marginBottom: "3px",
                                    cursor: "pointer",
                                    borderLeft: `3px solid ${masteryPalette(l.mastery).bd}`,
                                    lineHeight: "1.4",
                                    transition: "background .12s",
                                  }}
                                  onMouseEnter={(e) =>
                                    (e.currentTarget.style.background =
                                      "#eef2ff")
                                  }
                                  onMouseLeave={(e) =>
                                    (e.currentTarget.style.background =
                                      "#f8f9fb")
                                  }
                                >
                                  <span
                                    style={{
                                      fontWeight: 700,
                                      marginRight: "4px",
                                    }}
                                  >
                                    {l.id}
                                  </span>
                                  {l.mastery}%
                                </li>
                              ))
                            )}
                          </ul>
                        </div>
                      </div>
                    )}
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
