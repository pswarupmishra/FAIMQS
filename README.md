# FA-IQM — Ferro Alloy Incoming Quality Management

Functional starter application based on the FA-IQM functional specification.

## Stack

- React + TypeScript + Vite
- FastAPI
- SQLAlchemy
- SQLite

## Implemented MVP flow

1. Incoming ferro alloy receipt
2. Effective specification resolution
3. Batch-managed receipt
4. Submit for sampling
5. Create sample
6. Collect sample
7. Send to laboratory
8. Receive/start testing
9. Record chemistry results
10. Automatic PASS/FAIL against configured limits
11. Submit laboratory results
12. Approve results
13. Quality review
14. Accept or reject batch
15. RELEASED/BLOCKED/REJECTED state
16. Dashboard and receipt register

The seed chemistry limits are **DEMO / ILLUSTRATIVE only**.

## Run backend

Windows:

```powershell
cd backend
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open API docs at `http://localhost:8000/docs`.

The SQLite database `fa_iqm.db` is created automatically in the backend directory.

## Run frontend

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Demo path

Create a receipt using **FA000123 / Ferro Silicon**, choose any demo supplier, submit for sampling, create the sample, collect it, send it to the lab, receive it, start testing, open the Laboratory Workbench, enter results, save, submit, approve, and finally accept/reject the batch.

For a passing FA000123 example, enter values inside the displayed DEMO limits.

## Important before production

This starter is intentionally an MVP. Before plant deployment add:

- AD/OIDC authentication
- role-based authorization
- immutable audit trail
- specification administration/approval UI
- supplier-material approval mapping
- configurable sampling plans
- retest/resampling workflow
- conditional acceptance and hold/release authorization
- attachment/COA storage
- QR/sample label printing
- Alembic migrations
- concurrency/version controls
- comprehensive automated tests
- SAP/ERP interfaces as required

Quality release rules must remain server-side.

## Configuration masters and dated specification control

The application now includes a **Configuration** workspace with:

- Ferro alloy material master (material code, description, base UOM)
- Supplier master
- Reusable quality attribute master
- Material quality specification master with optional supplier-specific scope
- Mandatory **Valid From** and **Valid To** dates
- Overlap prevention for approved specifications in the same material/supplier scope

At incoming receipt creation, FA-IQM resolves the approved specification using the **Receipt / Transaction Date**. The resolved specification ID is stored on the receipt. All sample requirements and laboratory PASS/FAIL evaluation then use that locked specification, preserving the quality rule that applied when the batch was received even if a newer specification becomes effective later.
