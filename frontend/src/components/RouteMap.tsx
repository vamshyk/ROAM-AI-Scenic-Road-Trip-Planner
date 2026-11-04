
import { useEffect, useRef } from "react";
import {
    Map as MapLibreMap,
    NavigationControl,
    Marker,
    Popup,
    LngLatBounds,
} from "maplibre-gl";

import "maplibre-gl/dist/maplibre-gl.css";

interface RouteMapProps {
    geometry: {
        type: string;
        coordinates: [number, number][];
    };
    origin: {
        latitude: number;
        longitude: number;
        display_name: string;
    };
    destination: {
        latitude: number;
        longitude: number;
        display_name: string;
    };
}

function RouteMap({
    geometry,
    origin,
    destination,
}: RouteMapProps) {
    const mapContainer = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        if (
            !mapContainer.current ||
            !geometry.coordinates ||
            geometry.coordinates.length === 0
        ) {
            return;
        }

        const map = new MapLibreMap({
            container: mapContainer.current,
            style: "https://tiles.openfreemap.org/styles/dark",
            center: [origin.longitude, origin.latitude],
            zoom: 7,
            attributionControl: {
                compact: true,
            },
        });

        map.addControl(
            new NavigationControl(),
            "top-right"
        );

        map.on("load", () => {
            map.addSource("road-route", {
                type: "geojson",
                data: {
                    type: "Feature",
                    properties: {},
                    geometry: {
                        type: "LineString",
                        coordinates: geometry.coordinates,
                    },
                },
            });

            map.addLayer({
                id: "road-route-line",
                type: "line",
                source: "road-route",
                layout: {
                    "line-join": "round",
                    "line-cap": "round",
                },
                paint: {
                    "line-color": "#e6a94e",
                    "line-width": 5,
                    "line-opacity": 0.95,
                },
            });

            new Marker({ color: "#48b985" })
                .setLngLat([
                    origin.longitude,
                    origin.latitude,
                ])
                .setPopup(
                    new Popup().setText("Starting point")
                )
                .addTo(map);

            new Marker({ color: "#e6a94e" })
                .setLngLat([
                    destination.longitude,
                    destination.latitude,
                ])
                .setPopup(
                    new Popup().setText("Destination")
                )
                .addTo(map);

            const bounds = new LngLatBounds();

            geometry.coordinates.forEach((coordinate) => {
                bounds.extend(coordinate);
            });

            map.fitBounds(bounds, {
                padding: 65,
                maxZoom: 12,
                duration: 1000,
            });
        });

        map.on("error", (event) => {
            console.error(
                "MapLibre map error:",
                event.error
            );
        });

        return () => map.remove();

    }, [geometry, origin, destination]);

    return (
        <div
            style={{
                width: "100%",
                height: "420px",
                marginTop: "24px",
                borderRadius: "16px",
                overflow: "hidden",
                border: "1px solid rgba(255,255,255,0.12)",
                background: "#101b1a",
            }}
        >
            <div
                ref={mapContainer}
                style={{
                    width: "100%",
                    height: "100%",
                }}
            />
        </div>
    );
}

export default RouteMap;
