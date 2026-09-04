# CentralOps AI - Hướng dẫn chạy project và quy trình phát triển

> **Project:** CentralOps AI / Central Service AI Automation  
> **Mục tiêu:** Chạy project ổn định trên Windows 11, phát triển theo roadmap, và duy trì Git workflow chuyên nghiệp với một branch riêng cho từng mục thay đổi.

---

## 1. Cách khuyến nghị: chạy toàn bộ bằng Docker Desktop

Đây là cách nên dùng khi demo với HR/recruiter hoặc khi muốn kiểm tra toàn bộ stack nhanh nhất.

### 1.1. Yêu cầu

Cài sẵn:

- Git
- Docker Desktop
- Docker Compose v2 (đi kèm Docker Desktop)

Kiểm tra trong PowerShell:

```powershell
git --version
docker --version
docker compose version
```

### 1.2. Mở project

```powershell
cd C:\duong-dan\toi\CentralOps-AI
```

Ví dụ:

```powershell
cd C:\AI_project\central-service-ai-automation
```

### 1.3. Chạy stack

```powershell
docker compose up --build
```

Lần đầu có thể mất vài phút vì Docker cần build image và tải dependency.

Khi muốn chạy ở background:

```powershell
docker compose up -d --build
```

### 1.4. Kiểm tra các service

Mở trình duyệt:

- Frontend: `http://localhost:3000`
- FastAPI Swagger: `http://localhost:8000/docs`
- API health: `http://localhost:8000/health`
- API readiness: `http://localhost:8000/ready`
- MinIO Console: `http://localhost:9001`

Kiểm tra container:

```powershell
docker compose ps
```

Kỳ vọng các service chính ở trạng thái running/healthy:

```text
database
redis
minio
api
web
```

### 1.5. Demo account

| Role | Email | Password |
|---|---|---|
| Employee | `employee@centralops.demo` | `Employee123!` |
| Approver | `approver@centralops.demo` | `Approver123!` |
| Admin | `admin@centralops.demo` | `Admin123!` |

Chỉ sử dụng các tài khoản này cho local demo.

### 1.6. Dừng project

```powershell
docker compose down
```

Dừng và xóa cả local database/volume:

```powershell
docker compose down -v
```

> **Cảnh báo:** `-v` xóa dữ liệu PostgreSQL, Redis và MinIO local. Chỉ sử dụng khi bạn muốn reset môi trường hoàn toàn.

---

# 2. Chạy project theo chế độ development

Chế độ này phù hợp khi đang code vì backend/frontend có thể chạy riêng và reload nhanh hơn.

## 2.1. Backend - FastAPI

### Yêu cầu

- Python 3.11+
- `uv`

Kiểm tra:

```powershell
python --version
uv --version
```

Nếu chưa có `uv`, cài bằng PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Sau đó đóng và mở lại PowerShell.

### Cài dependency

Từ project root:

```powershell
cd backend
Copy-Item ..\.env.example .env
uv sync --extra dev
```

### Chạy migration

```powershell
uv run alembic upgrade head
```

Kiểm tra migration hiện tại:

```powershell
uv run alembic current
```

### Chạy FastAPI

```powershell
uv run uvicorn app.main:app --reload --port 8000
```

Kiểm tra:

```text
http://localhost:8000/health
http://localhost:8000/ready
http://localhost:8000/docs
```

Backend mặc định local có thể sử dụng SQLite theo `.env.example`, giúp chạy nhanh mà không bắt buộc PostgreSQL.

---

## 2.2. Frontend - React/TypeScript

### Yêu cầu

Repository hiện yêu cầu:

```text
Node.js >= 22.13.0
```

Kiểm tra:

```powershell
node --version
npm --version
```

### Cài dependency

Mở **PowerShell thứ hai**, tại project root:

```powershell
npm ci
```

### Chạy frontend trên Windows PowerShell

Các script frontend hiện tại chứa cú pháp đặt environment variable kiểu Unix. Vì vậy, để tránh lỗi trên PowerShell, sử dụng trực tiếp:

```powershell
$env:NEXT_PUBLIC_API_URL="http://localhost:8000/api/v1"
$env:WRANGLER_LOG_PATH=".wrangler/wrangler.log"
npx vite
```

Sau đó mở:

```text
http://localhost:3000
```

> Một improvement nhỏ trong tương lai sẽ chuẩn hóa npm scripts thành cross-platform để `npm run dev` chạy giống nhau trên Windows/Linux/macOS.

---

# 3. Kiểm tra project sau khi chạy

## 3.1. Backend test

```powershell
cd backend
uv run ruff check app tests
uv run pytest --cov=app
```

