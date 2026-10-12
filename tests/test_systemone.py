import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError


spec = importlib.util.spec_from_file_location(
    "systemone", Path(__file__).parents[1] / "skills/clef-jev/scripts/systemone.py"
)
systemone = importlib.util.module_from_spec(spec)
spec.loader.exec_module(systemone)

PAYLOAD = {
    "state": "Invoice paid",
    "questions": {"paid": {"type": "noul", "instructions": "Is it paid?"}},
}
ANSWER = {
    "model": "clef-flash",
    "answers": {"paid": {"type": "noul", "noul": 0.9}},
    "usage": {"input_tokens": 20, "output_tokens": 0},
}


class Response(io.BytesIO):
    def __init__(self, body):
        super().__init__(json.dumps(body).encode())


def http_error(status):
    return HTTPError("https://example.test", status, "test failure", {}, io.BytesIO())


class FailoverTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(systemone.os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_primary_success_returns_provenance_and_keeps_request_unchanged(self):
        with patch.object(systemone, "urlopen", return_value=Response(ANSWER)) as send:
            result = systemone.evaluate(PAYLOAD)
        self.assertEqual(result["provider"]["name"], "clef-primary")
        self.assertEqual(result["response"], ANSWER)
        self.assertEqual(send.call_count, 1)
        self.assertNotIn("model", PAYLOAD)

    def test_connection_failure_uses_secondary_without_jev_key(self):
        with patch.dict(systemone.os.environ, {"TYPESAFE_API_KEY": "official-only"}):
            with patch.object(systemone, "urlopen", side_effect=[URLError("offline"), Response(ANSWER)]) as send:
                result = systemone.evaluate(PAYLOAD)
        self.assertEqual(result["provider"]["name"], "clef-secondary")
        for call in send.call_args_list:
            self.assertIsNone(call.args[0].get_header("Authorization"))

    def test_two_service_failures_use_jev_with_correct_model_and_key(self):
        with patch.dict(systemone.os.environ, {"TYPESAFE_API_KEY": "official-only"}):
            with patch.object(systemone, "urlopen", side_effect=[http_error(503), http_error(429), Response(ANSWER)]) as send:
                result = systemone.evaluate(PAYLOAD)
        request = send.call_args_list[2].args[0]
        self.assertEqual(request.full_url, "https://api.typesafe.ai/v1/systemone")
        self.assertEqual(request.get_header("Authorization"), "Bearer official-only")
        self.assertEqual(json.loads(request.data)["model"], "jev-latest")
        self.assertEqual(result["provider"]["name"], "jev")

    def test_input_error_stops_without_fallback(self):
        for status in (400, 422):
            with self.subTest(status=status):
                with patch.object(systemone, "urlopen", side_effect=http_error(status)) as send:
                    with self.assertRaises(systemone.DecisionError):
                        systemone.evaluate(PAYLOAD)
                self.assertEqual(send.call_count, 1)

    def test_known_batch_overflow_reported_as_500_stops_without_fallback(self):
        body = json.dumps({"error": {"message": "input (5143 tokens) is too large to process. increase the physical batch size (current batch size: 4096)"}}).encode()
        error = HTTPError("https://example.test", 500, "overflow", {}, io.BytesIO(body))
        with patch.object(systemone, "urlopen", side_effect=error) as send:
            with self.assertRaisesRegex(systemone.DecisionError, "physical batch limit"):
                systemone.evaluate(PAYLOAD)
        self.assertEqual(send.call_count, 1)

    def test_self_hosted_access_error_moves_to_next_service(self):
        with patch.object(systemone, "urlopen", side_effect=[http_error(403), Response(ANSWER)]):
            result = systemone.evaluate(PAYLOAD)
        self.assertEqual(result["provider"]["name"], "clef-secondary")

    def test_invalid_success_body_moves_to_next_service(self):
        for invalid in ({}, {**ANSWER, "answers": {"paid": {"type": "noul", "noul": 2}}}):
            with self.subTest(invalid=invalid):
                with patch.object(systemone, "urlopen", side_effect=[Response(invalid), Response(ANSWER)]):
                    result = systemone.evaluate(PAYLOAD)
                self.assertEqual(result["provider"]["name"], "clef-secondary")

    def test_missing_jev_key_reports_exhaustion_without_third_request(self):
        with patch.object(systemone, "urlopen", side_effect=TimeoutError("timeout")) as send:
            with self.assertRaisesRegex(systemone.DecisionError, "TYPESAFE_API_KEY"):
                systemone.evaluate(PAYLOAD)
        self.assertEqual(send.call_count, 2)

    def test_custom_base_url_uses_api_root(self):
        with patch.dict(systemone.os.environ, {"CLEF_PRIMARY_BASE_URL": "https://custom.test/"}):
            with patch.object(systemone, "urlopen", return_value=Response(ANSWER)) as send:
                systemone.evaluate(PAYLOAD)
        self.assertEqual(send.call_args.args[0].full_url, "https://custom.test/v1/systemone")

    def test_numeric_instructions_rejected_before_network(self):
        payload = {"state": "text", "questions": {"q": {"type": "noul", "instructions": 42}}}
        with patch.object(systemone, "urlopen") as send:
            with self.assertRaises(systemone.DecisionError):
                systemone.evaluate(payload)
        send.assert_not_called()

    def test_structured_input_and_null_choice_description_are_preserved_on_fallback(self):
        payload = {
            "state": {"invoice": "paid"},
            "questions": {
                "status": {"type": "choice", "instructions": {"question": "Status?"},
                           "criteria": {"paid": {"description": "Paid"}, "unpaid": None}},
                "level": {"type": "score", "instructions": ["Level?"],
                          "criteria": ["Low", {"description": "High"}]},
            },
        }
        response = {
            **ANSWER,
            "answers": {
                "status": {"type": "choice", "choice": "paid", "probabilities": {"paid": 0.9, "unpaid": 0.1}, "confidence": 0.8},
                "level": {"type": "score", "score": 0.9, "probabilities": {"0": 0.1, "1": 0.9}, "confidence": 0.8,
                          "legend": {"0": "Low", "1": {"description": "High"}}},
            },
        }
        with patch.object(systemone, "urlopen", side_effect=[TimeoutError(), Response(response)]) as send:
            result = systemone.evaluate(payload)
        self.assertEqual(result["provider"]["name"], "clef-secondary")
        self.assertEqual(result["response"]["answers"], response["answers"])
        for call in send.call_args_list:
            self.assertEqual(json.loads(call.args[0].data)["questions"], payload["questions"])

    def test_low_confidence_success_does_not_escalate(self):
        answer = {**ANSWER, "answers": {"paid": {"type": "noul", "noul": 0.5}}}
        with patch.object(systemone, "urlopen", return_value=Response(answer)) as send:
            result = systemone.evaluate(PAYLOAD)
        self.assertEqual(result["response"]["answers"]["paid"]["noul"], 0.5)
        self.assertEqual(send.call_count, 1)

    def test_timeout_uses_secondary(self):
        with patch.object(systemone, "urlopen", side_effect=[TimeoutError(), Response(ANSWER)]):
            result = systemone.evaluate(PAYLOAD)
        self.assertEqual(result["provider"]["name"], "clef-secondary")

    def test_jev_auth_error_is_reported(self):
        with patch.dict(systemone.os.environ, {"TYPESAFE_API_KEY": "official-only"}):
            with patch.object(systemone, "urlopen", side_effect=[http_error(502), http_error(504), http_error(401)]):
                with self.assertRaisesRegex(systemone.DecisionError, "jev: HTTP 401"):
                    systemone.evaluate(PAYLOAD)

    def test_all_services_unavailable_reports_each_provider(self):
        with patch.dict(systemone.os.environ, {"TYPESAFE_API_KEY": "official-only"}):
            with patch.object(systemone, "urlopen", side_effect=[http_error(503), http_error(503), http_error(529)]) as send:
                with self.assertRaises(systemone.DecisionError) as raised:
                    systemone.evaluate(PAYLOAD)
        self.assertEqual(send.call_count, 3)
        for provider in ("clef-primary", "clef-secondary", "jev"):
            self.assertIn(provider, str(raised.exception))

    def test_non_https_or_endpoint_base_url_is_rejected(self):
        for url in ("http://custom.test", "https://custom.test/v1", "https://key@custom.test"):
            with self.subTest(url=url), patch.dict(systemone.os.environ, {"CLEF_PRIMARY_BASE_URL": url}):
                with patch.object(systemone, "urlopen") as send:
                    with self.assertRaises(systemone.DecisionError):
                        systemone.evaluate(PAYLOAD)
                send.assert_not_called()

    def test_choice_and_score_validate_their_distributions(self):
        questions = {
            "category": {"type": "choice", "instructions": "Category?", "criteria": {"a": "A", "b": "B"}},
            "level": {"type": "score", "instructions": "Level?", "criteria": ["Low", "High"]},
        }
        response = {
            **ANSWER,
            "answers": {
                "category": {"type": "choice", "choice": "a", "probabilities": {"a": 0.8, "b": 0.2}, "confidence": 0.6},
                "level": {"type": "score", "score": 0.8, "probabilities": {"0": 0.2, "1": 0.8}, "confidence": 0.6, "legend": {"0": "Low", "1": "High"}},
            },
        }
        systemone.validate_response(response, questions)
        response["answers"]["category"]["probabilities"]["b"] = 0.8
        with self.assertRaises(ValueError):
            systemone.validate_response(response, questions)

    def test_redirect_does_not_forward_credentials(self):
        request = systemone.Request("https://api.typesafe.ai/v1/systemone", data=b"{}")
        with self.assertRaises(HTTPError) as raised:
            systemone.NoRedirect().redirect_request(request, None, 307, "redirect", {}, "https://other.test")
        raised.exception.close()


if __name__ == "__main__":
    unittest.main()
