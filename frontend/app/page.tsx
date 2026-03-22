"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface AnalyzeResponse {
  industry: string;
  brand: string;
  sentiment_count: number;
  avg_score: number;
  bullish_count: number;
  bearish_count: number;
  neutral_count: number;
  anomaly_count: number;
  anomalies: { text: string; z_score: number; direction: string; severity: string }[];
  forecast_30d: number | null;
  forecast_60d: number | null;
  forecast_90d: number | null;
  forecast_label: string;
  competitor_delta: { brand: string; score: number; label: string; rank: number; is_primary: boolean }[];
  insight_report: string;
  top_headlines: { text: string; score: number; label: string; confidence?: number }[];
}

interface HistoryRun {
  id: number;
  timestamp: string;
  industry: string;
  brand: string;
  avg_score: number;
  bullish_count: number;
  bearish_count: number;
  neutral_count: number;
  anomaly_count: number;
  forecast_30d: number | null;
  insight_report: string;
}

const INDUSTRIES = ["Hotels", "Airlines", "Finance"];
const BRANDS: Record<string, string[]> = {
  Hotels: ["Marriott", "Hilton", "IHG", "Hyatt", "Wyndham"],
  Airlines: ["Delta", "United", "American", "Southwest", "JetBlue"],
  Finance: ["JPMorgan", "Goldman", "Morgan Stanley", "Citi", "BofA"],
};

const AGENT_STEPS = [
  "Sentiment agent reading live news",
  "Forecasting agent projecting demand",
  "Anomaly agent checking outliers",
  "Competitor agent ranking peers",
  "Insight agent writing the briefing",
];

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function scoreColor(score: number) {
  if (score > 0.2) return "#1D9E75";
  if (score < -0.2) return "#D85A30";
  return "var(--muted)";
}

function badgeClasses(label: string) {
  if (label === "bullish") return "bg-[var(--accent-soft)] text-[var(--accent)]";
  if (label === "bearish") return "bg-[var(--danger-soft)] text-[var(--danger)]";
  return "bg-[var(--grid)] text-[var(--foreground)]";
}

function fmtForecastMetric(value: number | null, forecastLabel: string | undefined) {
  if (value === null) return "N/A";
  const label = (forecastLabel ?? "").toLowerCase();
  if (label.includes("nps") || label.includes("satisfaction")) {
    return `${Math.round(value * 100)}%`;
  }
  if (label.includes("revpar") || label.includes("adr")) {
    return `$${value.toFixed(1)}`;
  }
  return value.toFixed(1);
}

function fmtConfidence(value: number | undefined) {
  return typeof value === "number" ? `${value.toFixed(1)}%` : "N/A";
}

function formatLocalTime(rawTimestamp: string): string {
  const date = new Date(rawTimestamp);
  if (Number.isNaN(date.getTime())) return rawTimestamp;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZoneName: "short",
  });
}

function sentimentSurface(score: number) {
  if (score >= 0.2) return { bg: "rgba(29, 158, 117, 0.16)", border: "#1D9E75", text: "#1D9E75" };
  if (score <= -0.2) return { bg: "rgba(216, 90, 48, 0.14)", border: "#D85A30", text: "#D85A30" };
  return { bg: "rgba(120, 113, 108, 0.12)", border: "var(--border)", text: "var(--foreground)" };
}