## 3.2. Frontend checks

Từ project root:

```powershell
npm run typecheck
npm run lint
npm run build
```

## 3.3. Data-quality exercise

Từ project root:

```powershell
python scripts/clean_service_requests.py
```

Output:

```text
data/generated/service_requests_clean.csv
data/generated/data_quality_report.json
```

---

# 4. Flow demo nên kiểm tra sau khi project chạy

Thực hiện theo thứ tự:

```text
Employee login
    -> Create request
    -> AI triage/classification
    -> Submit request
    -> Approver login
    -> Approve/Reject
    -> Check request status
    -> Open analytics
    -> Test policy assistant
    -> Review Swagger API
```

Ở giai đoạn hiện tại đây là POC flow. Workflow engine đầy đủ sẽ được xây ở các sprint sau.

---

# 5. Troubleshooting trên Windows

## Docker Desktop chưa chạy

Lỗi thường gặp:

```text
Cannot connect to the Docker daemon
```

Giải pháp:

1. Mở Docker Desktop.
2. Chờ Docker Engine báo Running.
3. Chạy lại:

```powershell
docker compose up -d --build
```

## Port 3000 hoặc 8000 đang bị chiếm

Kiểm tra:

```powershell
netstat -ano | findstr :3000
netstat -ano | findstr :8000
```

Dừng process nếu đó là service cũ không còn cần thiết:

```powershell
taskkill /PID <PID> /F
```

## Database migration lỗi do local volume cũ

Trước tiên xem log:

```powershell
docker compose logs api
docker compose logs database
```

Chỉ khi không cần dữ liệu local cũ mới reset:

```powershell
docker compose down -v
docker compose up -d --build
```

## Frontend không gọi được API

Kiểm tra backend trước:

```text
http://localhost:8000/health
```

Sau đó kiểm tra frontend environment:

```powershell
$env:NEXT_PUBLIC_API_URL
```

Kỳ vọng:

```text
http://localhost:8000/api/v1
```

---

# 6. Git workflow bắt buộc cho project

Từ thời điểm này, **mỗi mục thay đổi độc lập phải nằm trên một branch riêng**.

Không phát triển trực tiếp trên `main`.

## Quy trình chuẩn

### Bước 1 - Đồng bộ main

```powershell
git checkout main
git pull origin main
```

### Bước 2 - Tạo branch mới

Ví dụ:

```powershell
git checkout -b feat/organization-rbac
```

### Bước 3 - Code và kiểm tra

```powershell
git status
git diff
```

Chạy test liên quan trước khi commit.

### Bước 4 - Commit

```powershell
git add .
git commit -m "feat(auth): normalize organization and RBAC model"
```

### Bước 5 - Push branch

```powershell
git push -u origin feat/organization-rbac
```

### Bước 6 - Pull Request

Tạo PR:

```text
feat/organization-rbac -> main
```

Chỉ merge khi:

- test pass,
- migration chạy từ clean database,
- không commit secrets,
- docs liên quan đã được update,
- thay đổi đã được review.

---

# 7. Branch naming convention

Sử dụng:

```text
feat/<feature>
fix/<bug>
docs/<documentation>
refactor/<area>
test/<area>
chore/<maintenance>
```

Ví dụ roadmap:

```text
docs/run-project-guide
feat/organization-rbac
feat/request-catalog-dynamic-forms
feat/workflow-engine
feat/approval-inbox
feat/audit-timeline
feat/service-fulfillment
feat/notifications-worker
feat/attachments-minio
feat/ai-intake-evaluation
feat/policy-rag
feat/power-platform-evidence
chore/observability-deployment
```

Không gom các feature không liên quan vào cùng một branch.

---

# 8. Commit convention

Sử dụng Conventional Commits:

```text
feat(scope): add capability
fix(scope): correct behavior
refactor(scope): restructure without feature change
test(scope): add or improve tests
docs(scope): update documentation
chore(scope): tooling/infrastructure maintenance
```

Ví dụ:

```text
docs(dev): add Windows and Docker run guide
feat(auth): add normalized roles and departments
feat(workflow): resolve manager approval tasks
fix(approvals): prevent duplicate approval decisions
test(workflow): cover manager approval lifecycle
```

---

# 9. Chuẩn báo cáo bắt buộc sau mỗi lần update

Mỗi lần project được thay đổi, báo cáo phải có đúng các phần sau.

## Update Report

**Branch**

```text
feat/example-feature
```

**Mục tiêu**

Mô tả ngắn vấn đề branch này giải quyết.

**Đã thay đổi**

