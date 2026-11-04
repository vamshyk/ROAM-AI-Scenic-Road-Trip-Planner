
"""
ROAM - Day-wise Itinerary Generator

Builds practical daily itineraries using actual route geometry,
mapped settlements and local OSM points of interest.

Features:
- Route-distance-based daily boundaries.
- Mapped overnight settlements.
- Named POI prioritisation.
- Attraction quality heuristics.
- Category-aware duplicate and spacing filters.
- Stops distributed along each day's route.
- Food, fuel, viewpoints and tourist attractions.
- No invented hotels or accommodation availability.

Important:
POI quality is estimated from category and name only.
OSM records are not independently verified.
"""

import math
import re

try:
    from . import db
    DB_SUPPORT = True
except ImportError:
    DB_SUPPORT = False


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

DAILY_RANGE = {
    "car": {"comfortable": 300, "max": 500},
    "bike": {"comfortable": 200, "max": 350},
}

DAILY_DRIVE_HOURS = {
    "car": 7.0,
    "bike": 6.0,
}

STOP_CATEGORIES = {
    "car": [
        "food", "fuel", "viewpoint", "attraction",
        "museum", "picnic_site", "camp_site",
        "zoo", "theme_park",
    ],
    "bike": [
        "food", "fuel", "viewpoint", "attraction",
        "museum", "picnic_site", "camp_site",
        "zoo", "theme_park",
    ],
}

ROUTE_SAMPLE_INTERVAL_KM = 5.0
SETTLEMENT_SEARCH_RADIUS_KM = 15.0
POI_SAMPLE_INTERVAL_KM = 3.0
POI_SEARCH_RADIUS_DEG = 0.02

MIN_DAILY_FRACTION = 0.45
MAX_DAILY_FRACTION = 1.65

MAX_DAILY_STOPS = 5
MAX_POI_DISTANCE_KM = 3.5

# Minimum spacing depends on the types of stops being compared.
MIN_SPACING_SAME_CATEGORY_KM = 4.0
MIN_SPACING_SCENIC_OTHER_KM = 2.0
MIN_SPACING_FOOD_FUEL_KM = 2.5

SCENIC_CATEGORIES = {
    "viewpoint",
    "attraction",
    "museum",
    "picnic_site",
    "camp_site",
    "zoo",
    "theme_park",
}

# Categories with stronger sightseeing intent are considered first.
SCENIC_CATEGORY_PRIORITY = {
    "viewpoint": 1,
    "museum": 2,
    "zoo": 3,
    "theme_park": 3,
    "picnic_site": 4,
    "attraction": 5,
    "camp_site": 6,
}

# These words often indicate a minor mapped landmark rather than
# a substantial visitor attraction. They reduce priority, not eligibility.
LOW_VALUE_NAME_TERMS = {
    "idol",
    "arch",
    "statue",
    "pillar",
    "stone",
    "signboard",
    "name board",
    "gate",
    "entrance",
}

# These terms can indicate a more established visitor destination.
POSITIVE_NAME_TERMS = {
    "fort",
    "palace",
    "museum",
    "falls",
    "waterfall",
    "lake",
    "dam",
    "park",
    "sanctuary",
    "national park",
    "garden",
    "view point",
    "viewpoint",
    "peak",
    "temple",
    "heritage",
    "monument",
    "wildlife",
    "reserve",
}


# --------------------------------------------------
# GEOMETRY HELPERS
# --------------------------------------------------

def _haversine_km(lon1, lat1, lon2, lat2):
    """Calculate distance between two geographic coordinates."""

    radius = 6371.0

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    delta_lat = lat2_rad - lat1_rad
    delta_lon = math.radians(lon2 - lon1)

    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lon / 2) ** 2
    )

    value = max(0.0, min(1.0, value))

    return radius * 2 * math.atan2(
        math.sqrt(value),
        math.sqrt(1 - value)
    )


def _route_cumulative_distances(coordinates):
    """Calculate cumulative distance along route geometry."""

    if not coordinates:
        return []

    cumulative = [0.0]

    for index in range(1, len(coordinates)):
        previous = coordinates[index - 1]
        current = coordinates[index]

        distance = _haversine_km(
            previous[0], previous[1],
            current[0], current[1]
        )

        cumulative.append(cumulative[-1] + distance)

    return cumulative


