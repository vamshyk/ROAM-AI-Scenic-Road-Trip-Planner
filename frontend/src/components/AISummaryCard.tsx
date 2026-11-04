
import type { AISummary } from "../types";
import { Sparkles } from "lucide-react";

interface AISummaryProps {
  summary: AISummary;
  origin: string;
  destination: string;
}

export default function AISummaryCard({
  summary,
  origin,
  destination,
}: AISummaryProps) {
  const isAI = summary.source === "gemini";

  // Convert **bold** Markdown text into styled spans.
  const renderText = (text: string) => {
    const parts = text.split(/(\*\*.*?\*\*)/g);

    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={i} style={{ color: "#e2ad77", fontWeight: 600 }}>
            {part.slice(2, -2)}
          </strong>
        );
      }

      return <span key={i}>{part}</span>;
    });
  };

  return (
    <div
      style={{
        padding: "22px",
        background: "rgba(214,164,107,0.05)",
        border: "1px solid rgba(214,164,107,0.20)",
        borderRadius: "12px",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "16px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "9px" }}>
          <div
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "8px",
              background: "#d6a46b18",
              border: "1px solid #d6a46b40",
              display: "grid",
              placeItems: "center",
              color: "#d6a46b",
            }}
          >
            <Sparkles size={15} />
          </div>

          <div>
            <div
              style={{
                fontSize: "11px",
                fontWeight: 600,
                color: "#e2ad77",
              }}
            >
              ROAM AI TRIP SUMMARY
            </div>

            <div
              style={{
                fontSize: "9px",
                color: "#9da398",
                marginTop: "1px",
                letterSpacing: "0.5px",
              }}
            >
              {origin} → {destination}
            </div>
          </div>
        </div>

        <span
          style={{
            fontSize: "8px",
            letterSpacing: "1px",
            padding: "3px 8px",
            borderRadius: "3px",
            background: isAI
              ? "rgba(230,169,78,0.12)"
              : "rgba(255,255,255,0.06)",
            border: `1px solid ${isAI
                ? "rgba(230,169,78,0.30)"
                : "rgba(255,255,255,0.12)"
              }`,
            color: isAI ? "#e6a94e" : "#9da398",
          }}
        >
          {isAI ? "✦ GEMINI AI" : "AUTO GENERATED"}
        </span>
      </div>

      {/* Summary text */}
      <div
        style={{
          fontSize: "13px",
          lineHeight: "1.9",
          color: "#d4d7cf",
          whiteSpace: "pre-line",
        }}
      >
        {renderText(summary.summary)}
      </div>

      {/* Note */}
      {summary.note && (
        <p
          style={{
            marginTop: "14px",
            fontSize: "10px",
            color: "#9da398",
            lineHeight: 1.6,
            padding: "8px 12px",
            background: "rgba(255,255,255,0.03)",
            borderRadius: "5px",
            border: "1px solid rgba(255,255,255,0.07)",
          }}
        >
          💡 {summary.note}
        </p>
      )}
    </div>
  );
}
