"""Small, dependency-free geospatial helpers."""

from math import asin, atan2, cos, degrees, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0088
NAUTICAL_MILE_KM = 1.852


def destination_point(
    *,
    latitude: float,
    longitude: float,
    heading_degrees: float,
    speed_knots: float,
    duration_minutes: float,
) -> tuple[float, float]:
    """Project a position on a spherical Earth with a constant ground vector."""

    distance_km = speed_knots * NAUTICAL_MILE_KM * duration_minutes / 60.0
    angular_distance = distance_km / EARTH_RADIUS_KM
    bearing = radians(heading_degrees)
    lat1 = radians(latitude)
    lon1 = radians(longitude)

    lat2 = asin(
        sin(lat1) * cos(angular_distance) + cos(lat1) * sin(angular_distance) * cos(bearing)
    )
    lon2 = lon1 + atan2(
        sin(bearing) * sin(angular_distance) * cos(lat1),
        cos(angular_distance) - sin(lat1) * sin(lat2),
    )
    normalized_lon = (degrees(lon2) + 540.0) % 360.0 - 180.0
    return degrees(lat2), normalized_lon


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance between two WGS84 coordinates."""

    lat1_rad, lat2_rad = radians(lat1), radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    value = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * atan2(sqrt(value), sqrt(1 - value))


def smallest_heading_delta(previous: float, current: float) -> float:
    """Return the signed shortest turn between headings in degrees."""

    return (current - previous + 180.0) % 360.0 - 180.0
