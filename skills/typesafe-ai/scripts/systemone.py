#!/usr/bin/env python3
"""System One client: primary Clef -> secondary Clef -> official Jev."""

import argparse
import json
import math
import os
import sys
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class DecisionError(Exception):
    """Invalid input or exhausted providers."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, "Redirect refused", headers, fp)


# Keep provider credentials on the configured host, including for GET redirects.
urlopen = build_opener(NoRedirect()).open


def validate_request(payload):
    if not isinstance(payload, dict) or "state" not in payload:
        raise DecisionError("Request must be an object containing state and questions.")
    if set(payload) - {"state", "questions", "model"}:
        raise DecisionError("Portable requests support only state, questions, and model; images are provider-specific.")
    if not isinstance(payload["state"], (str, dict, list)):
        raise DecisionError("Portable state must be a string, object, or array.")
    questions = payload.get("questions")
    if not isinstance(questions, dict) or not questions:
        raise DecisionError("questions must be a non-empty object.")
    for qid, question in questions.items():
        if not isinstance(qid, str) or not isinstance(question, dict):
            raise DecisionError("Each question must have a string ID and an object definition.")
        kind = question.get("type")
        if kind not in ("noul", "choice", "score"):
            raise DecisionError("Question type must be noul, choice, or score.")
        if set(question) - {"type", "instructions", "criteria"}:
            raise DecisionError("Portable questions support only type, instructions, and criteria.")
        instructions = question.get("instructions")
        if not flexible(instructions) or not instructions or (isinstance(instructions, str) and not instructions.strip()):
            raise DecisionError("Each question needs explicit non-empty string, object, or array instructions.")
        criteria = question.get("criteria")
        if kind == "choice":
            if not isinstance(criteria, dict) or not 1 <= len(criteria) <= 255:
                raise DecisionError("Choice criteria must contain 1 to 255 options.")
            if not all(isinstance(k, str) and (v is None or flexible(v)) for k, v in criteria.items()):
                raise DecisionError("Choice criteria require string IDs and string/object/array/null descriptions.")
        elif kind == "score":
            if not isinstance(criteria, list) or not 2 <= len(criteria) <= 10:
                raise DecisionError("Score criteria must contain 2 to 10 ordered levels.")
            if not all(flexible(v) for v in criteria):
                raise DecisionError("Score criteria require string, object, or array descriptions.")
        elif criteria is not None:
            if not isinstance(criteria, dict) or set(criteria) - {"true", "false"}:
                raise DecisionError("Noul criteria may describe true and false only.")
            if not all(flexible(v) for v in criteria.values()):
                raise DecisionError("Noul criteria require string, object, or array descriptions.")
    try:
        json.dumps(payload, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise DecisionError("Request must contain finite, JSON-serializable values.") from exc


def flexible(value):
    return isinstance(value, (str, dict, list))


def number(value, lower, upper):
    return type(value) in (int, float) and math.isfinite(value) and lower <= value <= upper


def validate_response(response, questions):
    if not isinstance(response, dict) or not isinstance(response.get("model"), str):
        raise ValueError("Invalid response model")
    usage = response.get("usage")
    if not isinstance(usage, dict) or not all(
        type(usage.get(k)) is int and usage[k] >= 0 for k in ("input_tokens", "output_tokens")
    ):
        raise ValueError("Invalid response usage")
    answers = response.get("answers")
    if not isinstance(answers, dict) or set(answers) != set(questions):
        raise ValueError("Response question IDs do not match")
    for qid, question in questions.items():
        answer = answers[qid]
        kind = question["type"]
        if not isinstance(answer, dict) or answer.get("type") != kind:
            raise ValueError("Response type does not match")
        if kind == "noul":
            if not number(answer.get("noul"), 0, 1):
                raise ValueError("Invalid Noul probability")
            continue
        expected = set(question["criteria"]) if kind == "choice" else {str(i) for i in range(len(question["criteria"]))}
        probabilities = answer.get("probabilities")
        if not isinstance(probabilities, dict) or set(probabilities) != expected:
            raise ValueError("Response probability keys do not match")
        if not all(number(p, 0, 1) for p in probabilities.values()) or not math.isclose(sum(probabilities.values()), 1, abs_tol=0.01):
            raise ValueError("Invalid probability distribution")
        if not number(answer.get("confidence"), 0, 1):
            raise ValueError("Invalid confidence")
        if kind == "choice" and (not isinstance(answer.get("choice"), str) or answer["choice"] not in expected):
            raise ValueError("Unknown selected option")
        if kind == "score":
            if not number(answer.get("score"), 0, len(expected) - 1):
                raise ValueError("Invalid score")
            if not isinstance(answer.get("legend"), dict) or set(answer["legend"]) != expected:
                raise ValueError("Invalid score legend")
            if not all(flexible(value) for value in answer["legend"].values()):
                raise ValueError("Invalid score legend descriptions")


def evaluate(payload, timeout=15):
    """Return provider provenance and the unmodified System One response.

    Each provider gets one attempt. Input errors stop the entire chain.
    """
    validate_request(payload)
    if not number(timeout, 0.001, 3600):
        raise DecisionError("Timeout must be finite and between 0.001 and 3600 seconds.")
    providers = [
        ("clef-primary", os.getenv("CLEF_PRIMARY_BASE_URL", "https://clef.create360.ai"), "clef-flash", os.getenv("CLEF_PRIMARY_API_KEY")),
        ("clef-secondary", os.getenv("CLEF_SECONDARY_BASE_URL", "https://clef.aiurl.tw"), "clef-flash", os.getenv("CLEF_SECONDARY_API_KEY")),
        ("jev", "https://api.typesafe.ai", "jev-latest", os.getenv("TYPESAFE_API_KEY")),
    ]
    failures = []
    for name, base_url, model, api_key in providers:
        base_url = base_url.rstrip("/")
        parts = urlsplit(base_url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment or parts.path:
            raise DecisionError(f"{name}: base URL must be an HTTPS origin, without /v1 or credentials.")
        if name == "jev" and not api_key:
            failures.append("jev: TYPESAFE_API_KEY is unset")
            continue
        headers = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "Mozilla/5.0 ClefSkill/1.0"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        data = json.dumps({**payload, "model": model}, ensure_ascii=False, allow_nan=False).encode()
        request = Request(base_url + "/v1/systemone", data=data, headers=headers)
        try:
            with urlopen(request, timeout=timeout) as result:
                response = json.load(result)
            validate_response(response, payload["questions"])
        except HTTPError as exc:
            try:
                error_body = exc.read(8192).decode("utf-8", errors="replace")
            except (OSError, HTTPException):
                error_body = ""
            finally:
                exc.close()
            if "is too large to process" in error_body and "physical batch size" in error_body:
                raise DecisionError(f"{name}: rendered prompt exceeds the physical batch limit; reduce state or split independent questions.") from exc
            # Access failures can be host-specific; malformed requests stop.
            fallback = exc.code == 429 or 500 <= exc.code <= 599 or (name != "jev" and exc.code in (401, 403))
            if not fallback:
                raise DecisionError(f"{name}: HTTP {exc.code}; stopped. Check request, capacity, or provider configuration.") from exc
            failures.append(f"{name}: HTTP {exc.code}")
            continue
        except (URLError, TimeoutError, OSError, HTTPException):
            failures.append(f"{name}: connection failure or timeout")
            continue
        except (ValueError, UnicodeError):
            failures.append(f"{name}: invalid response")
            continue
        return {"provider": {"name": name, "base_url": base_url, "requested_model": model}, "failures": failures, "response": response}
    raise DecisionError("All providers exhausted: " + "; ".join(failures))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", nargs="?", default="-", help="JSON file, or - for stdin")
    parser.add_argument("--timeout", type=float, default=15, help="Seconds per provider (default: 15)")
    args = parser.parse_args()
    try:
        if args.request == "-":
            payload = json.load(sys.stdin)
        else:
            with open(args.request, encoding="utf-8") as file:
                payload = json.load(file)
        result = evaluate(payload, timeout=args.timeout)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (DecisionError, ValueError, OSError) as exc:
        print(f"Decision request failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