- Thay đổi 1.
- Thay đổi 2.
- Thay đổi 3.

**Files changed**

```text
path/file-1
path/file-2
path/file-3
```

**Database migration**

```text
Có / Không
```

Nếu có, ghi migration revision.

**Cách kiểm tra**

```powershell
<commands>
```

**Kết quả test**

```text
PASS / FAIL / NOT VERIFIED
```

Không được ghi PASS nếu test chưa thực sự được chạy.

**Suggested commit**

```text
feat(scope): description
```

**Next step**

Một mục duy nhất nên làm tiếp theo.

---

# 10. Trạng thái hiện tại của roadmap

Project hiện đã có POC mạnh ở:

- FastAPI backend.
- React/TypeScript frontend.
- PostgreSQL/Docker foundation.
- Auth cơ bản.
- AI triage.
- Policy assistant.
- Analytics.
- Power Platform integration specifications.
- CI/UAT/reviewer documentation.

Nhưng core enterprise workflow vẫn cần được nâng cấp.

Immediate next sprint:

```text
feat/organization-rbac
```

---

# 11. Bước cải tiến tiếp theo - Organization & RBAC

## Mục tiêu

Thay thế identity model đơn giản hiện tại:

```text
User.department = string
User.role = string
```

bằng organization model thực tế có quan hệ rõ ràng:

```text
Department
    -> Users
    -> Manager relationship

User
    -> UserRoles
    -> Roles

ServiceTeam
    -> Members
    -> Service Lead
```

Đây là nền bắt buộc trước khi xây manager-based workflow routing.

## Branch

```powershell
git checkout main
git pull origin main
git checkout -b feat/organization-rbac
```

## Scope của branch

Chỉ làm:

1. `departments` table.
2. `roles` table.
3. `user_roles` table.
4. `service_teams` table.
5. service-team membership.
6. `users.manager_id`.
7. `users.department_id`.
8. centralized permission helpers.
9. seed organization relationships.
10. Alembic migration.
11. API/domain tests liên quan.

Không làm trong branch này:

- workflow engine,
- dynamic forms,
- RAG,
- Power BI,
- UI redesign,
- AI agent.

## Acceptance criteria

Branch chỉ hoàn thành khi:

- deactivated user không đăng nhập được,
- employee chỉ xem resource được phép,
- self-approval bị chặn,
- direct manager được resolve từ database,
- service-team membership được resolve từ database,
- role được resolve qua `user_roles`,
- clean database chạy được bằng `alembic upgrade head`,
- tests liên quan đều pass.

## Suggested commit sequence

Không cần nhét cả branch vào một commit duy nhất. Có thể dùng:

```text
feat(org): add departments and manager relationships
feat(auth): normalize roles and user-role assignments
feat(service-teams): add service team membership model
refactor(auth): centralize permission policies
test(auth): cover organization and RBAC authorization
```

PR cuối:

```text
feat/organization-rbac -> main
```

---

# 12. Roadmap branch sau Organization/RBAC

Sau khi branch `feat/organization-rbac` được test và merge:

```text
1. feat/request-catalog-dynamic-forms
2. feat/workflow-engine
3. feat/approval-inbox
4. feat/audit-timeline
5. feat/service-fulfillment
6. feat/notifications-worker
7. feat/attachments-minio
8. feat/ai-intake-evaluation
9. feat/policy-rag
10. feat/power-platform-evidence
11. chore/observability-deployment
```

Nguyên tắc quan trọng:

> Hoàn thiện Request -> Approval -> Fulfillment trước khi mở rộng AI sâu hơn.

AI hỗ trợ intake, extraction, retrieval và summarization; authorization, workflow routing và approval vẫn phải deterministic/human-owned.

---

# 13. Checklist trước mỗi lần push

```text
[ ] Đang ở đúng feature branch
[ ] git status đã kiểm tra
[ ] Không có .env/secret bị commit
[ ] Migration đã test nếu schema thay đổi
[ ] Backend tests pass
[ ] Frontend typecheck/build pass nếu frontend thay đổi
[ ] Documentation đã update nếu behavior thay đổi
[ ] Commit message đúng convention
[ ] Update Report đã ghi rõ thay đổi
```

---

## Project development rule

Từ đây, project sẽ được phát triển theo chu kỳ:

```text
1 objective
    -> 1 dedicated branch
        -> focused implementation
            -> tests
                -> documentation
                    -> update report
                        -> commit
                            -> PR
                                -> merge
```

Cách làm này giúp repository dễ review, dễ rollback, dễ trình bày với recruiter và thể hiện quy trình engineering chuyên nghiệp.
