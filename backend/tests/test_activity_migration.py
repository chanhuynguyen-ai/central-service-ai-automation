from datetime import UTC, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from app.core.config import settings

BASELINE = "e6a0c3f5b712"
HEAD = "f7b1d4a6c823"


def migrated_database(tmp_path, monkeypatch, target=HEAD):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'migration.db'}")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    command.upgrade(config, target)
    return config, sa.create_engine(settings.database_url)


def seed_old_records(engine):
    tables = sa.MetaData()
    tables.reflect(engine)
    recorded = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    with engine.begin() as con:
        con.execute(tables.tables["users"].insert().values(
            id=1, email="history@example.test", full_name="Historical requester", department="Finance",
            role="employee", hashed_password="never-used", is_active=True, created_at=recorded,
        ))
        con.execute(tables.tables["request_types"].insert().values(id=1, code="OLD", category="IT", is_active=True, created_at=recorded))
        con.execute(tables.tables["request_type_versions"].insert().values(id=1, request_type_id=1, version=1,
            title="Historical form", form_schema={"sections": []}, status="PUBLISHED", created_at=recorded))
        con.execute(tables.tables["service_requests"].insert().values(id=1, reference="DRF-OLD", title="Historical request",
            description="Retain the original historical request.", category="IT", priority="medium", status="approved",
            department="Finance", requester_id=1, submitted_at=recorded, due_at=None, updated_at=recorded,
            request_type_version_id=1, form_data={"secret": "private"}, draft_revision=1,
            workflow_attempt=1, approval_state="approved", fulfillment_state="not_queued"))
        for event_type, details in [
            ("request_submitted", {"attempt": 1, "password": "do-not-copy"}),
            ("approval_decided", {"attempt": 1, "decision": "approve", "comment": "do-not-copy"}),
            ("draft_updated", {"revision": 5}),
            ("approval_decided", {"decision": {"unexpected": "object"}}),
        ]:
            con.execute(tables.tables["audit_events"].insert().values(request_id=1, actor_id=1, event_type=event_type,
                details=details, created_at=recorded))
    return recorded


def test_upgrade_backfills_only_known_events_and_preserves_existing_data(tmp_path, monkeypatch):
    config, engine = migrated_database(tmp_path, monkeypatch, BASELINE)
    recorded = seed_old_records(engine)
    command.upgrade(config, HEAD)
    metadata = sa.MetaData()
    metadata.reflect(engine)
    with engine.connect() as con:
        rows = con.execute(sa.select(metadata.tables["request_events"]).order_by(sa.text("id"))).mappings().all()
        assert [row["event_type"] for row in rows] == ["REQUEST_SUBMITTED", "APPROVAL_APPROVED"]
        assert len({row["source_audit_id"] for row in rows}) == 2
        assert all(row["payload"]["backfilled"] for row in rows)
        assert all(row["created_at"].replace(tzinfo=UTC) == recorded for row in rows)
        assert "do-not-copy" not in str([row["payload"] for row in rows])
        assert con.execute(sa.text("SELECT COUNT(*) FROM audit_events")).scalar_one() == 4
        assert con.execute(sa.text("SELECT title FROM service_requests WHERE id=1")).scalar_one() == "Historical request"
    # Repeating upgrade is idempotent, without replaying the backfill.
    command.upgrade(config, HEAD)
    with engine.connect() as con:
        assert con.execute(sa.text("SELECT COUNT(*) FROM request_events")).scalar_one() == 2
    with pytest.raises(RuntimeError, match="Refusing"):
        command.downgrade(config, BASELINE)
    engine.dispose()


def test_migrated_sqlite_blocks_raw_sql_history_mutation(tmp_path, monkeypatch):
    config, engine = migrated_database(tmp_path, monkeypatch, BASELINE)
    seed_old_records(engine)
    command.upgrade(config, HEAD)
    with engine.begin() as con:
        con.execute(sa.text("INSERT INTO request_comments (request_id,author_user_id,body,visibility,client_token,created_at) "
                            "VALUES (1,1,'Original','REQUESTER_VISIBLE','example','2026-01-02 03:04:05')"))
    for table in ("request_events", "request_comments", "audit_events"):
        for statement in (f"UPDATE {table} SET id=id", f"DELETE FROM {table}"):
            with engine.begin() as con, pytest.raises(sa.exc.DBAPIError, match="append-only"):
                con.execute(sa.text(statement))
    with engine.connect() as con:
        assert con.execute(sa.text("SELECT body FROM request_comments")).scalar_one() == "Original"
    engine.dispose()


def test_empty_migration_can_downgrade_without_losing_data(tmp_path, monkeypatch):
    config, engine = migrated_database(tmp_path, monkeypatch)
    command.downgrade(config, BASELINE)
    assert "request_comments" not in sa.inspect(engine).get_table_names()
    assert "resource_type" not in {column["name"] for column in sa.inspect(engine).get_columns("audit_events")}
    command.upgrade(config, HEAD)
    assert "request_events" in sa.inspect(engine).get_table_names()
    engine.dispose()
