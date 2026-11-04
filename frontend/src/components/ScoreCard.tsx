
import type { ScenicFeatures } from "../types";

interface ScoreCardProps {
  scenicScore: number | null;
  mlScore: number | null;
  environment: string | null;
  features: ScenicFeatures | null;
  scoringStatus: string;
}

const ENV_ICONS: Record<string, string> = {
  Forest: "🌲",
  "Forest & Mountain": "🏔️",
  Mountain: "⛰️",
  "Mountain & River": "🌊",
  Coastal: "🌊",
  Rural: "🌾",
  Urban: "🏙️",
  Highway: "🛣️",
  Mixed: "🗺️",
};

const ENV_COLORS: Record<string, string> = {
  Forest: "#4caf50",
  "Forest & Mountain": "#66bb6a",
  Mountain: "#78909c",
  "Mountain & River": "#26c6da",
  Coastal: "#29b6f6",
  Rural: "#a5d6a7",
  Urban: "#ef9a9a",
  Highway: "#bdbdbd",
  Mixed: "#d6a46b",
};

function ScoreBar({
  label,
  value,
  maximum,
  color,
}: {
  label: string;
  value: number;
  maximum: number;
  color: string;
}) {
  const percentage = Math.min(
    Math.max((value / maximum) * 100, 0),
    100
  );

  return (
    <div style={{ marginBottom: "12px" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: "5px",
        }}
      >
        <span
          style={{
            fontSize: "10px",
            color: "#9da398",
            letterSpacing: "1px",
          }}
        >
          {label}
        </span>

        <span style={{ fontSize: "10px", color: "#e2ad77" }}>
          {value.toFixed(1)} / {maximum}
        </span>
      </div>

      <div
        style={{
          height: "5px",
          background: "rgba(255,255,255,0.08)",
          borderRadius: "3px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${percentage}%`,
            background: color,
            borderRadius: "3px",
            transition: "width 0.6s ease",
          }}
        />
      </div>
    </div>
  );
}

