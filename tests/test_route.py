import copy
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).parents[1] / "skills/clef-jev/scripts"
sys.path.insert(0, str(SCRIPT_DIR))
spec = importlib.util.spec_from_file_location("decision_route", SCRIPT_DIR / "route.py")
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)

CONTEXT = {
    "task": {"request": "Investigate independent API and UI errors."},
    "runtime": {"agent": "example-host", "catalog_source": "native model listing",
                "current_model": "model-a", "can_switch_model": False,
                "models": [{"id": "model-a", "available": True, "targets": ["current", "subagent"], "level": "balanced"},
                           {"id": "model-b", "available": True, "targets": ["current", "subagent"], "level": "deep"}],
                "subagents": {"available": True, "free_slots": 2, "can_choose_model": True}},
}


def execution(mode):
    return {"response": {"answers": {"execution": {"choice": mode}, "complexity": {"score": 2.2}}}}


def selection(model):
    return {"response": {"answers": {"model": {"choice": model}}}}


class RoutingTests(unittest.TestCase):
    def test_parallel_plan_uses_a_real_worker_model(self):
        with patch.object(router, "evaluate", side_effect=[execution("parallel"), selection("model-b")]):
            result = router.route(CONTEXT)
        self.assertEqual(result["plan"]["execution"], "parallel")
        self.assertEqual(result["plan"]["model_id"], "model-b")
        self.assertEqual(result["plan"]["model_level"], "deep")
        self.assertEqual(result["plan"]["max_subagents"], 2)

    def test_missing_subagent_permission_removes_delegation_candidates(self):
        context = copy.deepcopy(CONTEXT)
        context["runtime"]["subagents"]["available"] = False
        with patch.object(router, "evaluate", side_effect=[execution("current"), selection("model-a")]) as send:
            result = router.route(context)
        self.assertEqual(set(send.call_args_list[0].args[0]["questions"]["execution"]["criteria"]), {"current"})
        self.assertFalse(result["plan"]["spawn_subagent"])

    def test_model_change_without_host_support_is_a_recommendation(self):
        with patch.object(router, "evaluate", side_effect=[execution("current"), selection("model-b")]):
            result = router.route(CONTEXT)
        self.assertEqual(result["plan"]["model_application"], "recommendation_only")

    def test_explicit_model_is_preserved(self):
        context = copy.deepcopy(CONTEXT)
        context["task"]["requested_model"] = "model-a"
        with patch.object(router, "evaluate", return_value=execution("delegate")) as send:
            result = router.route(context)
        self.assertEqual(result["plan"]["model_id"], "model-a")
        self.assertEqual(send.call_count, 1)

    def test_unavailable_requested_model_stops_before_inference(self):
        context = copy.deepcopy(CONTEXT)
        context["task"]["requested_model"] = "missing"
        with patch.object(router, "evaluate") as send:
            with self.assertRaises(router.DecisionError):
                router.route(context)
        send.assert_not_called()

    def test_inherited_worker_model_is_preserved(self):
        context = copy.deepcopy(CONTEXT)
        context["runtime"]["subagents"].update(can_choose_model=False, default_model="model-a")
        with patch.object(router, "evaluate", return_value=execution("delegate")):
            result = router.route(context)
        self.assertEqual(result["plan"]["model_id"], "model-a")

    def test_provider_secrets_are_omitted_from_the_catalog(self):
        context = copy.deepcopy(CONTEXT)
        context["runtime"]["models"][0]["api_key"] = "secret-placeholder"
        with patch.object(router, "evaluate", side_effect=[execution("current"), selection("model-a")]) as send:
            router.route(context)
        self.assertNotIn("api_key", send.call_args_list[0].args[0]["state"]["models"][0])

    def test_reasoning_level_comes_from_selected_models_native_options(self):
        context = copy.deepcopy(CONTEXT)
        context["runtime"]["models"][1]["reasoning_levels"] = ["low", "high"]
        context["runtime"]["subagents"]["can_set_reasoning_effort"] = True
        effort = {"response": {"answers": {"effort": {"choice": "high"}}}}
        with patch.object(router, "evaluate", side_effect=[execution("delegate"), selection("model-b"), effort]):
            result = router.route(context)
        self.assertEqual(result["plan"]["reasoning_effort"], "high")
        self.assertEqual(result["plan"]["effort_application"], "host_supported")

    def test_unsupported_requested_effort_stops_before_inference(self):
        context = copy.deepcopy(CONTEXT)
        context["task"]["requested_effort"] = "unsupported"
        with patch.object(router, "evaluate") as send:
            with self.assertRaises(router.DecisionError):
                router.route(context)
        send.assert_not_called()

    def test_route_cannot_choose_an_unavailable_execution_mode(self):
        context = copy.deepcopy(CONTEXT)
        context["runtime"]["subagents"]["available"] = False
        with patch.object(router, "evaluate", return_value=execution("parallel")):
            with self.assertRaises(router.DecisionError):
                router.route(context)

    def test_route_cannot_select_a_model_outside_the_live_catalog(self):
        with patch.object(router, "evaluate", side_effect=[execution("current"), selection("invented-model")]):
            with self.assertRaises(router.DecisionError):
                router.route(CONTEXT)


if __name__ == "__main__":
    unittest.main()
