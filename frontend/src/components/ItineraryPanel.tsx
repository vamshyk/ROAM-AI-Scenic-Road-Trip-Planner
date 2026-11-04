
import { useState } from "react";
import type { ReactNode } from "react";
import {
  ChevronDown,
  ChevronUp,
  MapPin,
  Coffee,
  Fuel,
  Eye,
  Bed,
} from "lucide-react";

import type { Itinerary, POI } from "../types";

interface ItineraryProps {
  itinerary: Itinerary;
  vehicle: string;
}

const POI_ICONS: Record<
  string,
  { icon: ReactNode; label: string; color: string }
> = {
  fuel: {
    icon: <Fuel size={13} />,
    label: "Fuel",
    color: "#e6a94e",
  },
  food: {
    icon: <Coffee size={13} />,
    label: "Food",
    color: "#81c784",
  },
  viewpoint: {
    icon: <Eye size={13} />,
    label: "Viewpoint",
    color: "#29b6f6",
  },
  hotel: {
    icon: <Bed size={13} />,
    label: "Stay",
    color: "#ce93d8",
  },
  medical: {
    icon: <MapPin size={13} />,
    label: "Medical",
    color: "#ef9a9a",
  },
};

function StopPill({ stop }: { stop: POI }) {
  const type = stop.poi_type ?? stop.type ?? "other";

  const meta = POI_ICONS[type] ?? {
    icon: <MapPin size={13} />,
    label: type,
    color: "#9da398",
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "5px",
        padding: "4px 9px",
        borderRadius: "4px",
        background: `${meta.color}12`,
        border: `1px solid ${meta.color}30`,
        color: meta.color,
        fontSize: "10px",
        letterSpacing: "0.5px",
      }}
    >
      {meta.icon}
      {stop.name || meta.label}
    </div>
  );
}

type ItineraryDay = Itinerary["days"][number];

function DayCard({
  day,
  isOpen,
  onToggle,
}: {
  day: ItineraryDay;
  isOpen: boolean;
  onToggle: () => void;
}) {
  return (
    <div
      style={{
        border: "1px solid rgba(255,255,255,0.10)",
        borderRadius: "10px",
        overflow: "hidden",
        background: "rgba(255,255,255,0.02)",
      }}
    >
      <button
        onClick={onToggle}
        style={{
          width: "100%",
          padding: "16px 18px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: "transparent",
          border: "none",
          color: "inherit",
          textAlign: "left",
          cursor: "pointer",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "6px",
              background: "#d6a46b18",
              border: "1px solid #d6a46b40",
              display: "grid",
              placeItems: "center",
              color: "#d6a46b",
              fontSize: "11px",
              fontWeight: 700,
              flexShrink: 0,
            }}
          >
            D{day.day}
          </div>

          <div>
            <div style={{ fontSize: "13px", fontWeight: 600 }}>
              {day.from} → {day.to}
            </div>

            <div
              style={{
                fontSize: "10px",
                color: "#9da398",
                marginTop: "2px",
              }}
            >
              {day.distance_km} km · {day.drive_time}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span
            style={{
              fontSize: "10px",
              color: "#9da398",
              textAlign: "right",
              maxWidth: "160px",
            }}
          >
            {day.highlights}
          </span>

          {isOpen ? (
            <ChevronUp size={16} color="#9da398" />
          ) : (
            <ChevronDown size={16} color="#9da398" />
          )}
        </div>
      </button>

      {isOpen && (
        <div
          style={{
            padding: "0 18px 18px",
            borderTop: "1px solid rgba(255,255,255,0.06)",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
              gap: "12px",
              padding: "14px 0",
            }}
          >
            <div>
              <span className="section-label">DISTANCE</span>
              <p style={{ marginTop: "5px", fontSize: "15px", fontWeight: 600 }}>
                {day.distance_km} km
              </p>
            </div>

            <div>
              <span className="section-label">DRIVE TIME</span>
              <p style={{ marginTop: "5px", fontSize: "15px", fontWeight: 600 }}>
                {day.drive_time}
              </p>
            </div>

            <div>
              <span className="section-label">OVERNIGHT</span>
              <p
                style={{
                  marginTop: "5px",
                  fontSize: "14px",
                  color: "#d6a46b",
                  display: "flex",
                  alignItems: "center",
                  gap: "5px",
                }}
              >
                <Bed size={13} />
                {day.overnight_stay.name}
              </p>
            </div>
          </div>

          {day.suggested_stops.length > 0 && (
            <div>
              <span className="section-label">STOPS ALONG THE WAY</span>

              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "6px",
                  marginTop: "8px",
                }}
              >
                {day.suggested_stops.map((stop, index) => (
                  <StopPill key={index} stop={stop} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ItineraryPanel({
  itinerary,
  vehicle,
}: ItineraryProps) {
  const [openDay, setOpenDay] = useState<number | null>(1);

  return (
    <div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))",
          gap: "12px",
          marginBottom: "20px",
          padding: "16px",
          background: "rgba(255,255,255,0.025)",
          borderRadius: "10px",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <div>
          <span className="section-label">TOTAL DISTANCE</span>
          <p style={{ marginTop: "6px", fontSize: "16px", fontWeight: 600 }}>
            {itinerary.total_distance_km} km
          </p>
        </div>

        <div>
          <span className="section-label">TOTAL DRIVE</span>
          <p style={{ marginTop: "6px", fontSize: "16px", fontWeight: 600 }}>
            {itinerary.total_drive_time}
          </p>
        </div>

        <div>
          <span className="section-label">PER DAY</span>
          <p style={{ marginTop: "6px", fontSize: "16px", fontWeight: 600 }}>
            ~{itinerary.km_per_day} km
          </p>
        </div>

        <div>
          <span className="section-label">VEHICLE</span>
          <p
            style={{
              marginTop: "6px",
              fontSize: "16px",
              fontWeight: 600,
              textTransform: "capitalize",
            }}
          >
            {vehicle}
          </p>
        </div>
      </div>

      {itinerary.comfort_note && (
        <div
          style={{
            padding: "10px 14px",
            marginBottom: "16px",
            background: "rgba(230,169,78,0.08)",
            border: "1px solid rgba(230,169,78,0.25)",
            borderRadius: "6px",
            fontSize: "11px",
            color: "#e6a94e",
            lineHeight: 1.6,
          }}
        >
          ⚠️ {itinerary.comfort_note}
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {itinerary.days.map((day) => (
          <DayCard
            key={day.day}
            day={day}
            isOpen={openDay === day.day}
            onToggle={() =>
              setOpenDay(openDay === day.day ? null : day.day)
            }
          />
        ))}
      </div>
    </div>
  );
}