def _coordinate_at_distance(coordinates, cumulative, target_km):
    """Interpolate a coordinate at a cumulative route distance."""

    if not coordinates:
        return None

    if target_km <= 0:
        return coordinates[0]

    if target_km >= cumulative[-1]:
        return coordinates[-1]

    low = 0
    high = len(cumulative) - 1

    while low < high:
        middle = (low + high) // 2

        if cumulative[middle] < target_km:
            low = middle + 1
        else:
            high = middle

    index = low

    previous_distance = cumulative[index - 1]
    current_distance = cumulative[index]

    segment_distance = current_distance - previous_distance

    if segment_distance <= 0:
        return coordinates[index]

    fraction = (
        (target_km - previous_distance) / segment_distance
    )

    previous = coordinates[index - 1]
    current = coordinates[index]

    return [
        previous[0] + (current[0] - previous[0]) * fraction,
        previous[1] + (current[1] - previous[1]) * fraction,
    ]


def _coordinates_between(
    coordinates, cumulative, start_km, end_km
):
    """Extract route geometry between two cumulative distances."""

    start = _coordinate_at_distance(
        coordinates, cumulative, start_km
    )
    end = _coordinate_at_distance(
        coordinates, cumulative, end_km
    )

    if start is None or end is None:
        return []

    segment = [start]

    for index, distance in enumerate(cumulative):
        if start_km < distance < end_km:
            segment.append(coordinates[index])

    if segment[-1] != end:
        segment.append(end)

    return segment


def _sample_route(coordinates, cumulative, interval_km):
    """Sample route coordinates at regular distance intervals."""

    if not coordinates or not cumulative:
        return []

    total = cumulative[-1]

    if total <= 0:
        return [coordinates[0]]

    samples = []
    target = 0.0

    while target < total:
        coordinate = _coordinate_at_distance(
            coordinates, cumulative, target
        )

        if coordinate is not None:
            samples.append(coordinate)

        target += interval_km

    samples.append(coordinates[-1])

    return samples


def _sample_route_with_distances(
    coordinates, cumulative, interval_km
):
    """Sample route coordinates together with their distances."""

    if not coordinates or not cumulative:
        return []

    total = cumulative[-1]

    if total <= 0:
        return []

    samples = []
    target = 0.0

    while target < total:
        coordinate = _coordinate_at_distance(
            coordinates, cumulative, target
        )

        if coordinate is not None:
            samples.append((
                coordinate[0],
                coordinate[1],
                target
            ))

        target += interval_km

    samples.append((
        coordinates[-1][0],
        coordinates[-1][1],
        total
    ))

    return samples


# --------------------------------------------------
# POI ROUTE POSITION
# --------------------------------------------------

def _project_poi_onto_route(poi, coordinates, cumulative):
    """
    Find the closest position of a POI along a route.

    Returns its cumulative route position and approximate
    lateral distance from the route.
    """

    if len(coordinates) < 2:
        return None

    try:
        poi_lon = float(poi["lon"])
        poi_lat = float(poi["lat"])
    except (KeyError, TypeError, ValueError):
        return None

    best_distance = float("inf")
    best_route_position = None

    reference_lat = poi_lat
    km_per_degree_lat = 111.32
    km_per_degree_lon = (
        111.32 * math.cos(math.radians(reference_lat))
    )

    for index in range(1, len(coordinates)):
        start = coordinates[index - 1]
        end = coordinates[index]

        ax = (start[0] - poi_lon) * km_per_degree_lon
        ay = (start[1] - poi_lat) * km_per_degree_lat

        bx = (end[0] - poi_lon) * km_per_degree_lon
        by = (end[1] - poi_lat) * km_per_degree_lat

        dx = bx - ax
        dy = by - ay

        denominator = dx * dx + dy * dy

        if denominator <= 0:
            fraction = 0.0
        else:
            fraction = -(
                ax * dx + ay * dy
            ) / denominator

            fraction = max(0.0, min(1.0, fraction))

        projected_x = ax + fraction * dx
        projected_y = ay + fraction * dy

        lateral_distance = math.sqrt(
            projected_x ** 2 + projected_y ** 2
        )

        if lateral_distance < best_distance:
            segment_distance = (
                cumulative[index] - cumulative[index - 1]
            )

            best_distance = lateral_distance

            best_route_position = (
                cumulative[index - 1]
                + fraction * segment_distance
            )

    if best_route_position is None:
        return None

    return {
        "route_distance_km": round(best_route_position, 2),
        "distance_from_route_km": round(best_distance, 2),
    }


