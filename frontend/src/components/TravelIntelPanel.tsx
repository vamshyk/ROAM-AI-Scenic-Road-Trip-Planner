
import type { ReactNode } from "react";
import type { TravelIntel as TravelIntelType, Weather } from "../types";

import {
  Fuel,
  Coffee,
  Eye,
  Wind,
  Droplets,
  AlertTriangle,
} from "lucide-react";

interface TravelIntelProps {
  intel: TravelIntelType;
  days: number;
}

const RISK_COLORS: Record<string, string> = {
  Low: "#81c784",
  Moderate: "#e6a94e",
  High: "#ef5350",
};

function WeatherCard({
  weather,
  label,
}: {
  weather: Weather;
  label: string;
}) {
  const curr = weather.current;
  const forecast = weather.daily_forecast.slice(0, 5);

  return (
    <div
      style={{
        flex: 1,
        minWidth: "220px",
        padding: "16px",
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.09)",
        borderRadius: "10px",
      }}
    >
      <span className="section-label">{label.toUpperCase()}</span>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "10px",
          marginTop: "10px",
        }}
      >
        <span style={{ fontSize: "28px" }}>{curr.icon}</span>

        <div>
          <div
            style={{
              fontSize: "20px",
              fontWeight: 700,
              fontFamily: "Manrope, sans-serif",
            }}
          >
            {curr.temperature_c !== null
              ? `${curr.temperature_c}°C`
              : "—"}
          </div>

          <div style={{ fontSize: "11px", color: "#9da398" }}>
            {curr.description}
          </div>
        </div>

        <div style={{ marginLeft: "auto", textAlign: "right" }}>
          {curr.wind_kmh !== null && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "4px",
                fontSize: "10px",
                color: "#9da398",
              }}
            >
              <Wind size={11} /> {curr.wind_kmh} km/h
            </div>
          )}

          {curr.humidity_pct !== null && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "4px",
                fontSize: "10px",
                color: "#9da398",
                marginTop: "2px",
              }}
            >
              <Droplets size={11} /> {curr.humidity_pct}%
            </div>
          )}
        </div>
      </div>

      {weather.fog_risk !== "Low" && (
        <div
          style={{
            marginTop: "8px",
            padding: "6px 10px",
            background: "rgba(230,169,78,0.08)",
            borderRadius: "5px",
            fontSize: "10px",
            color: "#e6a94e",
            display: "flex",
            alignItems: "center",
            gap: "5px",
          }}
        >
          <AlertTriangle size={11} />
          Fog risk: {weather.fog_risk}
        </div>
      )}

      <div
        style={{
          display: "flex",
          gap: "6px",
          marginTop: "12px",
          overflowX: "auto",
          paddingBottom: "4px",
        }}
      >
        {forecast.map((day) => (
          <div
            key={day.date}
            style={{
              flex: "0 0 auto",
              textAlign: "center",
              padding: "8px 6px",
              borderRadius: "6px",
              background: "rgba(255,255,255,0.04)",
              minWidth: "46px",
            }}
          >
            <div
              style={{
                fontSize: "8px",
                color: "#9da398",
                marginBottom: "4px",
              }}
            >
              {new Date(day.date).toLocaleDateString("en-IN", {
                weekday: "short",
              })}
            </div>

            <div style={{ fontSize: "16px" }}>{day.icon}</div>

            <div style={{ fontSize: "9px", marginTop: "3px" }}>
              <span style={{ color: "#e2ad77" }}>
                {day.temp_max_c ?? "—"}°
              </span>
              <span style={{ color: "#9da398" }}>
                {" "}/ {day.temp_min_c ?? "—"}°
              </span>
            </div>

            {day.precipitation_mm > 0 && (
              <div
                style={{
                  fontSize: "8px",
                  color: RISK_COLORS[day.rain_risk] ?? "#9da398",
                  marginTop: "2px",
                }}
              >
                {day.precipitation_mm}mm
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function StopSummary({
  count,
  icon,
  label,
  color,
}: {
  count: number;
  icon: ReactNode;
  label: string;
  color: string;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "8px",
        padding: "10px 14px",
        borderRadius: "8px",
        background: `${color}0D`,
        border: `1px solid ${color}25`,
      }}
    >
      <div style={{ color }}>{icon}</div>

      <div>
        <div style={{ fontSize: "16px", fontWeight: 700, color }}>
          {count}
        </div>
        <div
          style={{
            fontSize: "9px",
            color: "#9da398",
            letterSpacing: "0.5px",
          }}
        >
          {label}
        </div>
      </div>
    </div>
  );
}

export default function TravelIntelPanel({
  intel,
}: TravelIntelProps) {
  const riskColor =
    RISK_COLORS[intel.trip_rain_risk] ?? "#9da398";

  const stops = intel.stops;

  return (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "10px",
          padding: "12px 16px",
          marginBottom: "18px",
          borderRadius: "8px",
          background: `${riskColor}0D`,
          border: `1px solid ${riskColor}30`,
        }}
      >
        <Droplets size={15} color={riskColor} />

        <div>
          <span
            style={{
              fontSize: "10px",
              letterSpacing: "1px",
              color: riskColor,
            }}
          >
            TRIP RAIN RISK
          </span>

          <p
            style={{
              fontSize: "13px",
              fontWeight: 600,
              color: riskColor,
              margin: "2px 0 0",
            }}
          >
            {intel.trip_rain_risk}
          </p>
        </div>

        {intel.trip_rain_risk !== "Low" && (
          <p
            style={{
              fontSize: "11px",
              color: "#9da398",
              marginLeft: "auto",
            }}
          >
            Check the forecast before heading out.
          </p>
        )}
      </div>

      {(intel.origin_weather || intel.destination_weather) && (
        <div
          style={{
            display: "flex",
            gap: "12px",
            flexWrap: "wrap",
            marginBottom: "18px",
          }}
        >
          {intel.origin_weather && (
            <WeatherCard
              weather={intel.origin_weather}
              label="Origin weather"
            />
          )}

          {intel.destination_weather && (
            <WeatherCard
              weather={intel.destination_weather}
              label="Destination weather"
            />
          )}
        </div>
      )}

      {stops && (
        <div>
          <span
            className="section-label"
            style={{ marginBottom: "10px", display: "block" }}
          >
            STOPS ALONG THE ROUTE
          </span>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))",
              gap: "10px",
              marginTop: "8px",
            }}
          >
            <StopSummary
              count={intel.fuel_station_count}
              icon={<Fuel size={15} />}
              label="FUEL STATIONS"
              color="#e6a94e"
            />

            <StopSummary
              count={intel.food_stop_count}
              icon={<Coffee size={15} />}
              label="FOOD STOPS"
              color="#81c784"
            />

            <StopSummary
              count={intel.viewpoint_count}
              icon={<Eye size={15} />}
              label="VIEWPOINTS"
              color="#29b6f6"
            />
          </div>

          {stops.viewpoints && stops.viewpoints.length > 0 && (
            <div style={{ marginTop: "14px" }}>
              <span className="section-label">
                FEATURED VIEWPOINTS
              </span>

              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "6px",
                  marginTop: "8px",
                }}
              >
                {stops.viewpoints.slice(0, 6).map((viewpoint, index) => (
                  <span
                    key={index}
                    style={{
                      fontSize: "10px",
                      padding: "4px 9px",
                      borderRadius: "4px",
                      background: "rgba(41,182,246,0.10)",
                      border: "1px solid rgba(41,182,246,0.25)",
                      color: "#29b6f6",
                    }}
                  >
                    👁️ {viewpoint.name || "Viewpoint"}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
