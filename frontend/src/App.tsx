
import { useState } from "react";
import type { ReactNode } from "react";
import {
  ArrowDown, ArrowRight, ArrowUpRight, Compass, MapPin,
  Mountain, CalendarDays, Car, Bike, Sparkles, Menu,
  Fuel, Coffee, Route, Heart, ChevronRight, Navigation,
  Map, BarChart2, Brain,
} from "lucide-react";

import RouteMap from "./components/RouteMap";
import ScoreCard from "./components/ScoreCard";
import ItineraryPanel from "./components/ItineraryPanel";
import TravelIntelPanel from "./components/TravelIntelPanel";
import AISummaryCard from "./components/AISummaryCard";

import type { TripResult, RouteOption } from "./types";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const PREFERENCE_OPTIONS = [
  { value: "explorer", label: "Explorer", hint: "Prioritise scenic beauty" },
  { value: "balanced", label: "Balanced", hint: "Mix of scenic & efficient" },
  { value: "efficient", label: "Efficient", hint: "Fastest, most direct" },
  { value: "budget", label: "Budget", hint: "Minimise tolls & cost" },
];

const destinations = [
  {
    name: "Coorg",
    subtitle: "The Scotland of India",
    distance: "265 km from Bengaluru",
    image: "https://images.unsplash.com/photo-1511497584788-876760111969?w=900&q=85",
    tag: "FOREST ESCAPE",
  },
  {
    name: "Chikmagalur",
    subtitle: "Into the coffee mountains",
    distance: "245 km from Bengaluru",
    image: "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=900&q=85",
    tag: "MOUNTAIN ROUTE",
  },
  {
    name: "Sakleshpur",
    subtitle: "Where the Western Ghats begin",
    distance: "220 km from Bengaluru",
    image: "https://images.unsplash.com/photo-1472396961693-142e6e269027?w=900&q=85",
    tag: "SCENIC DRIVE",
  },
];

type ActiveTab = "map" | "itinerary" | "weather" | "summary";

function TabButton({
  id,
  active,
  onClick,
  icon,
  label,
}: {
  id: ActiveTab;
  active: boolean;
  onClick: (tab: ActiveTab) => void;
  icon: ReactNode;
  label: string;
}) {
  return (
    <button
      onClick={() => onClick(id)}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "7px",
        padding: "9px 14px",
        borderRadius: "6px",
        border: active
          ? "1px solid #d6a46b"
          : "1px solid rgba(255,255,255,0.12)",
        background: active ? "#d6a46b18" : "transparent",
        color: active ? "#e6a94e" : "#9da398",
        fontSize: "11px",
        fontWeight: active ? 600 : 400,
        cursor: "pointer",
        transition: "all 0.2s",
      }}
    >
      {icon}
      {label}
    </button>
  );
}