# --------------------------------------------------
# LOCATION HELPERS
# --------------------------------------------------

def _normalise_name(name):
    """Normalise names for alias and duplicate detection."""

    value = re.sub(
        r"[^a-z0-9]",
        "",
        str(name).lower()
    )

    aliases = {
        "kodagu": "coorg",
        "kodagucoorg": "coorg",
        "madikeri": "coorg",
    }

    return aliases.get(value, value)


def _find_route_settlements(coordinates, cumulative):
    """Retrieve mapped settlements close to the route."""

    if not DB_SUPPORT or not db.is_db_available():
        return []

    samples = _sample_route_with_distances(
        coordinates,
        cumulative,
        ROUTE_SAMPLE_INTERVAL_KM
    )

    if not samples:
        return []

    try:
        settlements = db.query_settlements_along_route(
            samples,
            radius_km=SETTLEMENT_SEARCH_RADIUS_KM,
            max_candidates=500
        )

        return settlements or []

    except Exception as error:
        print(
            f"[ITINERARY] Settlement lookup warning: {error}"
        )
        return []


def _choose_overnight_settlement(
    settlements,
    target_distance,
    previous_distance,
    total_distance,
    remaining_days,
    excluded_names
):
    """Choose a suitable mapped settlement near the daily boundary."""

    target_gap = target_distance - previous_distance

    min_gap = max(
        20.0,
        target_gap * MIN_DAILY_FRACTION
    )

    max_gap = max(
        min_gap,
        target_gap * MAX_DAILY_FRACTION
    )

    latest_allowed = total_distance - (
        remaining_days * min_gap
    )

    earliest_allowed = previous_distance + min_gap

    candidates = []

    for settlement in settlements:
        name = settlement.get("name")

        if not name:
            continue

        normalised = _normalise_name(name)

        if normalised in excluded_names:
            continue

        route_distance = float(
            settlement.get("route_distance_km", -1)
        )

        distance_from_route = float(
            settlement.get("distance_from_route_km", 999)
        )

        if route_distance < earliest_allowed:
            continue

        if route_distance > latest_allowed:
            continue

        daily_gap = route_distance - previous_distance

        if daily_gap > max_gap:
            continue

        population = int(settlement.get("population") or 0)

        place_type = str(
            settlement.get("place_type") or "settlement"
        ).lower()

        score = (
            abs(route_distance - target_distance)
            + distance_from_route * 1.5
        )

        if place_type == "village":
            score += 3.0
        elif place_type not in ("town", "city"):
            score += 5.0

        if population > 0:
            score -= min(
                math.log10(population + 1),
                2.0
            )

        candidates.append((score, settlement))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])

    return candidates[0][1]


def _make_route_area(
    coordinates, cumulative, distance_km, day_number
):
    """Create a transparent approximate route-area suggestion."""

    waypoint = _coordinate_at_distance(
        coordinates, cumulative, distance_km
    )

    return {
        "name": f"Suggested overnight area after Day {day_number}",
        "place_type": "route_area",
        "lat": waypoint[1],
        "lon": waypoint[0],
        "suggestion_source": "route_waypoint",
        "is_approximate": True,
    }


# --------------------------------------------------
# POI QUALITY AND SELECTION
# --------------------------------------------------