export default function ScoreCard({
  scenicScore,
  mlScore,
  environment,
  features,
  scoringStatus,
}: ScoreCardProps) {
  // Local OSM score is the primary baseline score.
  const displayScore = scenicScore ?? mlScore;
  const displayEnv = environment ?? "Mixed";

  const envIcon = ENV_ICONS[displayEnv] ?? "🗺️";
  const envColor = ENV_COLORS[displayEnv] ?? "#d6a46b";

  const featureScores = features?.feature_scores;
  const isMLAvailable = mlScore !== null;
  const isOSMScored = scenicScore !== null;

  return (
    <div
      style={{
        padding: "18px",
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.10)",
        borderRadius: "12px",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "14px",
        }}
      >
        <div>
          <span className="section-label">SCENIC SCORE</span>

          {displayScore !== null ? (
            <div
              style={{
                display: "flex",
                alignItems: "baseline",
                gap: "6px",
                marginTop: "6px",
              }}
            >
              <span
                style={{
                  fontSize: "32px",
                  fontFamily: "Manrope, sans-serif",
                  color: "#e6a94e",
                  fontWeight: 700,
                }}
              >
                {displayScore.toFixed(1)}
              </span>

              <span style={{ fontSize: "14px", color: "#9da398" }}>
                /100
              </span>
            </div>
          ) : (
            <div style={{ marginTop: "8px", fontSize: "13px", color: "#9da398" }}>
              Not available
            </div>
          )}
        </div>

        {/* Environment classification */}
        <div
          style={{
            textAlign: "center",
            padding: "10px 14px",
            background: `${envColor}14`,
            border: `1px solid ${envColor}40`,
            borderRadius: "8px",
          }}
        >
          <div style={{ fontSize: "22px" }}>{envIcon}</div>
          <div
            style={{
              fontSize: "9px",
              color: envColor,
              letterSpacing: "1px",
              marginTop: "4px",
            }}
          >
            {displayEnv.toUpperCase()}
          </div>
        </div>
      </div>

      {/* Scoring source */}
      <div
        style={{
          display: "flex",
          gap: "6px",
          flexWrap: "wrap",
          marginBottom: "14px",
        }}
      >
        {isOSMScored && (
          <span
            style={{
              fontSize: "8px",
              letterSpacing: "1px",
              padding: "3px 8px",
              borderRadius: "3px",
              background: "rgba(76,175,80,0.10)",
              border: "1px solid rgba(76,175,80,0.25)",
              color: "#81c784",
            }}
          >
            LOCAL OSM BASELINE
          </span>
        )}

        {isMLAvailable && (
          <span
            style={{
              fontSize: "8px",
              letterSpacing: "1px",
              padding: "3px 8px",
              borderRadius: "3px",
              background: "rgba(230,169,78,0.12)",
              border: "1px solid rgba(230,169,78,0.30)",
              color: "#e6a94e",
            }}
          >
            EXPERIMENTAL ML
          </span>
        )}
      </div>

      {/* Separate experimental ML prediction */}
      {isOSMScored && isMLAvailable && (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "10px 12px",
            marginBottom: "16px",
            background: "rgba(230,169,78,0.06)",
            border: "1px solid rgba(230,169,78,0.18)",
            borderRadius: "8px",
          }}
        >
          <div>
            <div style={{ fontSize: "10px", color: "#9da398" }}>
              EXPERIMENTAL ML PREDICTION
            </div>
            <div style={{ fontSize: "9px", color: "#777f75", marginTop: "3px" }}>
              Not yet validated
            </div>
          </div>

          <div style={{ fontSize: "18px", color: "#e6a94e", fontWeight: 700 }}>
            {mlScore!.toFixed(1)}/100
          </div>
        </div>
      )}

      {/* Feature score breakdown */}
      {featureScores && (
        <div>
          <ScoreBar
            label="FOREST"
            value={featureScores.forest_score}
            maximum={40}
            color="#4caf50"
          />

          <ScoreBar
            label="WATER"
            value={featureScores.water_score}
            maximum={25}
            color="#29b6f6"
          />

          <ScoreBar
            label="ATTRACTIONS"
            value={featureScores.attraction_score}
            maximum={20}
            color="#e6a94e"
          />

          <ScoreBar
            label="TRACK ROADS"
            value={featureScores.track_score}
            maximum={15}
            color="#78909c"
          />
        </div>
      )}

      {/* OSM feature counts */}
      {features && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
            gap: "8px",
            marginTop: "14px",
            paddingTop: "14px",
            borderTop: "1px solid rgba(255,255,255,0.10)",
          }}
        >
          {[
            {
              label: "FOREST FEATURES",
              value: features.nearby_forest_count,
            },
            {
              label: "WATER FEATURES",
              value: features.nearby_water_count,
            },
            {
              label: "ATTRACTIONS",
              value: features.nearby_tourist_places,
            },
          ].map((item) => (
            <div key={item.label}>
              <div
                style={{
                  fontSize: "18px",
                  color: "#e6a94e",
                  fontWeight: 700,
                }}
              >
                {item.value}
              </div>

              <div
                style={{
                  fontSize: "8px",
                  color: "#9da398",
                  letterSpacing: "0.5px",
                  marginTop: "3px",
                }}
              >
                {item.label}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Methodology note */}
      {features && (
        <p
          style={{
            fontSize: "10px",
            color: "#9da398",
            marginTop: "12px",
            lineHeight: 1.6,
          }}
        >
          Baseline heuristic score calculated using local Karnataka
          OpenStreetMap features. Not yet validated against measured
          scenic quality.
        </p>
      )}

      {!features && scoringStatus && (
        <p
          style={{
            fontSize: "10px",
            color: "#9da398",
            marginTop: "10px",
          }}
        >
          {scoringStatus}
        </p>
      )}
    </div>
  );
}