function App() {
  const [vehicle, setVehicle] = useState("car");
  const [days, setDays] = useState(3);
  const [origin, setOrigin] = useState("Bengaluru");
  const [destination, setDestination] = useState("");
  const [preference, setPreference] = useState("balanced");
  const [notice, setNotice] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [tripResult, setTripResult] = useState<TripResult | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>("map");

  const selectedRoute: RouteOption | null =
    tripResult?.routes.find((route) => route.route_id === selectedId) ??
    tripResult?.routes[0] ??
    null;

  const handlePlanTrip = async () => {
    if (!origin.trim() || !destination.trim()) {
      setNotice("Please enter both your starting point and destination.");
      setTripResult(null);
      setSelectedId(null);
      return;
    }

    setIsLoading(true);
    setNotice("");
    setTripResult(null);
    setSelectedId(null);

    try {
      const response = await fetch(`${API_URL}/api/plan-trip`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          origin: origin.trim(),
          destination: destination.trim(),
          days,
          vehicle,
          preference,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || "Unable to calculate the route."
        );
      }

      const data: TripResult = await response.json();

      if (!data.routes || data.routes.length === 0) {
        throw new Error(
          "No road routes were returned by the routing service."
        );
      }

      setTripResult(data);
      setSelectedId(data.recommended_route_id);
      setNotice(data.message);
      setActiveTab("map");
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Unable to connect to ROAM. Please check that the backend is running."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = Math.round(minutes % 60);

    return hours === 0
      ? `${remainingMinutes} min`
      : `${hours} hr ${remainingMinutes} min`;
  };

  return (
    <main className="app">
      {/* NAVIGATION */}
      <nav className="navbar">
        <a href="#home" className="brand">
          <span className="brand-icon">
            <Compass size={23} />
          </span>
          <span>
            <strong>ROAM</strong>
            <small>BEYOND THE ROUTE</small>
          </span>
        </a>

        <div className="nav-links">
          <a href="#home" className="active">Discover</a>
          <a href="#planner">Plan a trip</a>
          <a href="#destinations">Destinations</a>
          <a href="#about">About us</a>
        </div>

        <button
          className="nav-button"
          onClick={() =>
            document.getElementById("planner")?.scrollIntoView({
              behavior: "smooth",
            })
          }
        >
          Start exploring <ArrowUpRight size={16} />
        </button>

        <button className="mobile-menu" aria-label="Open menu">
          <Menu size={24} />
        </button>
      </nav>

      {/* HERO */}
      <section className="hero" id="home">
        <div className="hero-overlay" />

        <div className="hero-content">
          <div className="eyebrow">
            <span className="live-dot" />
            YOUR NEXT ADVENTURE STARTS HERE
          </div>

          <h1>
            Roads less<br />
            travelled. <span>Stories</span><br />
            worth telling.
          </h1>

          <p className="hero-description">
            Discover breathtaking routes, hidden gems and unforgettable
            journeys. Let AI find the beautiful way there.
          </p>

          <div className="hero-actions">
            <button
              className="primary-button"
              onClick={() =>
                document.getElementById("planner")?.scrollIntoView({
                  behavior: "smooth",
                })
              }
            >
              Plan your journey <ArrowRight size={18} />
            </button>

            <a href="#destinations" className="text-button">
              Explore destinations <ArrowDown size={16} />
            </a>
          </div>

          <div className="hero-stats">
            <div><strong>AI</strong><span>Powered routes</span></div>
            <div><strong>360°</strong><span>Trip discovery</span></div>
            <div><strong>∞</strong><span>Ways to explore</span></div>
          </div>
        </div>

        <div className="hero-location">
          <MapPin size={15} />
          <span>WESTERN GHATS, INDIA</span>
        </div>

        <div className="scroll-indicator">
          SCROLL TO EXPLORE <ArrowDown size={14} />
        </div>
      </section>

      {/* TRIP PLANNER */}
      <section className="planner-section" id="planner">
        <div className="section-heading">
          <div>
            <span className="section-label">YOUR JOURNEY BEGINS</span>
            <h2>Where are we <span>heading?</span></h2>
            <p>Tell us a little about your adventure. We'll find the way.</p>
          </div>

          <div className="ai-label">
            <Sparkles size={16} /> AI TRIP PLANNER
          </div>
        </div>

        <div className="planner-card">
          <div className="input-grid">
            <label className="location-input">
              <span><Navigation size={15} /> STARTING POINT</span>
              <div>
                <MapPin size={19} />
                <input
                  value={origin}
                  onChange={(event) => setOrigin(event.target.value)}
                  placeholder="Where from?"
                />
              </div>
            </label>

            <div className="swap-icon">
              <ArrowRight size={19} />
            </div>

            <label className="location-input">
              <span><MapPin size={15} /> DESTINATION</span>
              <div>
                <MapPin size={19} />
                <input
                  value={destination}
                  onChange={(event) => setDestination(event.target.value)}
                  placeholder="Where to?"
                />
              </div>
            </label>

            <div className="duration-input">
              <span><CalendarDays size={15} /> DURATION</span>
              <div className="duration-control">
                <button
                  onClick={() => setDays(Math.max(1, days - 1))}
                  aria-label="Decrease duration"
                >
                  −
                </button>

                <strong>
                  {days} {days === 1 ? "Day" : "Days"}
                </strong>

                <button
                  onClick={() => setDays(Math.min(30, days + 1))}
                  aria-label="Increase duration"
                >
                  +
                </button>
              </div>
            </div>
          </div>

          {/* PREFERENCES */}
          <div style={{ marginTop: "20px" }}>
            <span
              className="section-label"
              style={{ display: "block", marginBottom: "10px" }}
            >
              TRIP PREFERENCE
            </span>

            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              {PREFERENCE_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  className={
                    preference === option.value ? "vehicle active" : "vehicle"
                  }
                  onClick={() => setPreference(option.value)}
                  title={option.hint}
                  style={{
                    flexDirection: "column",
                    alignItems: "flex-start",
                    padding: "9px 13px",
                    gap: "2px",
                  }}
                >
                  <span style={{ fontWeight: 600, fontSize: "12px" }}>
                    {option.label}
                  </span>
                  <span style={{ fontSize: "9px", opacity: 0.7 }}>
                    {option.hint}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* VEHICLE AND SEARCH */}
          <div className="planner-bottom">
            <div className="vehicle-selection">
              <span>TRAVELLING BY</span>

              <button
                className={vehicle === "car" ? "vehicle active" : "vehicle"}
                onClick={() => setVehicle("car")}
              >
                <Car size={18} /> Car
              </button>

              <button
                className={vehicle === "bike" ? "vehicle active" : "vehicle"}
                onClick={() => setVehicle("bike")}
              >
                <Bike size={18} /> Bike
              </button>
            </div>

            <button
              className="search-button"
              onClick={handlePlanTrip}
              disabled={isLoading}
            >
              <Sparkles size={18} />
              {isLoading ? "Planning your trip…" : "Find my adventure"}
              <ArrowRight size={18} />
            </button>
          </div>

          {notice && (
            <p className="planner-notice" role="status">
              {notice}
            </p>
          )}

          {/* RESULTS */}
          {tripResult && selectedRoute && (
            <div
              style={{
                marginTop: "28px",
                padding: "24px",
                borderRadius: "16px",
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.12)",
              }}
            >
              {/* ROUTE HEADER */}
              <div style={{ marginBottom: "20px" }}>
                <span className="section-label">YOUR ROUTE IS READY</span>

                <h3
                  style={{
                    marginTop: "8px",
                    fontSize: "22px",
                    display: "flex",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: "10px",
                  }}
                >
                  {origin} <ArrowRight size={18} /> {destination}
                </h3>

                <p
                  style={{
                    opacity: 0.7,
                    marginTop: "6px",
                    fontSize: "12px",
                  }}
                >
                  {tripResult.recommendation}
                </p>
              </div>

              {/* TRIP STATS */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
                  gap: "14px",
                  marginBottom: "22px",
                }}
              >
                {[
                  {
                    label: "ROAD DISTANCE",
                    value: `${selectedRoute.distance_km.toFixed(2)} km`,
                  },
                  {
                    label: vehicle === "bike" ? "ESTIMATED RIDE" : "ESTIMATED DRIVE",
                    value: formatTime(selectedRoute.duration_minutes),
                  },
                  {
                    label: "TRIP DURATION",
                    value: `${days} ${days === 1 ? "Day" : "Days"}`,
                  },
                ].map((stat) => (
                  <div key={stat.label}>
                    <span className="section-label">{stat.label}</span>
                    <h2 style={{ marginTop: "8px", fontSize: "20px" }}>
                      {stat.value}
                    </h2>
                  </div>
                ))}
              </div>

              {/* ROUTE SELECTOR */}
              <div style={{ marginBottom: "22px" }}>
                <span className="section-label">AVAILABLE ROUTES</span>
                <h3 style={{ marginTop: "8px", fontSize: "18px" }}>
                  Choose your way.
                </h3>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
                    gap: "12px",
                    marginTop: "14px",
                  }}
                >
                  {tripResult.routes.map((route) => {
                    const env =
                      route.scenic_features?.environment ??
                      route.ml_environment ??
                      "Unknown";

                    // Primary score: local OSM baseline (0–100).
                    const score = route.scenic_score;

                    // Experimental ML prediction, displayed separately.
                    const mlScore = route.ml_scenic_score;

                    const isSelected = selectedId === route.route_id;

                    return (
                      <button
                        key={route.route_id}
                        onClick={() => setSelectedId(route.route_id)}
                        style={{
                          textAlign: "left",
                          padding: "16px",
                          borderRadius: "12px",
                          cursor: "pointer",
                          color: "inherit",
                          background: isSelected
                            ? "rgba(230,169,78,0.12)"
                            : "rgba(255,255,255,0.03)",
                          border: isSelected
                            ? "1px solid #e6a94e"
                            : "1px solid rgba(255,255,255,0.10)",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "flex-start",
                            gap: "8px",
                          }}
                        >
                          <span className="section-label">
                            {route.is_recommended
                              ? "★ RECOMMENDED"
                              : "ALTERNATIVE"}
                          </span>

                          {score != null && (
                            <span
                              style={{
                                fontSize: "11px",
                                color: "#e6a94e",
                                fontWeight: 700,
                                whiteSpace: "nowrap",
                              }}
                            >
                              🌿 {score.toFixed(1)}/100
                            </span>
                          )}
                        </div>

                        {mlScore != null && (
                          <p
                            style={{
                              fontSize: "9px",
                              color: "#9da398",
                              marginTop: "5px",
                            }}
                          >
                            Experimental ML: {mlScore.toFixed(1)}/100
                          </p>
                        )}

                        <h3 style={{ marginTop: "8px", fontSize: "15px" }}>
                          {route.name}
                        </h3>

                        <p
                          style={{
                            fontSize: "10px",
                            color: "#9da398",
                            margin: "4px 0 8px",
                          }}
                        >
                          {env}
                        </p>

                        <p style={{ fontSize: "13px" }}>
                          {route.distance_km.toFixed(2)} km
                        </p>

                        <p
                          style={{
                            fontSize: "12px",
                            opacity: 0.7,
                            marginTop: "3px",
                          }}
                        >
                          {formatTime(route.duration_minutes)}
                        </p>

                        {route.has_toll && (
                          <span
                            style={{
                              fontSize: "9px",
                              color: "#e6a94e",
                              marginTop: "6px",
                              display: "block",
                            }}
                          >
                            Toll road
                          </span>
                        )}

                        <p
                          style={{
                            marginTop: "10px",
                            fontSize: "11px",
                            color: isSelected ? "#d6a46b" : "#9da398",
                          }}
                        >
                          {isSelected ? "✓ Selected" : "Select this route"}
                        </p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* ATTRIBUTION */}
              <div
                style={{
                  fontSize: "11px",
                  opacity: 0.55,
                  lineHeight: 1.7,
                  marginBottom: "22px",
                  paddingBottom: "18px",
                  borderBottom: "1px solid rgba(255,255,255,0.08)",
                }}
              >
                <p>Start: {tripResult.origin.display_name}</p>
                <p>Destination: {tripResult.destination.display_name}</p>
                <p>Routing data: {tripResult.source}</p>
                <p>{tripResult.attribution}</p>
                <p>
                  Note: This is the fastest available{" "}
                  {vehicle === "bike" ? "motorcycle" : "car"} route estimate,
                  not a live traffic prediction.
                </p>
              </div>

              {/* TABS */}
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "8px",
                  marginBottom: "22px",
                }}
              >
                <TabButton
                  id="map"
                  active={activeTab === "map"}
                  onClick={setActiveTab}
                  icon={<Map size={13} />}
                  label="Map"
                />

                <TabButton
                  id="itinerary"
                  active={activeTab === "itinerary"}
                  onClick={setActiveTab}
                  icon={<CalendarDays size={13} />}
                  label={`${days}-Day Itinerary`}
                />

                <TabButton
                  id="weather"
                  active={activeTab === "weather"}
                  onClick={setActiveTab}
                  icon={<BarChart2 size={13} />}
                  label="Travel Intel"
                />

                <TabButton
                  id="summary"
                  active={activeTab === "summary"}
                  onClick={setActiveTab}
                  icon={<Brain size={13} />}
                  label="AI Summary"
                />
              </div>

              {/* MAP TAB */}
              {activeTab === "map" && (
                <div>
                  <span className="section-label">EXPLORE YOUR ROUTE</span>
                  <h3
                    style={{
                      marginTop: "8px",
                      fontSize: "18px",
                      marginBottom: "16px",
                    }}
                  >
                    Your journey, mapped out.
                  </h3>

                  {selectedRoute.scenic_score != null ||
                    selectedRoute.ml_scenic_score != null ? (
                    <div style={{ marginBottom: "16px" }}>
                      <ScoreCard
                        scenicScore={selectedRoute.scenic_score}
                        mlScore={selectedRoute.ml_scenic_score}
                        environment={
                          selectedRoute.scenic_features?.environment ??
                          selectedRoute.ml_environment
                        }
                        features={selectedRoute.scenic_features}
                        scoringStatus={selectedRoute.scenic_score_status}
                      />
                    </div>
                  ) : null}

                  <RouteMap
                    geometry={selectedRoute.geometry}
                    origin={tripResult.origin}
                    destination={tripResult.destination}
                  />

                  {selectedRoute.maneuvers &&
                    selectedRoute.maneuvers.length > 0 && (
                      <details style={{ marginTop: "14px" }}>
                        <summary
                          style={{
                            cursor: "pointer",
                            fontSize: "11px",
                            color: "#9da398",
                            letterSpacing: "1px",
                          }}
                        >
                          TURN-BY-TURN DIRECTIONS (
                          {selectedRoute.maneuvers.length} steps)
                        </summary>

                        <div
                          style={{
                            marginTop: "10px",
                            maxHeight: "240px",
                            overflowY: "auto",
                          }}
                        >
                          {selectedRoute.maneuvers.map((maneuver, index) => (
                            <div
                              key={index}
                              style={{
                                padding: "8px 0",
                                borderBottom:
                                  "1px solid rgba(255,255,255,0.06)",
                                fontSize: "12px",
                                display: "flex",
                                gap: "10px",
                              }}
                            >
                              <span
                                style={{
                                  color: "#d6a46b",
                                  minWidth: "20px",
                                  fontSize: "10px",
                                  paddingTop: "1px",
                                }}
                              >
                                {index + 1}.
                              </span>

                              <span
                                style={{
                                  flex: 1,
                                  color: "#c8ccbf",
                                  lineHeight: 1.5,
                                }}
                              >
                                {maneuver.instruction}
                              </span>

                              <span
                                style={{
                                  color: "#9da398",
                                  fontSize: "10px",
                                  whiteSpace: "nowrap",
                                }}
                              >
                                {maneuver.distance_km} km
                              </span>
                            </div>
                          ))}
                        </div>
                      </details>
                    )}
                </div>
              )}

              {/* ITINERARY TAB */}
              {activeTab === "itinerary" && (
                <div>
                  <span className="section-label">DAY-WISE ITINERARY</span>
                  <h3
                    style={{
                      marginTop: "8px",
                      fontSize: "18px",
                      marginBottom: "16px",
                    }}
                  >
                    Your {days}-day plan.
                  </h3>

                  {tripResult.itinerary ? (
                    <ItineraryPanel
                      itinerary={tripResult.itinerary}
                      vehicle={vehicle}
                    />
                  ) : (
                    <p style={{ color: "#9da398", fontSize: "13px" }}>
                      Itinerary could not be generated for this route.
                    </p>
                  )}
                </div>
              )}

              {/* TRAVEL INTELLIGENCE TAB */}
              {activeTab === "weather" && (
                <div>
                  <span className="section-label">TRAVEL INTELLIGENCE</span>
                  <h3
                    style={{
                      marginTop: "8px",
                      fontSize: "18px",
                      marginBottom: "16px",
                    }}
                  >
                    Weather & stops along the way.
                  </h3>

                  {tripResult.travel_intel ? (
                    <TravelIntelPanel
                      intel={tripResult.travel_intel}
                      days={days}
                    />
                  ) : (
                    <p style={{ color: "#9da398", fontSize: "13px" }}>
                      Travel intelligence could not be loaded.
                    </p>
                  )}
                </div>
              )}

              {/* AI SUMMARY TAB */}
              {activeTab === "summary" && (
                <div>
                  <span className="section-label">AI TRIP SUMMARY</span>
                  <h3
                    style={{
                      marginTop: "8px",
                      fontSize: "18px",
                      marginBottom: "16px",
                    }}
                  >
                    Your adventure, narrated.
                  </h3>

                  {tripResult.ai_summary ? (
                    <AISummaryCard
                      summary={tripResult.ai_summary}
                      origin={origin}
                      destination={destination}
                    />
                  ) : (
                    <p style={{ color: "#9da398", fontSize: "13px" }}>
                      AI summary could not be generated.
                    </p>
                  )}
                </div>
              )}

              {/* WARNINGS */}
              {tripResult.warnings && tripResult.warnings.length > 0 && (
                <details style={{ marginTop: "18px" }}>
                  <summary
                    style={{
                      cursor: "pointer",
                      fontSize: "10px",
                      color: "#9da398",
                      letterSpacing: "1px",
                    }}
                  >
                    {tripResult.warnings.length} NOTICE
                    {tripResult.warnings.length > 1 ? "S" : ""}
                  </summary>

                  <ul style={{ marginTop: "8px", paddingLeft: "16px" }}>
                    {tripResult.warnings.map((warning, index) => (
                      <li
                        key={index}
                        style={{
                          fontSize: "11px",
                          color: "#9da398",
                          lineHeight: 1.7,
                        }}
                      >
                        {warning}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          )}
        </div>
      </section>

      {/* DESTINATIONS */}
      <section className="destinations-section" id="destinations">
        <div className="section-heading destination-heading">
          <div>
            <span className="section-label">HANDPICKED FOR EXPLORERS</span>
            <h2>Find your <span>next escape.</span></h2>
            <p>Places that make you forget about the destination.</p>
          </div>

          <a href="#planner" className="view-all">
            Plan a new adventure <ArrowUpRight size={17} />
          </a>
        </div>

        <div className="destination-grid">
          {destinations.map((place) => (
            <article className="destination-card" key={place.name}>
              <img src={place.image} alt={place.name} />
              <div className="card-shade" />

              <span className="destination-tag">{place.tag}</span>

              <button
                className="favorite-button"
                aria-label={`Save ${place.name}`}
                onClick={(event) =>
                  event.currentTarget.classList.toggle("favorited")
                }
              >
                <Heart size={19} />
              </button>

              <div className="destination-info">
                <span>{place.distance}</span>
                <h3>{place.name}</h3>
                <p>{place.subtitle}</p>

                <button
                  className="explore-link"
                  onClick={() => {
                    setDestination(place.name);
                    document.getElementById("planner")?.scrollIntoView({
                      behavior: "smooth",
                    });
                  }}
                >
                  Explore destination <ArrowUpRight size={16} />
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* ABOUT AND FEATURES */}
      <section className="features-section" id="about">
        <div className="features-intro">
          <span className="section-label">NOT JUST ANOTHER MAP</span>
          <h2>
            The journey<br />
            is the <span>destination.</span>
          </h2>
          <p>
            We combine intelligent technology with the spirit of exploration
            to make every road trip extraordinary.
          </p>
        </div>

        <div className="feature-list">
          {[
            {
              icon: <Route size={21} />,
              title: "Scenic route intelligence",
              desc: "OSM-powered scenic scoring and ML-enhanced environment classification.",
            },
            {
              icon: <Coffee size={21} />,
              title: "Stops worth making",
              desc: "Find food, cafés, fuel stations and hidden viewpoints along the way.",
            },
            {
              icon: <Mountain size={21} />,
              title: "Personalized adventures",
              desc: "Trips designed around your preferences, vehicle and scenic profile.",
            },
            {
              icon: <Fuel size={21} />,
              title: "Smarter travel planning",
              desc: "Day-wise itinerary, weather intelligence and AI-generated trip summaries.",
            },
            {
              icon: <Brain size={21} />,
              title: "Machine learning",
              desc: "Local OSM feature extraction and machine-learning-based route analysis.",
            },
          ].map((feature) => (
            <div key={feature.title} className="feature-item">
              <div className="feature-icon">{feature.icon}</div>

              <div>
                <h3>{feature.title}</h3>
                <p>{feature.desc}</p>
              </div>

              <ChevronRight size={19} />
            </div>
          ))}
        </div>
      </section>

      {/* FOOTER */}
      <footer className="footer">
        <a href="#home" className="brand">
          <span className="brand-icon">
            <Compass size={22} />
          </span>

          <span>
            <strong>ROAM</strong>
            <small>BEYOND THE ROUTE</small>
          </span>
        </a>

        <p>Made for the love of the journey.</p>
        <span>© 2026 ROAM · EXPLORE MORE.</span>
      </footer>
    </main>
  );
}

export default App;
