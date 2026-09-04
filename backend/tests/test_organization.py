from fastapi.testclient import TestClient

from app.db.seed import seed_data
from app.db.session import get_db
from app.models.models import (
    Department,
    Role,
    ServiceTeam,
    ServiceTeamMember,
    User,
    UserRole,
)
from app.services.organization import (
    require_direct_manager,
    resolve_direct_manager,
)


def _open_test_db(client: TestClient):
    db_provider = client.app.dependency_overrides[get_db]
    db_generator = db_provider()
    db = next(db_generator)

    return db_generator, db


def test_employee_has_normalized_department_and_manager(
    client: TestClient,
) -> None:
    db_generator, db = _open_test_db(client)

    try:
        employee = (
            db.query(User)
            .filter(User.email == "employee@centralops.demo")
            .first()
        )

        assert employee is not None
        assert employee.department_ref is not None
        assert employee.department_ref.code == "FINANCE"

        assert employee.manager is not None
        assert employee.manager.email == "manager.finance@centralops.demo"
    finally:
        db_generator.close()


def test_direct_manager_resolver(
    client: TestClient,
) -> None:
    db_generator, db = _open_test_db(client)

    try:
        employee = (
            db.query(User)
            .filter(User.email == "employee@centralops.demo")
            .first()
        )

        assert employee is not None

        manager = resolve_direct_manager(employee)

        assert manager is not None
        assert manager.email == "manager.finance@centralops.demo"
        assert require_direct_manager(employee).id == manager.id
    finally:
        db_generator.close()


def test_finance_manager_has_normalized_roles(
    client: TestClient,
) -> None:
    db_generator, db = _open_test_db(client)

    try:
        manager = (
            db.query(User)
            .filter(User.email == "manager.finance@centralops.demo")
            .first()
        )

        assert manager is not None

        role_codes = {
            assignment.role.code
            for assignment in manager.role_assignments
        }

        assert role_codes == {
            "EMPLOYEE",
            "MANAGER",
            "APPROVER",
        }
    finally:
        db_generator.close()


def test_central_service_team_has_lead_and_members(
    client: TestClient,
) -> None:
    db_generator, db = _open_test_db(client)

    try:
        team = (
            db.query(ServiceTeam)
            .filter(ServiceTeam.code == "CENTRAL_SERVICE")
            .first()
        )

        assert team is not None
        assert team.lead is not None
        assert team.lead.email == "service.lead@centralops.demo"

        member_emails = {
            membership.user.email
            for membership in team.memberships
        }

        assert member_emails == {
            "service.lead@centralops.demo",
            "approver@centralops.demo",
            "service.agent@centralops.demo",
        }
    finally:
        db_generator.close()


def test_seed_data_is_idempotent(
    client: TestClient,
) -> None:
    db_generator, db = _open_test_db(client)

    try:
        counts_before = {
            "departments": db.query(Department).count(),
            "roles": db.query(Role).count(),
            "users": db.query(User).count(),
            "user_roles": db.query(UserRole).count(),
            "teams": db.query(ServiceTeam).count(),
            "members": db.query(ServiceTeamMember).count(),
        }

        seed_data(db)

        counts_after = {
            "departments": db.query(Department).count(),
            "roles": db.query(Role).count(),
            "users": db.query(User).count(),
            "user_roles": db.query(UserRole).count(),
            "teams": db.query(ServiceTeam).count(),
            "members": db.query(ServiceTeamMember).count(),
        }

        assert counts_after == counts_before
    finally:
        db_generator.close()