function downloadCsv(filename: string, rows: string[][]) {
  const csv = rows
    .map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(","))
    .join("\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export default function Dashboard() {
  const [industry, setIndustry] = useState("Hotels");
  const [brand, setBrand] = useState("Marriott");
  const [isDark, setIsDark] = useState(false);
  const [loading, setLoading] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [history, setHistory] = useState<HistoryRun[]>([]);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [stepIndex, setStepIndex] = useState(0);
  const [expandedHeadlines, setExpandedHeadlines] = useState<Record<number, boolean>>({});

  useEffect(() => {
    const savedTheme = window.localStorage.getItem("theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const nextDark = savedTheme ? savedTheme === "dark" : prefersDark;
    document.documentElement.classList.toggle("dark", nextDark);
    setIsDark(nextDark);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDark);
    window.localStorage.setItem("theme", isDark ? "dark" : "light");
  }, [isDark]);

  useEffect(() => {
    if (!loading) return;
    setStepIndex(0);
    const id = window.setInterval(() => {
      setStepIndex((current) => Math.min(current + 1, AGENT_STEPS.length - 1));
    }, 1200);
    return () => window.clearInterval(id);
  }, [loading]);

  useEffect(() => {
    void loadHistory(industry, brand);
  }, [industry, brand]);

  useEffect(() => {
    if (!toast) return;
    const id = window.setTimeout(() => setToast(""), 3200);
    return () => window.clearTimeout(id);
  }, [toast]);

  const progressItems = useMemo(
    () =>
      AGENT_STEPS.map((step, index) => ({
        label: step,
        status: loading
          ? index < stepIndex
            ? "done"
            : index === stepIndex
              ? "active"
              : "pending"
          : data
            ? "done"
            : "pending",
      })),
    [data, loading, stepIndex],
  );

  const historyChartData = useMemo(
    () =>
        [...history].reverse().map((item, index) => ({
        ...item,
        fullTimestamp: formatLocalTime(item.timestamp),
        runLabel: `Run ${index + 1}`,
      })),
    [history],
  );
  const latestHistory = historyChartData.length > 0 ? historyChartData[historyChartData.length - 1] : null;
  const gaugeScore = latestHistory?.avg_score ?? 0;
  const gaugePivotX = 120;
  const gaugePivotY = 132;
  const needleLength = 68;
  const gaugeRadians = Math.PI * (1 - (gaugeScore + 1) / 2);
  const needleX = gaugePivotX + needleLength * Math.cos(gaugeRadians);
  const needleY = gaugePivotY - needleLength * Math.sin(gaugeRadians);
  const latestTotal = latestHistory
    ? latestHistory.bullish_count + latestHistory.bearish_count + latestHistory.neutral_count
    : 0;
  const bullishPct = latestTotal ? (latestHistory!.bullish_count / latestTotal) * 100 : 0;
  const neutralPct = latestTotal ? (latestHistory!.neutral_count / latestTotal) * 100 : 0;
  const bearishPct = latestTotal ? (latestHistory!.bearish_count / latestTotal) * 100 : 0;

  async function loadHistory(nextIndustry: string, nextBrand: string) {
    try {
      const params = new URLSearchParams({
        limit: "10",
        industry: nextIndustry,
        brand: nextBrand,
      });
      const res = await fetch(`${API_BASE_URL}/history?${params.toString()}`);
      if (!res.ok) return;
      setHistory(await res.json());
    } catch {
      setHistory([]);
    }
  }

  async function runAnalysis() {
    setLoading(true);
    setError("");
    setExpandedHeadlines({});
    try {
      const res = await fetch(`${API_BASE_URL}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          industry,
          brand,
          headlines: [],
        }),
      });
      if (!res.ok) {
        let message = `Request failed (${res.status})`;
        try {
          const err = await res.json();
          if (typeof err?.detail === "string") {
            message = err.detail;
          }
        } catch {
          const text = await res.text();
          if (text) message = text;
        }
        throw new Error(message);
      }
      setData(await res.json());
      await loadHistory(industry, brand);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  function exportResults() {
    if (!data) return;
    downloadCsv(`${data.brand.toLowerCase()}-industryiq-report.csv`, [
      ["industry", data.industry],
      ["brand", data.brand],
      ["avg_sentiment", data.avg_score],
      ["headlines_analyzed", data.sentiment_count],
      ["anomalies_detected", data.anomaly_count],
      ["forecast_30d", data.forecast_30d ?? ""],
      ["forecast_60d", data.forecast_60d ?? ""],
      ["forecast_90d", data.forecast_90d ?? ""],
      [],
      ["headline", "score", "label", "confidence_pct"],
      ...data.top_headlines.map((item) => [item.text, String(item.score), item.label, String(item.confidence ?? "")]),
    ]);
  }

  function toggleHeadline(index: number) {
    setExpandedHeadlines((current) => ({ ...current, [index]: !current[index] }));
  }

  function toggleTheme() {
    setIsDark((current) => !current);
  }

  async function downloadReport() {
    if (!data) return;
    setPdfLoading(true);
    setError("");
    setToast("");
    try {
      const res = await fetch(`${API_BASE_URL}/export-pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      if (!res.ok) {
        throw new Error(`PDF export failed (${res.status})`);
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "report.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "PDF export failed";
      setError(message);
      setToast(message);
    } finally {
      setPdfLoading(false);
    }
  }

  return (
    <>
      <style jsx global>{`
        :root {
          --bg: #f5f0e8;
          --card: #ffffff;
          --text: #1a1a1a;
          --background: #f5f0e8;
          --panel: #fffaf2;
          --panel-strong: #f6f0e6;
          --foreground: #1a1a1a;
          --muted: #6b6257;
          --border: rgba(111, 95, 74, 0.16);
          --input-bg: rgba(255, 255, 255, 0.72);
          --grid: rgba(120, 113, 108, 0.14);
          --card-shadow: 0 20px 48px rgba(73, 57, 38, 0.08);
          --hero-shell: linear-gradient(135deg, rgba(255, 250, 242, 0.98), rgba(244, 236, 223, 0.94));
        }

        .dark {
          --bg: #0f0f0f;
          --card: #1a1a1a;
          --text: #f5f5f5;
          --background: #0f0f0f;
          --panel: #141414;
          --panel-strong: #181818;
          --foreground: #f5f5f5;
          --muted: #a0a0a0;
          --border: #2a2a2a;
          --input-bg: #161616;
          --grid: rgba(245, 245, 245, 0.1);
          --card-shadow: 0 20px 48px rgba(0, 0, 0, 0.28);
          --hero-shell: linear-gradient(135deg, rgba(22, 22, 22, 0.98), rgba(15, 15, 15, 0.94));
        }

        html,
        body {
          background: var(--bg);
          color: var(--text);
        }

        body,
        main,
        section,
        div,
        button,
        input,
        select,
        p,
        h1,
        h2,
        h3,
        span {
          transition:
            background-color 0.2s ease,
            color 0.2s ease,
            border-color 0.2s ease,
            box-shadow 0.2s ease;
        }

        .themed-card,
        .themed-card-strong,
        .themed-surface {
          background: var(--card) !important;
          color: var(--text);
          border-color: var(--border) !important;
          box-shadow: var(--card-shadow);
        }

        .themed-input,
        .themed-subtle {
          background: var(--panel-strong) !important;
          color: var(--text);
          border-color: var(--border) !important;
        }

        .industryiq-hero {
          background: var(--hero-shell) !important;
        }

        .timeline-shell {
          overflow: hidden;
        }

        .timeline-scroll {
          overflow-x: auto;
          overflow-y: hidden;
          white-space: nowrap;
          scrollbar-width: thin;
          padding-bottom: 8px;
          -webkit-overflow-scrolling: touch;
        }

        .timeline-scroll::-webkit-scrollbar {
          height: 4px;
        }

        .timeline-scroll::-webkit-scrollbar-track {
          background: transparent;
        }

        .timeline-scroll::-webkit-scrollbar-thumb {
          background: #1d9e75;
          border-radius: 2px;
        }

        .timeline-fade {
          position: absolute;
          top: 0;
          right: 0;
          bottom: 8px;
          width: 56px;
          pointer-events: none;
          background: linear-gradient(90deg, rgba(255, 255, 255, 0), var(--card));
        }
      `}</style>
      <main
        className="min-h-screen overflow-x-hidden px-4 py-5 text-[var(--foreground)] sm:px-6 lg:px-10"
        style={{ background: "var(--bg)", color: "var(--text)" }}
      >
      {toast && (
        <div
          className="fixed right-4 top-4 z-50 rounded-2xl border px-4 py-3 text-sm shadow-lg"
          style={{ background: "var(--card)", borderColor: "var(--danger)", color: "var(--danger)" }}
        >
          {toast}
        </div>
      )}
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <section className="industryiq-hero themed-card overflow-hidden rounded-[28px] backdrop-blur">
          <div className="grid gap-6 p-5 lg:grid-cols-[1.3fr_0.9fr] lg:p-7">
            <div className="space-y-4">
              <div className="inline-flex items-center rounded-full bg-[var(--accent-soft)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-[var(--accent)]">
                IndustryIQ
              </div>
              <div className="space-y-3">
                <h1 className="max-w-2xl text-3xl font-semibold tracking-tight text-[var(--foreground)] sm:text-5xl">
                  Multi-agent intelligence for brand sentiment, peer pressure, and demand direction.
                </h1>
                <p className="max-w-2xl text-sm leading-6 text-[var(--muted)] sm:text-base">
                  Live brand news feeds the sentiment agent, every run is stored, and you can track score movement over time.
                </p>
              </div>
            </div>

            <div className="themed-card-strong rounded-[24px] p-4 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Control Center</div>
                  <div className="text-sm text-[var(--muted)]">Choose a market and brand for the agent run.</div>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={toggleTheme}
                    className="themed-surface rounded-full px-3 py-2 text-sm font-semibold text-[var(--foreground)] hover:border-[var(--accent)]"
                    aria-label="Toggle dark mode"
                  >
                    {isDark ? "☀" : "☾"}
                  </button>
                  {data && (
                    <button
                      onClick={downloadReport}
                      disabled={pdfLoading}
                      className="themed-surface rounded-full px-4 py-2 text-sm font-semibold text-[var(--foreground)] hover:border-[var(--accent)] hover:text-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {pdfLoading ? "Generating..." : "Download Report"}
                    </button>
                  )}
                  <button
                    onClick={runAnalysis}
                    disabled={loading}
                    className="rounded-full bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {loading ? "Running agents..." : "Run agents"}
                  </button>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <label className="space-y-1 text-sm">
                  <span className="text-[var(--muted)]">Industry</span>
                  <select
                    value={industry}
                    onChange={(e) => {
                      const nextIndustry = e.target.value;
                      setIndustry(nextIndustry);
                      setBrand(BRANDS[nextIndustry][0]);
                    }}
                    className="themed-input w-full rounded-2xl px-4 py-3 outline-none focus:border-[var(--accent)]"
                  >
                    {INDUSTRIES.map((item) => (
                      <option key={item}>{item}</option>
                    ))}
                  </select>
                </label>

                <label className="space-y-1 text-sm">
                  <span className="text-[var(--muted)]">Brand</span>
                  <select
                    value={brand}
                    onChange={(e) => setBrand(e.target.value)}
                    className="themed-input w-full rounded-2xl px-4 py-3 outline-none focus:border-[var(--accent)]"
                  >
                    {BRANDS[industry].map((item) => (
                      <option key={item}>{item}</option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="themed-subtle mt-4 flex items-center justify-between rounded-2xl px-4 py-3 text-sm">
                <span>Each run is stored in SQLite and available in recent history.</span>
                <button
                  onClick={exportResults}
                  disabled={!data}
                  className="themed-surface rounded-full px-3 py-1.5 font-medium text-[var(--foreground)] hover:border-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Export CSV
                </button>
              </div>
            </div>
          </div>
        </section>

        {error && (
          <div className="rounded-3xl border px-5 py-4 text-sm" style={{ borderColor: "var(--danger)", background: "var(--danger-soft)", color: "var(--danger)" }}>
            {error}
          </div>
        )}

        <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="themed-card rounded-[28px] p-5">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Agent Progress</div>
                <div className="text-sm text-[var(--muted)]">
                  {loading ? "Live orchestration in progress" : data ? "Last run completed" : "Waiting for a run"}
                </div>
              </div>
              <div className="h-12 w-12 rounded-full bg-[var(--accent-soft)] p-2">
                <div className={`h-full w-full rounded-full border-4 border-[var(--accent)] ${loading ? "animate-spin border-t-transparent" : ""}`} />
              </div>
            </div>

            <div className="space-y-3">
              {progressItems.map((item, index) => (
                <div
                  key={item.label}
                  className={`flex items-center gap-3 rounded-2xl border px-4 py-3 ${
                    item.status === "active"
                      ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                      : item.status === "done"
                        ? "border-[var(--border)] bg-[var(--card)]"
                        : "border-[var(--border)] bg-[var(--input-bg)]"
                  }`}
                >
                  <div
                    className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold ${
                      item.status === "active"
                        ? "bg-[var(--accent)] text-white"
                        : item.status === "done"
                          ? "bg-[var(--foreground)] text-[var(--background)]"
                          : "bg-[var(--grid)] text-[var(--muted)]"
                    }`}
                  >
                    {item.status === "done" ? "✓" : index + 1}
                  </div>
                  <div className="text-sm text-[var(--foreground)]">{item.label}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[
              {
                label: "Avg sentiment",
                value: data ? `${data.avg_score > 0 ? "+" : ""}${data.avg_score.toFixed(3)}` : "Awaiting run",
                tone: data ? scoreColor(data.avg_score) : "#57534e",
              },
              {
                label: "Headlines analyzed",
                value: data ? String(data.sentiment_count) : "0",
                tone: "#1f2937",
              },
              {
                label: "Anomalies detected",
                value: data ? String(data.anomaly_count) : "0",
                tone: data && data.anomaly_count > 0 ? "#c2410c" : "#0f766e",
              },
              {
                label: "30-day forecast",
                value: data ? fmtForecastMetric(data.forecast_30d, data.forecast_label) : "N/A",
                tone: "#1f2937",
              },
            ].map((metric) => (
              <div
                key={metric.label}
                className="rounded-[28px] p-5"
                style={{
                  minHeight: "172px",
                  padding: "20px",
                  background: isDark ? "#1e1e1e" : "var(--card)",
                  border: isDark ? "1px solid #2a2a2a" : "1px solid var(--border)",
                  boxShadow: "var(--card-shadow)",
                }}
              >
                <div
                  className="text-xs font-semibold uppercase tracking-[0.2em]"
                  style={{ color: isDark ? "#888888" : "var(--muted)" }}
                >
                  {metric.label}
                </div>
                <div className="mt-4 text-3xl font-semibold" style={{ color: metric.tone }}>
                  {metric.value}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="themed-card rounded-[28px] p-5">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Sentiment Trend</div>
              <div className="text-sm text-[var(--muted)]">{brand} run history shown through a premium score gauge, run timeline, and latest breakdown.</div>
            </div>
          </div>
          <div className="grid min-w-0 gap-6">
            <div className="themed-surface min-w-0 overflow-hidden rounded-[24px] px-5 pb-4 pt-2">
              <div className="mb-4 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Sentiment Score Gauge</div>
              {latestHistory ? (
                <div className="flex flex-col items-center justify-center pt-1">
                  <svg viewBox="0 24 240 196" className="h-[238px] w-full max-w-[420px] overflow-visible">
                    <defs>
                      <linearGradient id="gaugeArc" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#D85A30" />
                        <stop offset="50%" stopColor="#9ca3af" />
                        <stop offset="100%" stopColor="#1D9E75" />
                      </linearGradient>
                    </defs>
                    <path
                      d="M 44 132 A 76 76 0 0 1 196 132"
                      fill="none"
                      stroke="url(#gaugeArc)"
                      strokeWidth="16"
                      strokeLinecap="round"
                    />
                    <path
                      d="M 56 132 A 64 64 0 0 1 184 132"
                      fill="none"
                      stroke="var(--grid)"
                      strokeWidth="1.5"
                      strokeDasharray="2 6"
                    />
                    <line
                      x1={gaugePivotX}
                      y1={gaugePivotY}
                      x2={needleX}
                      y2={needleY}
                      stroke="var(--foreground)"
                      strokeWidth="4"
                      strokeLinecap="round"
                    />
                    <circle cx={gaugePivotX} cy={gaugePivotY} r="6" fill="#f5f5f5" />
                    <text x="44" y="148" textAnchor="middle" fontSize="11" fill="var(--muted)">-1.0</text>
                    <text x="120" y="158" textAnchor="middle" fontSize="11" fill="var(--muted)">0</text>
                    <text x="196" y="148" textAnchor="middle" fontSize="11" fill="var(--muted)">+1.0</text>
                    <text x="120" y="178" textAnchor="middle" fontSize="30" fontWeight="700" fill={scoreColor(gaugeScore)}>
                      {gaugeScore > 0 ? "+" : ""}
                      {gaugeScore.toFixed(3)}
                    </text>
                    <text x="120" y="196" textAnchor="middle" fontSize="10" fill="var(--muted)" style={{ letterSpacing: "0.18em", textTransform: "uppercase" }}>
                      Latest sentiment score
                    </text>
                    <text x="120" y="212" textAnchor="middle" fontSize="11" fill="var(--muted)">
                      {latestHistory.brand} • {latestHistory.fullTimestamp}
                    </text>
                  </svg>
                </div>
              ) : (
                <div className="flex h-[220px] items-center justify-center rounded-2xl bg-[var(--input-bg)] text-sm text-[var(--muted)]">
                  No history yet — run your first analysis
                </div>
              )}
            </div>

            <div className="timeline-shell themed-surface rounded-[24px] p-5">
              <div className="mb-4 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Runs Timeline</div>
              {historyChartData.length > 0 ? (
                <div className="relative">
                  <div className="timeline-scroll w-full max-w-full">
                    <div className="flex w-max min-w-max items-center gap-3 pr-14">
                    {historyChartData.map((item, index) => {
                      const surface = sentimentSurface(item.avg_score);
                      const prev = index > 0 ? historyChartData[index - 1] : null;
                      const delta = prev ? item.avg_score - prev.avg_score : 0;
                      return (
                        <div key={item.id} className="flex shrink-0 items-center gap-3 whitespace-normal">
                          <div
                            className="w-[220px] shrink-0 rounded-[20px] border px-4 py-4"
                            style={{
                              background: surface.bg,
                              borderColor: surface.border,
                            }}
                          >
                            <div className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">{item.runLabel}</div>
                            <div className="mt-2 text-sm text-[var(--foreground)]">{item.fullTimestamp}</div>
                            <div className="mt-1 text-sm text-[var(--muted)]">{item.brand}</div>
                            <div className="mt-3 text-2xl font-semibold" style={{ color: surface.text }}>
                              {item.avg_score > 0 ? "+" : ""}
                              {item.avg_score.toFixed(3)}
                            </div>
                          </div>
                          {index < historyChartData.length - 1 && (
                            <div className="flex min-w-[64px] shrink-0 flex-col items-center justify-center text-xs text-[var(--muted)]">
                              <div style={{ color: delta >= 0 ? "#1D9E75" : "#D85A30", fontSize: "20px", lineHeight: 1 }}>
                                {delta >= 0 ? "↗" : "↘"}
                              </div>
                              <div>{delta >= 0 ? "+" : ""}{delta.toFixed(3)}</div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                    </div>
                  </div>
                  <div className="timeline-fade" />
                </div>
              ) : (
                <div className="rounded-2xl bg-[var(--input-bg)] px-4 py-6 text-sm text-[var(--muted)]">
                  No history yet — run your first analysis
                </div>
              )}
            </div>

            <div className="themed-surface rounded-[24px] p-5">
              <div className="mb-4 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Sentiment breakdown — latest run</div>
              {latestHistory ? (
                <div className="space-y-3">
                  <div className="flex h-12 overflow-hidden rounded-full border border-[var(--border)] bg-[var(--input-bg)]">
                    <div
                      className="flex items-center justify-center text-xs font-semibold text-white"
                      style={{ width: `${bullishPct}%`, background: "#1D9E75", minWidth: bullishPct > 0 ? "56px" : "0px" }}
                    >
                      {bullishPct > 0 ? `${Math.round(bullishPct)}%` : ""}
                    </div>
                    <div
                      className="flex items-center justify-center text-xs font-semibold"
                      style={{ width: `${neutralPct}%`, background: "#a8a29e", color: "#111827", minWidth: neutralPct > 0 ? "56px" : "0px" }}
                    >
                      {neutralPct > 0 ? `${Math.round(neutralPct)}%` : ""}
                    </div>
                    <div
                      className="flex items-center justify-center text-xs font-semibold text-white"
                      style={{ width: `${bearishPct}%`, background: "#D85A30", minWidth: bearishPct > 0 ? "56px" : "0px" }}
                    >
                      {bearishPct > 0 ? `${Math.round(bearishPct)}%` : ""}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-3 text-xs text-[var(--muted)]">
                    <div className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full" style={{ background: "#1D9E75" }} />
                      Bullish {latestHistory.bullish_count}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full" style={{ background: "#a8a29e" }} />
                      Neutral {latestHistory.neutral_count}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full" style={{ background: "#D85A30" }} />
                      Bearish {latestHistory.bearish_count}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="rounded-2xl bg-[var(--input-bg)] px-4 py-6 text-sm text-[var(--muted)]">
                  No history yet — run your first analysis
                </div>
              )}
            </div>
          </div>
        </section>

        {data && (
          <>
            <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
              <div className="themed-card rounded-[28px] p-5">
                <div className="mb-5 flex items-center justify-between">
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Competitor Ranking</div>
                    <div className="text-sm text-[var(--muted)]">Sentiment score comparison across the peer set.</div>
                  </div>
                </div>
                <div className="h-[320px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.competitor_delta} layout="vertical" margin={{ left: 8, right: 8, top: 10, bottom: 10 }}>
                      <XAxis type="number" domain={[-1, 1]} tick={{ fontSize: 11, fill: "var(--muted)" }} />
                      <YAxis type="category" dataKey="brand" width={90} tick={{ fontSize: 12, fill: "var(--foreground)" }} />
                      <Tooltip />
                      <Bar dataKey="score" radius={[0, 12, 12, 0]}>
                        {data.competitor_delta.map((entry) => (
                          <Cell key={entry.brand} fill={scoreColor(entry.score)} opacity={entry.is_primary ? 1 : 0.55} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="space-y-6">
                <div className="themed-card rounded-[28px] p-5">
                  <div className="mb-4 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">
                    Forecast Snapshot
                  </div>
                  <div className="mb-4 text-lg font-semibold text-[var(--foreground)]">{data.forecast_label || "Demand outlook"}</div>
                  <div className="grid gap-3 sm:grid-cols-3">
                    {[
                      { label: "30 days", value: data.forecast_30d },
                      { label: "60 days", value: data.forecast_60d },
                      { label: "90 days", value: data.forecast_90d },
                    ].map((item) => (
                      <div key={item.label} className="rounded-2xl bg-[var(--input-bg)] p-4 text-center">
                        <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">{item.label}</div>
                        <div className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
                          {fmtForecastMetric(item.value, data.forecast_label)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="themed-card rounded-[28px] p-5">
                  <div className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--accent)]">Executive Brief</div>
                  <p className="text-sm leading-7 text-[var(--foreground)]">{data.insight_report}</p>
                </div>
              </div>
            </section>

            <section className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
              <div className="themed-card rounded-[28px] p-5">
                <div className="mb-4 text-xs font-semibold uppercase tracking-[0.2em]" style={{ color: "var(--danger)" }}>Anomalies</div>
                <div className="space-y-3">
                  {data.anomalies.length > 0 ? (
                    data.anomalies.map((item, index) => (
                      <div
                        key={`${item.text}-${index}`}
                        className="rounded-2xl border p-4"
                        style={{
                          borderColor: isDark ? "#4a2b16" : "var(--danger)",
                          background: isDark ? "#2a1a0e" : "var(--danger-soft)",
                        }}
                      >
                        <div className="mb-2 flex items-center justify-between gap-3">
                          <span
                            className="rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em]"
                            style={{
                              background: isDark
                                ? item.direction.toLowerCase() === "spike"
                                  ? "#0a3a1a"
                                  : "#3a0a0a"
                                : "var(--card)",
                              color: isDark
                                ? item.direction.toLowerCase() === "spike"
                                  ? "#4ade80"
                                  : "#f87171"
                                : "var(--danger)",
                            }}
                          >
                            {item.direction} z={item.z_score}
                          </span>
                          <span className="text-xs font-medium" style={{ color: isDark ? "#a0a0a0" : "var(--danger)" }}>{item.severity}</span>
                        </div>
                        <p className="text-sm leading-6" style={{ color: isDark ? "#e0c9b0" : "var(--foreground)" }}>
                          {item.text}
                        </p>
                      </div>
                    ))
                  ) : (
                    <div className="rounded-2xl bg-[var(--input-bg)] p-4 text-sm text-[var(--muted)]">No major sentiment anomalies detected.</div>
                  )}
                </div>
              </div>

              <div className="themed-card rounded-[28px] p-5">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Top Headlines</div>
                    <div className="text-sm text-[var(--muted)]">FinBERT label, score, and confidence for each headline.</div>
                  </div>
                </div>
                <div className="space-y-3">
                  {data.top_headlines.map((headline, index) => {
                    const expanded = expandedHeadlines[index];
                    return (
                      <button
                        key={`${headline.text}-${index}`}
                        type="button"
                        onClick={() => toggleHeadline(index)}
                        className="themed-surface w-full rounded-2xl px-4 py-4 text-left hover:border-[var(--accent)]"
                      >
                        <div className="flex flex-wrap items-center gap-3">
                          <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] ${badgeClasses(headline.label)}`}>
                            {headline.label}
                          </span>
                          <span className="text-sm font-semibold" style={{ color: scoreColor(headline.score) }}>
                            {headline.score > 0 ? "+" : ""}
                            {headline.score.toFixed(2)}
                          </span>
                          <span className="rounded-full bg-[var(--input-bg)] px-3 py-1 text-xs font-medium text-[var(--foreground)]">
                            Confidence {fmtConfidence(headline.confidence)}
                          </span>
                        </div>
                        <p className={`mt-3 text-sm leading-6 text-[var(--foreground)] ${expanded ? "" : "line-clamp-2"}`}>
                          {headline.text}
                        </p>
                        <div className="mt-2 text-xs font-medium text-[var(--accent)]">{expanded ? "Show less" : "Show full headline"}</div>
                      </button>
                    );
                  })}
                </div>
              </div>
            </section>
          </>
        )}
      </div>
      </main>
    </>
  );
}