def _poi_name_quality_penalty(name):
    """
    Estimate name usefulness.

    This is only a text heuristic. It does not verify the
    real-world importance or quality of a destination.
    """

    if not name:
        return 25.0

    normalised = str(name).lower()
    penalty = 0.0

    for term in LOW_VALUE_NAME_TERMS:
        if term in normalised:
            penalty += 12.0

    return penalty


def _poi_name_quality_bonus(name):
    """Give a modest preference to recognisable destination names."""

    if not name:
        return 0.0

    normalised = str(name).lower()

    for term in POSITIVE_NAME_TERMS:
        if term in normalised:
            return 4.0

    return 0.0


def _scenic_quality_score(item):
    """
    Lower scores indicate better sightseeing candidates.

    Category priority is stronger than name-based heuristics.
    """

    category = item.get("poi_type", "attraction")

    category_score = SCENIC_CATEGORY_PRIORITY.get(
        category, 8
    ) * 3.0

    name = item.get("name")

    return (
        category_score
        + _poi_name_quality_penalty(name)
        - _poi_name_quality_bonus(name)
        + item.get("distance_from_route_km", 0) * 2.0
    )


def _get_poi_candidates(day_coords, vehicle):
    """Retrieve and enrich POIs with their positions along the route."""

    if not DB_SUPPORT or not day_coords:
        return []

    if not db.is_db_available():
        return []

    categories = STOP_CATEGORIES.get(
        vehicle, STOP_CATEGORIES["car"]
    )

    cumulative = _route_cumulative_distances(day_coords)

    if not cumulative or cumulative[-1] <= 0:
        return []

    samples = _sample_route(
        day_coords,
        cumulative,
        POI_SAMPLE_INTERVAL_KM
    )

    try:
        raw_stops = db.query_pois_along_route(
            samples,
            categories,
            radius_deg=POI_SEARCH_RADIUS_DEG
        )

    except Exception as error:
        print(f"[ITINERARY] POI lookup warning: {error}")
        return []

    candidates = []
    exact_seen = set()

    for stop in raw_stops or []:
        try:
            poi_type = str(
                stop.get("poi_type") or ""
            ).lower()

            lat = float(stop["lat"])
            lon = float(stop["lon"])

            if poi_type not in categories:
                continue

            if not (
                -90 <= lat <= 90
                and -180 <= lon <= 180
            ):
                continue

            name = str(stop.get("name") or "").strip()

            exact_key = (
                poi_type,
                _normalise_name(name) if name else "",
                round(lat, 5),
                round(lon, 5),
            )

            if exact_key in exact_seen:
                continue

            exact_seen.add(exact_key)

            position = _project_poi_onto_route(
                {"lat": lat, "lon": lon},
                day_coords,
                cumulative
            )

            if not position:
                continue

            if (
                position["distance_from_route_km"]
                > MAX_POI_DISTANCE_KM
            ):
                continue

            enriched = dict(stop)
            enriched["poi_type"] = poi_type
            enriched["name"] = name or None
            enriched["lat"] = lat
            enriched["lon"] = lon
            enriched.update(position)

            candidates.append(enriched)

        except (TypeError, ValueError, KeyError):
            continue

    return candidates


def _minimum_spacing(candidate, existing):
    """Return the minimum allowed spacing for two POI categories."""

    candidate_type = candidate.get("poi_type")
    existing_type = existing.get("poi_type")

    if candidate_type == existing_type:
        return MIN_SPACING_SAME_CATEGORY_KM

    if (
        candidate_type in SCENIC_CATEGORIES
        or existing_type in SCENIC_CATEGORIES
    ):
        return MIN_SPACING_SCENIC_OTHER_KM

    return MIN_SPACING_FOOD_FUEL_KM


def _is_near_selected_stop(candidate, selected):
    """Check category-aware geographic spacing between stops."""

    for existing in selected:
        distance = _haversine_km(
            candidate["lon"],
            candidate["lat"],
            existing["lon"],
            existing["lat"]
        )

        minimum = _minimum_spacing(candidate, existing)

        if distance < minimum:
            return True

    return False


def _candidate_position_score(item, target):
    """Score a POI for route position, naming and route proximity."""

    return (
        abs(item["route_distance_km"] - target)
        + _poi_name_quality_penalty(item.get("name"))
        - _poi_name_quality_bonus(item.get("name"))
        + item["distance_from_route_km"] * 2.0
    )


