from backend.app.services.geo import destination_point, haversine_km, smallest_heading_delta


def test_destination_point_uses_nautical_speed_units() -> None:
    latitude, longitude = destination_point(
        latitude=48.0,
        longitude=2.0,
        heading_degrees=90.0,
        speed_knots=60.0,
        duration_minutes=60.0,
    )

    assert 47.9 < latitude < 48.1
    assert 3.45 < longitude < 3.55
    assert 110 < haversine_km(48.0, 2.0, latitude, longitude) < 112


def test_heading_delta_wraps_at_north() -> None:
    assert smallest_heading_delta(355.0, 5.0) == 10.0
    assert smallest_heading_delta(5.0, 355.0) == -10.0
