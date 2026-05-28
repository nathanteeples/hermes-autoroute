from hermes_autoroute.storage import StateStore
from hermes_autoroute.types import HealthRecord, ModelRecord


def test_state_store_round_trips_models_and_health(tmp_path):
    path = tmp_path / "state.json"
    store = StateStore(path)
    store.upsert_model(ModelRecord(endpoint="local", model="tiny"))
    store.upsert_health(HealthRecord(endpoint="local", model="tiny", status="healthy"))
    store.add_decision({"endpoint": "local", "model": "tiny"})
    store.save()

    loaded = StateStore(path)

    assert loaded.get_models()[0].key == "local:tiny"
    assert loaded.get_health("local:tiny").status == "healthy"
    assert loaded.last_decision()["model"] == "tiny"