def _choose_category_stops(
    candidates,
    selected,
    category,
    quota,
    target_fractions,
    route_length
):
    """Choose category-specific stops near desired route positions."""

    category_candidates = [
        item for item in candidates
        if item["poi_type"] == category
    ]

    chosen = []

    for fraction in target_fractions:
        if len(chosen) >= quota:
            break

        target = route_length * fraction

        available = [
            item for item in category_candidates
            if item not in chosen
            and not _is_near_selected_stop(item, selected)
            and not _is_near_selected_stop(item, chosen)
        ]

        if not available:
            continue

        best = min(
            available,
            key=lambda item: _candidate_position_score(
                item, target
            )
        )

        chosen.append(best)

    return chosen


def _choose_scenic_stops(candidates, selected, route_length):
    """
    Select up to two sightseeing candidates.

    Viewpoints and museums receive priority over generic attractions.
    Generic landmark names are penalised, not automatically rejected.
    """

    scenic_candidates = [
        item for item in candidates
        if item["poi_type"] in SCENIC_CATEGORIES
    ]

    scenic_selected = []

    for fraction in [0.35, 0.75]:
        if len(scenic_selected) >= 2:
            break

        target = route_length * fraction

        available = [
            item for item in scenic_candidates
            if item not in scenic_selected
            and not _is_near_selected_stop(item, selected)
            and not _is_near_selected_stop(
                item, scenic_selected
            )
        ]

        if not available:
            continue

        def score(item):
            return (
                _candidate_position_score(item, target)
                + _scenic_quality_score(item)
            )

        best = min(available, key=score)
        scenic_selected.append(best)

    return scenic_selected


def _find_stops_for_day(day_coords, vehicle, seen_pois):
    """
    Find a useful selection of stops distributed along the daily route.

    Sightseeing is selected first so that food and fuel candidates
    do not unnecessarily crowd out available attractions.
    """

    candidates = _get_poi_candidates(
        day_coords, vehicle
    )

    if not candidates:
        return []

    cumulative = _route_cumulative_distances(day_coords)
    route_length = cumulative[-1]

    if route_length <= 0:
        return []

    selected = []

    # Select sightseeing first.
    selected.extend(
        _choose_scenic_stops(
            candidates,
            selected,
            route_length
        )
    )

    # Add up to two food stops.
    selected.extend(
        _choose_category_stops(
            candidates,
            selected,
            "food",
            quota=2,
            target_fractions=[0.30, 0.72],
            route_length=route_length
        )
    )

    # Add one fuel stop, preferably around the middle.
    selected.extend(
        _choose_category_stops(
            candidates,
            selected,
            "fuel",
            quota=1,
            target_fractions=[0.55],
            route_length=route_length
        )
    )

    # Keep the daily cap and present stops in route order.
    selected = selected[:MAX_DAILY_STOPS]

    selected.sort(
        key=lambda item: item["route_distance_km"]
    )

    result = []

    for stop in selected:
        identity = (
            stop["poi_type"],
            _normalise_name(stop.get("name") or ""),
            round(stop["lat"], 4),
            round(stop["lon"], 4),
        )

        if identity in seen_pois:
            continue

        seen_pois.add(identity)

        result.append({
            "poi_type": stop["poi_type"],
            "name": stop.get("name"),
            "lat": stop["lat"],
            "lon": stop["lon"],
            "route_distance_km": stop["route_distance_km"],
            "distance_from_route_km": (
                stop["distance_from_route_km"]
            ),
        })

    return result


# --------------------------------------------------
# FORMATTING
# --------------------------------------------------

def _format_time(minutes):
    """Convert minutes into a readable duration."""

    minutes = max(0, int(round(minutes)))

    hours, remaining_minutes = divmod(minutes, 60)

    if hours == 0:
        return f"{remaining_minutes} min"

    return f"{hours} hr {remaining_minutes} min"


