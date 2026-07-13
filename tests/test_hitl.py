import pytest

from conftest import org
from studio_compliance.hitl import HITLStore
from studio_compliance.hitl import main as hitl_cli
from studio_compliance.policy import evaluate_entities
from studio_compliance.schemas import ExclusivityDeal, HITLStatus, IntakeConstraints


def make_finding():
    constraints = IntakeConstraints(
        exclusivity_deals=ExclusivityDeal(primary_sponsor="S", restricted_competitors=["Facebook"])
    )
    return evaluate_entities([org("Facebook")], constraints)[0]


def test_create_and_get_roundtrip(tmp_path):
    store = HITLStore(str(tmp_path / "q"))
    finding = make_finding()
    record = store.create("RUN-1", "gs://b/a.txt", finding)
    assert finding.hitl_token == record.token
    loaded = store.get(record.token)
    assert loaded.status == HITLStatus.PENDING
    assert loaded.finding.entity == "Facebook"


def test_list_filters_by_status_and_resolve_lifecycle(tmp_path):
    store = HITLStore(str(tmp_path / "q"))
    r1 = store.create("RUN-1", "gs://b/a.txt", make_finding())
    r2 = store.create("RUN-1", "gs://b/a.txt", make_finding())
    assert len(store.list(HITLStatus.PENDING)) == 2

    resolved = store.resolve(r1.token, HITLStatus.APPROVED, reviewer="J. Doe", note="waiver")
    assert resolved.resolved_at is not None
    assert len(store.list(HITLStatus.PENDING)) == 1
    assert store.resolutions_for_run("RUN-1") == {
        r1.token: HITLStatus.APPROVED,
        r2.token: HITLStatus.PENDING,
    }


def test_double_resolve_rejected(tmp_path):
    store = HITLStore(str(tmp_path / "q"))
    record = store.create("RUN-1", "gs://b/a.txt", make_finding())
    store.resolve(record.token, HITLStatus.ENFORCED, reviewer="A")
    with pytest.raises(ValueError):
        store.resolve(record.token, HITLStatus.APPROVED, reviewer="B")


def test_resolve_unknown_token_raises(tmp_path):
    store = HITLStore(str(tmp_path / "q"))
    with pytest.raises(KeyError):
        store.resolve("HITL-NOPE", HITLStatus.APPROVED, reviewer="A")


def test_cli_list_and_approve(tmp_path, capsys):
    root = str(tmp_path / "q")
    store = HITLStore(root)
    record = store.create("RUN-1", "gs://b/a.txt", make_finding())

    assert hitl_cli(["--store", root, "list"]) == 0
    assert record.token in capsys.readouterr().out

    assert hitl_cli(["--store", root, "approve", record.token, "--reviewer", "QA"]) == 0
    assert store.get(record.token).status == HITLStatus.APPROVED
