from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.seed import seed_data
from app.db.session import Base, get_db
from app.main import app


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
    database_file = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{database_file}",
        connect_args={"check_same_thread": False},
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    with testing_session() as db:
        seed_data(db)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def login(client: TestClient, role: str = "employee") -> dict[str, str]:
    credentials = {
        "employee": ("employee@centralops.demo", "Employee123!"),
        "employee2": ("other.employee@centralops.demo", "Employee123!"),
        "approver": ("approver@centralops.demo", "Approver123!"),
        "admin": ("admin@centralops.demo", "Admin123!"),
    }
    email, password = credentials[role]
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