def _build_day_highlights(
    day_num, total_days, overnight, stops
):
    """Build a short summary of daily highlights."""

    parts = []

    if day_num == 1:
        parts.append("Departure day")

    if day_num == total_days:
        parts.append("Arrival day")

    food_count = sum(
        1 for stop in stops
        if stop.get("poi_type") == "food"
    )

    fuel_count = sum(
        1 for stop in stops
        if stop.get("poi_type") == "fuel"
    )

    sightseeing_count = sum(
        1 for stop in stops
        if stop.get("poi_type") in SCENIC_CATEGORIES
    )

    if sightseeing_count:
        parts.append(
            f"{sightseeing_count} sightseeing stop(s)"
        )

    if food_count:
        parts.append(f"{food_count} food stop(s)")

    if fuel_count:
        parts.append(f"{fuel_count} fuel stop(s)")

    parts.append(f"Overnight in {overnight['name']}")

    return " · ".join(parts)


# --------------------------------------------------
# COMFORT WARNINGS
# --------------------------------------------------

def _comfort_warning(distance_km, duration_minutes, vehicle):
    """Warn when daily driving exceeds recommended limits."""

    comfortable = DAILY_RANGE[vehicle]["comfortable"]
    maximum = DAILY_RANGE[vehicle]["max"]
    maximum_minutes = DAILY_DRIVE_HOURS[vehicle] * 60

    if distance_km > maximum:
        return (
            f"Daily distance exceeds the {maximum} km "
            f"recommended maximum for a {vehicle}."
        )

    if duration_minutes > maximum_minutes:
        return (
            f"Daily driving time exceeds "
            f"{DAILY_DRIVE_HOURS[vehicle]} hours for a {vehicle}."
        )

    if distance_km > comfortable:
        return (
            f"Daily distance is above the comfortable "
            f"{comfortable} km range for a {vehicle}."
        )

    return None


# --------------------------------------------------
# MAIN ITINERARY BUILDER
# --------------------------------------------------

