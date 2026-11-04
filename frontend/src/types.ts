
// ROAM - Shared TypeScript interfaces

export interface RouteOption {
  route_id: number;
  name: string;
  route_type: string;
  is_fastest: boolean;
  is_recommended: boolean;
  distance_km: number;
  duration_minutes: number;
  duration_hours: number;
  has_toll: boolean | null;
  has_highway: boolean | null;
  has_ferry: boolean | null;
  scenic_score: number | null;
  scenic_score_status: string;
  scenic_features: ScenicFeatures | null;
  ml_scenic_score: number | null;
  ml_environment: string | null;
  recommendation_score: number | null;
  recommendation_reason: string;
  geometry: {
    type: string;
    coordinates: [number, number][];
  };
  maneuvers: Maneuver[];
}

export interface ScenicFeatures {
  scenic_score: number | null;
  scoring_method: string;
  route_length_km: number;
  nearby_forest_count: number;
  nearby_water_count: number;
  nearby_tourist_places: number;
  environment?: string | null;
  road_distribution: Record<string, number>;
  feature_scores: {
    forest_score: number;
    water_score: number;
    attraction_score: number;
    track_score: number;
  };
}

export interface Maneuver {
  instruction: string;
  distance_km: number;
  duration_seconds: number;
}

export interface GeoPoint {
  latitude: number;
  longitude: number;
  display_name: string;
}

export interface TripResult {
  status: string;
  message: string;
  origin: GeoPoint;
  destination: GeoPoint;
  vehicle: string;
  days: number;
  preference: string;
  distance_km: number;
  duration_minutes: number;
  duration_hours: number;
  geometry: {
    type: string;
    coordinates: [number, number][];
  };
  routes: RouteOption[];
  route_count: number;
  recommended_route_id: number;
  recommendation: string;
  routing_engine: string;
  itinerary: Itinerary | null;
  travel_intel: TravelIntel | null;
  ai_summary: AISummary | null;
  warnings: string[];
  source: string;
  attribution: string;
  cache_hit: boolean;
}

export interface ItineraryDay {
  day: number;
  from: string;
  to: string;
  distance_km: number;
  drive_minutes: number;
  drive_time: string;
  overnight_stay: {
    name: string;
    place_type: string;
    lat: number;
    lon: number;
  };
  suggested_stops: POI[];
  highlights: string;
}

export interface Itinerary {
  total_days: number;
  total_distance_km: number;
  total_drive_time: string;
  km_per_day: number;
  vehicle: string;
  comfort_note: string | null;
  days: ItineraryDay[];
}

export interface WeatherDay {
  date: string;
  description: string;
  icon: string;
  temp_max_c: number | null;
  temp_min_c: number | null;
  precipitation_mm: number;
  rain_risk: string;
}

export interface Weather {
  current: {
    temperature_c: number | null;
    description: string;
    icon: string;
    wind_kmh: number | null;
    humidity_pct: number | null;
  };
  daily_forecast: WeatherDay[];
  fog_risk: string;
  best_travel_days: string[];
}

export interface POI {
  name: string;
  lat?: number;
  lon?: number;
  type: string;
  poi_type?: string;
}

export interface TravelIntel {
  origin_weather: Weather | null;
  destination_weather: Weather | null;
  trip_rain_risk: string;
  stops: {
    fuel_stations: POI[];
    food_stops: POI[];
    viewpoints: POI[];
    hotels: POI[];
    medical: POI[];
  };
  fuel_station_count: number;
  food_stop_count: number;
  viewpoint_count: number;
}

export interface AISummary {
  summary: string;
  source: "gemini" | "fallback";
  note?: string;
}
