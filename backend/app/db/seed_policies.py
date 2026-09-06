from datetime import UTC, datetime

from app.db.session import SessionLocal
from app.models.knowledge import PolicyDocument
from app.models.models import Department, User
from app.schemas.knowledge import PolicyDocumentCreate
from app.services.knowledge import create_policy_document


def main() -> None:
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@centralops.demo").first()
        if admin is None:
            raise RuntimeError("Run the organization seed before the policy seed")
        finance = db.query(Department).filter(Department.code == "FINANCE").first()
        definitions = [
            PolicyDocumentCreate(
                slug="managed-device-replacement",
                title="Managed Device Replacement Policy",
                version="1.0",
                source_name="demo-managed-device-policy.md",
                access_scope="ALL",
                effective_from=datetime(2026, 1, 1, tzinfo=UTC),
                content=(
                    "# Eligibility\n\nEmployees may request a managed laptop replacement when the assigned "
                    "device has repeated hardware failures, materially interrupts business work, or can no "
                    "longer receive required security updates.\n\n# Request information\n\nThe request should "
                    "state the business impact, preferred managed platform, cost center, and required date. "
                    "Approval of the request does not mean the replacement has already been fulfilled."
                ),
            ),
            PolicyDocumentCreate(
                slug="expense-reimbursement",
                title="Finance Expense Reimbursement Policy",
                version="1.0",
                source_name="demo-finance-reimbursement-policy.md",
                access_scope="DEPARTMENT",
                department_id=finance.id if finance else None,
                effective_from=datetime(2026, 1, 1, tzinfo=UTC),
                content=(
                    "# Reimbursable expenses\n\nFinance employees may submit documented business expenses "
                    "for reimbursement. The request must include the amount, currency, expense date, and "
                    "business purpose. Receipts should be attached when the service form requires them."
                ),
            ),
            PolicyDocumentCreate(
                slug="audit-control-notes",
                title="Audit Control Review Notes",
                version="1.0",
                source_name="demo-audit-control-policy.md",
                access_scope="ROLE",
                role_code="AUDITOR",
                effective_from=datetime(2026, 1, 1, tzinfo=UTC),
                content=(
                    "# Audit review\n\nAuditors may inspect governed lifecycle events and policy evidence needed "
                    "for control testing. This material is restricted to users holding the AUDITOR role."
                ),
            ),
        ]
        for payload in definitions:
            if payload.access_scope == "DEPARTMENT" and payload.department_id is None:
                raise RuntimeError("FINANCE department is required for demo policy seed")
            exists = (
                db.query(PolicyDocument)
                .filter(PolicyDocument.slug == payload.slug, PolicyDocument.version == payload.version)
                .first()
            )
            if exists is None:
                create_policy_document(db, payload, admin)
        db.commit()
        print("Demo policy documents are indexed and ready.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
