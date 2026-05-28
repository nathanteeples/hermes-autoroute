from hermes_autoroute.scoring import extract_prompt_features, score_candidate
from hermes_autoroute.types import HealthRecord, ModelRecord


def test_extract_prompt_features_routes_small_prompt_to_tiny():
    features = extract_prompt_features(
        {"model": "auto", "messages": [{"role": "user", "content": "Say hello"}]}
    )

    assert features.task_class == "tiny"
    assert features.prompt_tokens_estimate > 0


def test_extract_prompt_features_routes_important_prompt_to_critical():
    features = extract_prompt_features(
        {
            "model": "auto",
            "messages": [
                {
                    "role": "user",
                    "content": "Production auth outage. Investigate the database migration and fix credentials safely.",
                }
            ],
        }
    )

    assert features.task_class == "critical"


def test_score_candidate_filters_toolless_model_when_tools_required():
    features = extract_prompt_features(
        {
            "model": "auto",
            "messages": [{"role": "user", "content": "Use tools to inspect this."}],
            "tools": [{"type": "function", "function": {"name": "x"}}],
        }
    )
    model = ModelRecord(endpoint="e", model="m", supports_tools=False)

    assert score_candidate(model, None, features, {}) is None


def test_score_candidate_prefers_healthy_model():
    features = extract_prompt_features(
        {"model": "auto/standard", "messages": [{"role": "user", "content": "Summarize this."}]}
    )
    model = ModelRecord(endpoint="e", model="fast-mini", quality_tier=0.5)
    health = HealthRecord(endpoint="e", model="fast-mini", status="healthy", success_count=10)

    score = score_candidate(model, health, features, {})

    assert score is not None
    assert score.score > 0

