from tests.integration.client.transport import unmatched_requests


def test_requests_to_existing_routes_are_matched(app):
    assert unmatched_requests(app, [("GET", "/api/v2/specimens"), ("GET", "/api/v2/specimens/SP1")]) == []


def test_request_to_missing_path_is_reported(app):
    missing = ("GET", "/api/v2/acquisitions/A1/complete-metadata")
    assert unmatched_requests(app, [missing]) == [missing]


def test_request_with_wrong_method_is_reported(app):
    assert unmatched_requests(app, [("PUT", "/api/v2/specimens")]) == [("PUT", "/api/v2/specimens")]