def generate_itinerary(
    origin_name: str,
    destination_name: str,
    origin: dict,
    destination: dict,
    route: dict,
    days: int,
    vehicle: str,
) -> dict:
    """
    Generate a route-aware day-wise itinerary.

    Daily boundaries use mapped settlements when available.
    Daily stops are selected and distributed along actual
    route geometry.
    """

    days = max(1, min(int(days), 30))

    vehicle = (
        vehicle if vehicle in DAILY_RANGE else "car"
    )

    coordinates = (
        route.get("geometry", {}).get("coordinates", [])
    )

    total_distance_km = float(
        route.get("distance_km", 0) or 0
    )

    total_duration_min = float(
        route.get("duration_minutes", 0) or 0
    )

    if total_distance_km <= 0:
        raise ValueError("Route distance is unavailable.")

    if total_duration_min <= 0:
        raise ValueError("Route driving duration is unavailable.")

    if len(coordinates) < 2:
        raise ValueError("Route geometry is unavailable.")

    cumulative = _route_cumulative_distances(coordinates)
    geometry_distance = cumulative[-1]

    if geometry_distance <= 0:
        raise ValueError("Route geometry has zero distance.")

    distance_scale = total_distance_km / geometry_distance

    comfort_km = DAILY_RANGE[vehicle]["comfortable"]

    average_distance = total_distance_km / days
    average_duration = total_duration_min / days

    comfort_note = None

    if average_distance > DAILY_RANGE[vehicle]["max"]:
        comfort_note = (
            f"The average daily distance is "
            f"{average_distance:.1f} km, exceeding the "
            f"{DAILY_RANGE[vehicle]['max']} km recommended "
            f"maximum for a {vehicle}. Consider adding days."
        )

    elif average_distance > comfort_km:
        comfort_note = (
            f"The average daily distance is "
            f"{average_distance:.1f} km, above the comfortable "
            f"{comfort_km} km range for a {vehicle}."
        )

    elif average_duration > DAILY_DRIVE_HOURS[vehicle] * 60:
        comfort_note = (
            f"The average daily driving time exceeds "
            f"{DAILY_DRIVE_HOURS[vehicle]} hours. "
            f"Plan sufficient breaks."
        )

    settlements = _find_route_settlements(
        coordinates, cumulative
    )

    print(
        f"[ITINERARY] Mapped settlements near route: "
        f"{len(settlements)}"
    )

    days_list = []

    excluded_names = {
        _normalise_name(origin_name),
        _normalise_name(destination_name),
    }

    seen_pois = set()
    previous_boundary = 0.0

    for day_num in range(1, days + 1):

        if day_num == days:
            end_boundary = geometry_distance

            overnight = {
                "name": destination_name,
                "place_type": "destination",
                "lat": destination["latitude"],
                "lon": destination["longitude"],
                "suggestion_source": "user_destination",
                "is_approximate": False,
            }

        else:
            target_boundary = (
                geometry_distance * day_num / days
            )

            remaining_days = days - day_num

            settlement = _choose_overnight_settlement(
                settlements=settlements,
                target_distance=target_boundary,
                previous_distance=previous_boundary,
                total_distance=geometry_distance,
                remaining_days=remaining_days,
                excluded_names=excluded_names,
            )

            if settlement:
                end_boundary = float(
                    settlement["route_distance_km"]
                )

                overnight = {
                    "name": settlement["name"],
                    "place_type": settlement.get(
                        "place_type", "settlement"
                    ),
                    "lat": settlement["lat"],
                    "lon": settlement["lon"],
                    "suggestion_source": "local_osm_database",
                    "is_approximate": False,
                    "distance_from_route_km": round(
                        float(
                            settlement.get(
                                "distance_from_route_km", 0
                            )
                        ),
                        2
                    ),
                }

                excluded_names.add(
                    _normalise_name(settlement["name"])
                )

            else:
                end_boundary = target_boundary

                overnight = _make_route_area(
                    coordinates,
                    cumulative,
                    end_boundary,
                    day_num
                )

        day_coords = _coordinates_between(
            coordinates,
            cumulative,
            previous_boundary,
            end_boundary
        )

        geometry_day_distance = (
            end_boundary - previous_boundary
        )

        daily_distance = (
            geometry_day_distance * distance_scale
        )

        daily_duration = (
            total_duration_min
            * geometry_day_distance
            / geometry_distance
        )

        if day_num == 1:
            day_start_name = origin_name
        else:
            day_start_name = days_list[-1][
                "overnight_stay"
            ]["name"]

        stops = _find_stops_for_day(
            day_coords,
            vehicle,
            seen_pois
        )

        highlights = _build_day_highlights(
            day_num,
            days,
            overnight,
            stops
        )

        warning = _comfort_warning(
            daily_distance,
            daily_duration,
            vehicle
        )

        days_list.append({
            "day": day_num,
            "from": day_start_name,
            "to": overnight["name"],
            "distance_km": round(daily_distance, 1),
            "drive_minutes": round(daily_duration),
            "drive_time": _format_time(daily_duration),
            "overnight_stay": overnight,
            "suggested_stops": stops,
            "highlights": highlights,
            "comfort_warning": warning is not None,
            "comfort_warning_message": warning,
        })

        previous_boundary = end_boundary

    return {
        "total_days": days,
        "total_distance_km": round(total_distance_km, 1),
        "total_drive_time": _format_time(total_duration_min),
        "km_per_day": round(total_distance_km / days, 1),
        "vehicle": vehicle,
        "comfort_note": comfort_note,
        "geometry_distance_km": round(geometry_distance, 2),
        "days": days_list,
        "notes": [
            "Daily segments follow actual route geometry.",
            "Overnight settlements are selected from mapped local OSM records when available.",
            "Route-area suggestions are approximate and are not verified accommodation locations.",
            "Suggested POIs are selected from mapped local OSM records and distributed along daily route segments.",
            "Named POIs are prioritised where suitable records are available.",
            "Sightseeing priority uses POI category and name heuristics, not verified attraction ratings.",
            "Nearby duplicate stops are filtered using category-aware spacing.",
            "Driving times are estimates allocated from route distance and total routing time.",
            "Driving times exclude meal breaks, sightseeing and overnight stays.",
        ],
    }
