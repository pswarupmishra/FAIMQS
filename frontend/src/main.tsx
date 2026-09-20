import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

const API = "http://localhost:8000/api/v1";
type AnyObj = Record<string, any>;
const localDateTime = () => {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
};
const today = () => localDateTime().slice(0, 10);
function Badge({ children }: { children: React.ReactNode }) {
  return <span className="badge">{children}</span>;
}
type GridSort = [string, (row: any) => any];
function DataGrid({
  rows,
  searchText,
  sortOptions,
  children,
  initialPageSize = 10,
}: {
  rows: any[];
  searchText: (row: any) => string;
  sortOptions: GridSort[];
  children: (pageRows: any[]) => React.ReactNode;
  initialPageSize?: number;
}) {
  const [query, setQuery] = useState(""),
    [sortKey, setSortKey] = useState("0"),
    [direction, setDirection] = useState("asc"),
    [pageSize, setPageSize] = useState(initialPageSize),
    [page, setPage] = useState(1);
  const filtered = rows.filter((row) =>
    searchText(row).toLowerCase().includes(query.trim().toLowerCase()),
  );
  const getter = sortOptions[Number(sortKey)]?.[1] || (() => "");
  const sorted = [...filtered].sort((left, right) => {
    const a = getter(left),
      b = getter(right);
    const comparison =
      typeof a === "number" && typeof b === "number"
        ? a - b
        : String(a ?? "").localeCompare(String(b ?? ""), undefined, {
            numeric: true,
          });
    return direction === "asc" ? comparison : -comparison;
  });
  const pageCount = Math.max(1, Math.ceil(sorted.length / pageSize));
  const safePage = Math.min(page, pageCount);
  const pageRows = sorted.slice((safePage - 1) * pageSize, safePage * pageSize);
  useEffect(() => setPage(1), [query, sortKey, direction, pageSize, rows.length]);
  return (
    <div className="dataGrid">
      <div className="dataGridToolbar">
        <label>
          Filter
          <input
            value={query}
            placeholder="Filter rows…"
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <label>
          Sort by
          <select value={sortKey} onChange={(event) => setSortKey(event.target.value)}>
            {sortOptions.map(([label], index) => (
              <option value={index} key={label}>{label}</option>
            ))}
          </select>
        </label>
        <label>
          Direction
          <select value={direction} onChange={(event) => setDirection(event.target.value)}>
            <option value="asc">Ascending</option>
            <option value="desc">Descending</option>
          </select>
        </label>
        <label>
          Rows
          <select value={pageSize} onChange={(event) => setPageSize(Number(event.target.value))}>
            {[10, 25, 50, 100].map((size) => <option key={size}>{size}</option>)}
          </select>
        </label>
        <span className="dataGridCount">{filtered.length.toLocaleString()} row{filtered.length === 1 ? "" : "s"}</span>
      </div>
      {children(pageRows)}
      <div className="dataGridPager">
        <button type="button" disabled={safePage === 1} onClick={() => setPage(1)}>First</button>
        <button type="button" disabled={safePage === 1} onClick={() => setPage(safePage - 1)}>Previous</button>
        <span>Page <b>{safePage}</b> of <b>{pageCount}</b></span>
        <button type="button" disabled={safePage === pageCount} onClick={() => setPage(safePage + 1)}>Next</button>
        <button type="button" disabled={safePage === pageCount} onClick={() => setPage(pageCount)}>Last</button>
      </div>
    </div>
  );
}
function App() {
  const [tab, setTab] = useState("dashboard"),
    [dash, setDash] = useState<AnyObj>({}),
    [receipts, setReceipts] = useState<any[]>([]),
    [blockedReceipts, setBlockedReceipts] = useState<any[]>([]),
    [materials, setMaterials] = useState<any[]>([]),
    [suppliers, setSuppliers] = useState<any[]>([]),
    [plants, setPlants] = useState<any[]>([]),
    [smsLocations, setSmsLocations] = useState<any[]>([]),
    [stores, setStores] = useState<any[]>([]),
    [selected, setSelected] = useState<any>(null),
    [tests, setTests] = useState<any[]>([]),
    [msg, setMsg] = useState("");
  const [form, setForm] = useState<any>({
    plant_id: "",
    sms_id: "",
    store_id: "",
    material_id: "",
    supplier_id: "",
    supplier_batch_no: "",
    internal_batch_no: "",
    po_no: "",
    grn_no: "",
    quantity: 20,
    uom: "MT",
    vehicle_no: "",
    receipt_datetime: localDateTime(),
  });
  const get = async (path: string) => {
    const r = await fetch(API + path);
    return r.json();
  };
  const load = async () => {
    setDash(await get("/dashboard"));
    setReceipts(await get("/receipts"));
    setBlockedReceipts(await get("/receipts?release_state=BLOCKED&limit=5000"));
    setMaterials(await get("/materials"));
    setSuppliers(await get("/suppliers"));
    setPlants(await get("/config/plants"));
    setSmsLocations(await get("/config/sms-locations"));
    setStores(await get("/config/store-locations"));
  };
  useEffect(() => {
    load();
  }, []);
  const createReceipt = async (e: any) => {
    e.preventDefault();
    const r = await fetch(API + "/receipts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    if (!r.ok) {
      const d = await r
        .json()
        .catch(() => ({ detail: "Unable to create receipt" }));
      setMsg(d.detail || "Unable to create receipt");
      return;
    }
    setMsg(
      "Receipt created with the quality specification effective on the receipt date.",
    );
    setTab("receipts");
    load();
  };
  const openReceipt = async (id: string) => {
    setSelected(await get("/receipts/" + id));
    setTests([]);
    setTab("detail");
  };
  const act = async (url: string, method = "POST", body?: any) => {
    const r = await fetch(API + url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    const d = await r.json();
    if (!r.ok) {
      setMsg(d.detail || "Action failed");
      return null;
    }
    setMsg("Action completed.");
    if (selected) openReceipt(selected.id);
    load();
    return d;
  };
  const openTests = async (s: any) =>
    setTests(await get("/samples/" + s.id + "/required-tests"));
  const saveTests = async (sid: string) => {
    await act(
      "/samples/" + sid + "/results",
      "PUT",
      tests.map((t) => ({
        specification_attribute_id: t.specification_attribute_id,
        numeric_result:
          t.data_type === "NUMERIC" && t.result !== ""
            ? Number(t.result)
            : null,
        text_result: t.data_type !== "NUMERIC" ? t.result || null : null,
      })),
    );
    await openTests({ id: sid });
  };
  const title =
    tab === "dashboard"
      ? "Quality Control Center"
      : tab === "new"
        ? "Incoming Material Receipt"
        : tab === "detail"
          ? "Batch Quality Record"
          : tab === "config"
            ? "Configuration & Quality Masters"
            : tab === "attention"
              ? "Attention Cockpit"
              : tab === "analysis"
                ? "Batch & Quality Analysis"
              : tab === "report"
                ? "Material Quality Register"
                : tab === "docs"
                  ? "FA-IQM Documentation"
                  : "Incoming Receipts";
  return (
    <div className="app">
      <aside>
        <div className="brand">
          <div className="jswLogoPlate">
            <img src="/jsw-group-logo.webp" alt="JSW Group" />
          </div>
          <div className="brandProduct">
            <b>FA-IQM</b>
            <small>Incoming Quality Management</small>
          </div>
        </div>
        {[
          ["dashboard", "Dashboard"],
          ["receipts", "Receipts"],
          ["new", "New Receipt"],
          ["analysis", "Analysis"],
          ["attention", "Attention Engine"],
          ["report", "Report"],
          ["config", "Configuration"],
          ["docs", "Documentation"],
        ].map(([k, l]) => (
          <button
            key={k}
            className={tab === k ? "active" : ""}
            onClick={() => setTab(k)}
          >
            {l}
          </button>
        ))}
        <div className="asideFoot">
          FERRO ALLOY STORE
          <br />
          <span>Integrated Steel Plant</span>
        </div>
      </aside>
      <main>
        <header>
          <div>
            <h1>{title}</h1>
            <p>Ferro Alloy Store · Laboratory · Quality</p>
          </div>
          <Badge>● SYSTEM ONLINE</Badge>
        </header>
        {msg && (
          <div className="message" onClick={() => setMsg("")}>
            {msg} ×
          </div>
        )}
        {tab === "dashboard" && (
          <>
            <section className="cards">
              {[
                ["Total Receipts", dash.total],
                ["Pending Sampling", dash.pending_sampling],
                ["Lab Pending", dash.lab_pending],
                ["Quality Review", dash.under_review],
                ["On Hold", dash.on_hold],
                ["Released", dash.released],
                ["Rejected", dash.rejected],
              ].map(([a, b]) => (
                <div className="card" key={String(a)}>
                  <small>{a}</small>
                  <strong>{b ?? 0}</strong>
                </div>
              ))}
            </section>
            <section className="panel">
              <h2>Recent Incoming Batches</h2>
              <ReceiptTable rows={receipts.slice(0, 8)} open={openReceipt} />
            </section>
          </>
        )}
        {tab === "receipts" && (
          <>
            <section className="panel blockedReceiptPanel">
              <div className="panelTitle">
                <div><h2>Blocked Batches</h2><p className="muted">Batches awaiting sampling, laboratory completion, quality review, or another release decision.</p></div>
                <div className="panelTitleActions"><Badge>{blockedReceipts.length} BLOCKED</Badge><button className="primary" onClick={() => setTab("new")}>+ New Receipt</button></div>
              </div>
              <ReceiptTable rows={blockedReceipts} open={openReceipt} emptyText="No batches are currently blocked." />
            </section>
            <section className="panel">
              <div className="panelTitle"><div><h2>Material Receipt Register</h2><p className="muted">Complete register of incoming material receipts and their current quality status.</p></div></div>
              <ReceiptTable rows={receipts} open={openReceipt} />
            </section>
          </>
        )}
        {tab === "new" && (
          <section className="panel formPanel">
            <h2>Create Incoming Receipt</h2>
            <p className="muted">
              The system resolves and locks the approved specification effective
              on the receipt transaction date.
            </p>
            <form onSubmit={createReceipt} className="formgrid">
              <label>
                Plant Location
                <select
                  required
                  value={form.plant_id}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      plant_id: e.target.value,
                      sms_id: "",
                      store_id: "",
                    })
                  }
                >
                  <option value="">Select plant</option>
                  {plants
                    .filter((x) => x.active)
                    .map((x) => (
                      <option key={x.id} value={x.id}>
                        {x.plant_code} · {x.plant_name}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                SMS Location
                <select
                  required
                  disabled={!form.plant_id}
                  value={form.sms_id}
                  onChange={(e) =>
                    setForm({ ...form, sms_id: e.target.value, store_id: "" })
                  }
                >
                  <option value="">Select SMS</option>
                  {smsLocations
                    .filter((x) => x.active && x.plant_id === form.plant_id)
                    .map((x) => (
                      <option key={x.id} value={x.id}>
                        {x.sms_code} · {x.sms_name}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                Store Location
                <select
                  required
                  disabled={!form.sms_id}
                  value={form.store_id}
                  onChange={(e) =>
                    setForm({ ...form, store_id: e.target.value })
                  }
                >
                  <option value="">Select store</option>
                  {stores
                    .filter((x) => x.active && x.sms_id === form.sms_id)
                    .map((x) => (
                      <option key={x.id} value={x.id}>
                        {x.store_code} · {x.store_name}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                Material
                <select
                  required
                  value={form.material_id}
                  onChange={(e) =>
                    setForm({ ...form, material_id: e.target.value })
                  }
                >
                  <option value="">Select material</option>
                  {materials.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.material_code} · {m.material_name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Supplier
                <select
                  required
                  value={form.supplier_id}
                  onChange={(e) =>
                    setForm({ ...form, supplier_id: e.target.value })
                  }
                >
                  <option value="">Select supplier</option>
                  {suppliers.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.supplier_code} · {s.supplier_name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Receipt / Transaction Date
                <input
                  required
                  type="datetime-local"
                  value={form.receipt_datetime}
                  onChange={(e) =>
                    setForm({ ...form, receipt_datetime: e.target.value })
                  }
                />
                <span className="hint">
                  Specification validity is evaluated against this timestamp.
                </span>
              </label>
              {[
                ["supplier_batch_no", "Supplier Batch No"],
                ["internal_batch_no", "Internal Batch No"],
                ["po_no", "PO No"],
                ["grn_no", "GRN No"],
                ["vehicle_no", "Vehicle No"],
              ].map(([k, l]) => (
                <label key={k}>
                  {l}
                  <input
                    required={!['vehicle_no', 'grn_no'].includes(k)}
                    value={form[k]}
                    onChange={(e) => setForm({ ...form, [k]: e.target.value })}
                  />
                </label>
              ))}
              <label>
                Quantity
                <input
                  type="number"
                  min="0.001"
                  required
                  step=".001"
                  value={form.quantity}
                  onChange={(e) =>
                    setForm({ ...form, quantity: Number(e.target.value) })
                  }
                />
              </label>
              <label>
                UOM
                <input
                  value={form.uom}
                  onChange={(e) => setForm({ ...form, uom: e.target.value })}
                />
              </label>
              <div className="full actions">
                <button type="button" onClick={() => setTab("receipts")}>
                  Cancel
                </button>
                <button className="primary">Create Receipt</button>
              </div>
            </form>
          </section>
        )}
        {tab === "detail" && selected && (
          <Detail
            r={selected}
            act={act}
            tests={tests}
            setTests={setTests}
            openTests={openTests}
            saveTests={saveTests}
          />
        )}
        {tab === "config" && <ConfigPage notify={setMsg} refreshApp={load} />}{" "}
        {tab === "attention" && <AttentionPage notify={setMsg} />}
        {tab === "analysis" && (
          <AnalysisPage materials={materials} suppliers={suppliers} notify={setMsg} />
        )}
        {tab === "report" && (
          <MaterialQualityReport openReceipt={openReceipt} materials={materials} suppliers={suppliers} />
        )}
        {tab === "docs" && <DocumentationPage />}
      </main>
    </div>
  );
}

function DocumentationPage() {
  const [section, setSection] = useState("overview");
  const nav = [
    ["overview", "Overview"],
    ["configuration", "Configuration Guide"],
    ["logic", "Application Logic"],
    ["user", "User Guide"],
    ["api", "API Documentation"],
  ];
  return (
    <div className="wikiLayout">
      <nav className="wikiNav">
        <div className="wikiNavTitle">Documentation</div>
        {nav.map(([key, label]) => (
          <button
            key={key}
            className={section === key ? "active" : ""}
            onClick={() => setSection(key)}
          >
            {label}
          </button>
        ))}
      </nav>
      <article className="wikiArticle">
        {section === "overview" && (
          <>
            <div className="wikiHero">
              <span className="eyebrow">FA-IQM KNOWLEDGE BASE</span>
              <h2>Incoming Quality Management, explained</h2>
              <p>
                This documentation is written for store users, laboratory teams,
                quality managers, administrators, auditors and developers.
              </p>
            </div>
            <WikiSection title="What the application does">
              <p>
                FA-IQM controls the incoming-quality journey for ferro-alloy
                materials: receipt, sampling, laboratory testing, result
                evaluation, quality disposition and release. Every receipt is
                tied to the material specification version that applied when the
                transaction was created.
              </p>
            </WikiSection>
            <div className="wikiCards">
              <WikiCard
                title="Business users"
                text="Follow a batch from receipt through release, understand exceptions and use the Material Quality Register."
              />
              <WikiCard
                title="Quality teams"
                text="Maintain specifications, enter results, investigate attention events and retain auditable decisions."
              />
              <WikiCard
                title="Technical users"
                text="Use the API, versioned configuration and traceable data model to integrate and extend FA-IQM."
              />
            </div>
            <WikiSection title="Core principles">
              <ul>
                <li>
                  Historical transactions never change when a specification is
                  revised.
                </li>
                <li>
                  The latest material specification version applies to new
                  transactions.
                </li>
                <li>
                  Specification failure remains authoritative; statistical
                  attention is advisory.
                </li>
                <li>
                  Every attention signal retains its receipt, sample, result,
                  specification and configuration lineage.
                </li>
              </ul>
            </WikiSection>
          </>
        )}
        {section === "configuration" && (
          <>
            <WikiTitle
              title="Configuration Guide"
              intro="Set up master data in this order so transactional users always see valid choices."
            />
            <WikiSection title="1. Configure the Plant hierarchy">
              <ol><li>Open <b>Configuration</b> from the main sidebar and keep the <b>Masters</b> tab selected.</li><li>Select <b>Plant</b> in the master-data sidebar.</li><li>Enter a unique Plant Code and Plant Name, then choose <b>Add Plant</b>.</li><li>Under SMS Locations, select the parent plant, enter the SMS code/name and add it.</li><li>Under Store Locations, select the parent SMS, enter the store code/name and add it.</li><li>Confirm every row displays <b>ACTIVE</b>. These choices will cascade on New Receipt.</li></ol>
              <DocScreenshot src="/docs/config-plant.png" alt="Plant, SMS and Store configuration screen" caption="Plant configuration: create the hierarchy from Plant to SMS to Store." />
            </WikiSection>
            <WikiSection title="2. Configure Materials and Suppliers">
              <ol><li>Select <b>Material</b> in the Masters sidebar.</li><li>Enter a unique Material Code, business-friendly Material Name, Description and Base UOM.</li><li>Choose <b>Add Material</b> and confirm it appears in the register.</li><li>Select <b>Supplier</b>, enter a unique supplier code and name, and choose <b>Add Supplier</b>.</li><li>Use Disable only when a supplier must not be selected for new receipts; historical receipts remain unchanged.</li></ol>
              <DocScreenshot src="/docs/config-material.png" alt="Material Master configuration screen" caption="Material Master: maintain identity and unit of measure independently from specifications." />
            </WikiSection>
            <WikiSection title="3. Configure Attribute Groups and Attributes">
              <ol><li>Select <b>Quality Attributes</b> in the Masters sidebar.</li><li>Create an Attribute Group such as Chemistry, Physical Properties or Visual Inspection.</li><li>In Quality Attributes, select the group before entering an attribute.</li><li>Enter a unique code, name and type: Numeric, Category or Yes/No.</li><li>For Numeric, enter UOM and decimal places. For Category, enter comma-separated allowed values.</li><li>Add the attribute and confirm it appears only when its group is selected.</li></ol>
              <DocScreenshot src="/docs/config-attributes.png" alt="Attribute Groups and Quality Attributes configuration" caption="Quality Attributes: group attributes first, then define their data type and validation options." />
            </WikiSection>
            <WikiSection title="4. Create or revise a Quality Specification">
              <ol><li>Open the top-level <b>Quality Spec Sheet</b> tab.</li><li>Select a material. If a specification exists, its latest version and attribute values load automatically.</li><li>Review the read-only <b>New Version</b> number.</li><li>Select an Attribute Group to add its available attributes.</li><li>Enter Minimum, mandatory Aim and Maximum for numeric attributes, or the required target for Category/Yes-No.</li><li>Modify values or use Remove to delete an attribute from the new version.</li><li>Choose <b>Save New Version</b>. The new version becomes enabled; the previous version is retained as disabled history.</li></ol>
              <DocScreenshot src="/docs/config-specification.png" alt="Material Quality Specification configuration" caption="Quality Spec Sheet: edit a working copy and save it as the next immutable version." />
            </WikiSection>
            <WikiSection title="5. Configure the Attention Engine">
              <ol><li>Open <b>Attention Engine</b> from the main sidebar, then select its <b>Configuration</b> tab.</li><li>Keep LATEST_PER_REFERENCE unless repeated tests must be treated independently.</li><li>Set the rolling Baseline Window and Minimum Stable Baseline required before WE1-WE4 rules run.</li><li>Set the Near-Spec Margin and enable only the rules required by the quality process.</li><li>In Reference Identity Profiler, select the receipt field combination that identifies one physical supplier lot.</li><li>Review population, duplicate and collision statistics before saving.</li><li>Choose <b>Save New Config Version</b>. Historical attention events retain their original configuration version.</li></ol>
              <DocScreenshot src="/docs/config-attention.png" alt="Attention Engine configuration and reference profiler" caption="Attention configuration: test policy, baseline, rules and reference identity are version controlled." />
            </WikiSection>
            <WikiSection title="6. Reset data or load the demonstration dataset">
              <ol><li>Open <b>Configuration → Masters</b> and locate the data tools at the bottom of the master sidebar.</li><li>Use <b>Reset Master Data</b> when configuration must be cleared while preserving historical transactions.</li><li>Use <b>Reset Entire App</b> only when all masters, specifications, transactions, results, attention data and audit history must be permanently deleted.</li><li>Use <b>Load Demo Data</b> to replace current data with 8 ferro-alloy materials, 12 suppliers, 50,100 completed samples and 250,500 numerical results.</li><li>Read the confirmation dialog carefully. Reset Entire App and Load Demo Data both replace transaction data.</li><li>During demo generation, leave the page open until the success message appears.</li></ol>
              <DocScreenshot src="/docs/config-data-tools.svg" alt="Illustrated Configuration data tools" caption="Illustrated guide: master-only reset, full application reset and large demo-data generation have different data impacts." />
            </WikiSection>
            <WikiNote>
              Before using Reset Entire App or Load Demo Data, export or back up
              any information that must be retained. These actions cannot be
              undone from the application.
            </WikiNote>
            <WikiSection title="Specification values">
              <table>
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Required configuration</th>
                    <th>Validation</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Numeric</td>
                    <td>Minimum, mandatory Aim, Maximum and UOM</td>
                    <td>Minimum ≤ Aim ≤ Maximum</td>
                  </tr>
                  <tr>
                    <td>Category</td>
                    <td>Allowed values and required target</td>
                    <td>Result must use a configured category</td>
                  </tr>
                  <tr>
                    <td>Yes / No</td>
                    <td>Required target state</td>
                    <td>Result is evaluated against the configured state</td>
                  </tr>
                </tbody>
              </table>
            </WikiSection>
            <WikiNote>
              Use unique plant, material, supplier, attribute-group and
              attribute codes. Codes are normalized to uppercase where
              applicable.
            </WikiNote>
          </>
        )}
        {section === "logic" && (
          <>
            <WikiTitle
              title="Application Logic"
              intro="How FA-IQM chooses specifications, moves transactions and produces attention."
            />
            <WikiSection title="Receipt and specification resolution">
              <ol>
                <li>
                  The user chooses Plant → SMS → Store, material and supplier.
                </li>
                <li>
                  The backend selects the latest material specification whose
                  creation time is not later than the receipt time.
                </li>
                <li>
                  The exact specification ID and version are stored on the
                  receipt.
                </li>
                <li>
                  Later specification versions apply only to new transactions;
                  the historical receipt remains locked.
                </li>
              </ol>
            </WikiSection>
            <WikiSection title="Quality workflow">
              <div className="logicFlow">
                Draft Receipt <b>→</b> Pending Sampling <b>→</b> Sample Created{" "}
                <b>→</b> Laboratory <b>→</b> Results Submitted <b>→</b> Quality
                Review <b>→</b> Released / Rejected
              </div>
              <p>
                Mandatory laboratory results must be entered before submission.
                Numeric results are checked against minimum and maximum.
                Category and Boolean results are checked against the configured
                target. Once submitted, results are immutable: the UI becomes
                read-only and the API rejects subsequent edits.
              </p>
            </WikiSection>
            <WikiSection title="Reference consolidation and SPC/SQC">
              <ul><li><b>Composite reference:</b> users can combine Supplier Batch, Internal Batch, GRN, PO, Vehicle, Receipt, Plant, SMS and Store identifiers.</li><li><b>Blank selected fields:</b> the unique receipt number is used so unrelated blank references are never merged.</li><li><b>All:</b> retains every numerical observation within a matching reference.</li><li><b>Latest:</b> retains the newest numerical result per attribute and reference.</li><li><b>Average mean:</b> produces one mean value per attribute and reference.</li><li><b>SPC/SQC:</b> displays count, mean, population sigma, three-sigma control limits and Cpk where specification limits permit calculation.</li></ul>
            </WikiSection>
            <WikiSection title="Attention Engine">
              <ul>
                <li>
                  <b>Independent reference:</b> defaults to supplier batch,
                  falling back to internal batch and receipt number.
                </li>
                <li>
                  <b>Retests:</b> default policy is the deterministic latest
                  eligible result per reference and attribute.
                </li>
                <li>
                  <b>Numeric:</b> specification failure and near-limit checks
                  always work; WE1–WE4 require the configured minimum baseline.
                </li>
                <li>
                  <b>Category/Boolean:</b> uses target mismatch, consecutive
                  adverse and adverse-rate rules—never numeric sigma rules.
                </li>
                <li>
                  <b>Idempotency:</b> rerunning the same configuration and
                  evidence cannot duplicate an event.
                </li>
              </ul>
            </WikiSection>
            <WikiSection title="Severity">
              <table>
                <thead>
                  <tr>
                    <th>Severity</th>
                    <th>Meaning</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>CRITICAL</td>
                    <td>
                      Specification failure or a severe statistical signal
                      requiring immediate review.
                    </td>
                  </tr>
                  <tr>
                    <td>HIGH</td>
                    <td>Strong repeat or rate signal.</td>
                  </tr>
                  <tr>
                    <td>MEDIUM</td>
                    <td>Developing pattern that requires investigation.</td>
                  </tr>
                  <tr>
                    <td>WATCH</td>
                    <td>
                      Early warning, such as proximity to a specification limit.
                    </td>
                  </tr>
                </tbody>
              </table>
            </WikiSection>
          </>
        )}
        {section === "user" && (
          <>
            <WikiTitle
              title="User Guide"
              intro="Day-to-day instructions for store, laboratory and quality users."
            />
            <WikiSection title="1. Create an incoming receipt">
              <ol><li>Choose <b>New Receipt</b> from the main sidebar.</li><li>Select Plant first, then SMS, then Store. Each list is filtered by its parent selection.</li><li>Select the material and supplier.</li><li>Confirm the Receipt / Transaction Date. This determines which historical specification version is locked.</li><li>Enter Supplier Batch, Internal Batch, PO, <b>GRN No</b>, vehicle, quantity and UOM. GRN is optional but recommended when it is used as an analysis or attention reference.</li><li>Choose <b>Create Receipt</b>. If no specification existed at that time, correct the date or ask Quality to configure one.</li></ol>
              <DocScreenshot src="/docs/user-new-receipt.png" alt="New incoming material receipt form" caption="New Receipt: complete location, material, supplier, reference and quantity information." />
            </WikiSection>
            <WikiSection title="2. Find and open a receipt">
              <ol><li>Choose <b>Receipts</b> from the sidebar.</li><li>Review the specification version, current quality status and release state.</li><li>Select the receipt number or its row to open the Batch Quality Record.</li></ol>
              <DocScreenshot src="/docs/user-receipts.png" alt="Incoming receipts register" caption="Receipts register: each transaction shows its locked specification version and workflow state." />
            </WikiSection>
            <WikiSection title="3. Submit, sample and send to the laboratory">
              <ol><li>On a Draft Batch Quality Record, choose <b>Submit for Sampling</b>.</li><li>Choose <b>Create Sample</b>, then <b>Mark Sample Collected</b>.</li><li>Choose <b>Send to Laboratory</b>, then <b>Receive at Laboratory</b>.</li><li>Choose <b>Start Testing</b>. Buttons appear only when the previous workflow step is complete.</li><li>The locked specification shown below the workflow remains the validation basis for this batch.</li></ol>
              <DocScreenshot src="/docs/user-batch-record.png" alt="Batch Quality Record and workflow actions" caption="Batch Quality Record: workflow actions and the locked applicable specification are shown together." />
            </WikiSection>
            <WikiSection title="4. Enter and submit laboratory results">
              <ol><li>Choose <b>Open Laboratory Workbench</b>.</li><li>Enter each Numeric result, or select the Category/Yes-No result.</li><li>Review the immediate PASS, FAIL or PENDING evaluation.</li><li>Choose <b>Save Draft</b> to retain work without submission.</li><li>Choose <b>Submit Results</b> only after checking every value. All mandatory attributes must have a result.</li><li>After submission, the result fields are locked and cannot be edited through either the screen or API.</li></ol>
              <DocScreenshot src="/docs/user-laboratory.png" alt="Laboratory result entry workbench" caption="Laboratory Workbench: enter values against the specification locked on the receipt." />
            </WikiSection>
            <WikiSection title="5. Review, approve and dispose the batch">
              <ol><li>After result submission, choose <b>Approve Lab Results</b>.</li><li>Review failed attributes and supporting values.</li><li>Choose <b>Accept Batch</b> when mandatory results pass.</li><li>Choose <b>Accept with Deviation</b> when an authorised exception permits use; a reason is mandatory and retained with the disposition.</li><li>Choose Reject and provide a reason when the batch cannot be accepted. Failed mandatory results prevent normal acceptance.</li><li>The release state updates to RELEASED, REJECTED or remains BLOCKED.</li></ol>
              <DocScreenshot src="/docs/user-batch-record.png" alt="Batch Quality Record disposition actions" caption="Batch Quality Record: approve submitted results, then select the appropriate controlled disposition." />
            </WikiSection>
            <WikiSection title="6. Find batches and analyse numerical trends">
              <ol><li>Choose <b>Analysis</b> from the sidebar.</li><li>At header level, select one or more receipt fields that form the Reference ID. At least one field remains selected.</li><li>Choose how repeated matching references are consolidated: Consider all results, Use latest result, or Use average mean value.</li><li>Filter by supplier and material, or search by receipt, batch, GRN, PO or vehicle.</li><li>Select a batch-reference row to open numerical attribute trend charts. The selected reference is highlighted.</li><li>Right-click a batch-reference row and choose <b>Open SPC / SQC Analysis</b> for mean, sigma, LCL/UCL and Cpk.</li></ol>
              <DocScreenshot src="/docs/user-analysis.svg" alt="Illustrated Batch and Quality Analysis workspace" caption="Illustrated guide: define the reference identity at header level, search matching batches, then click or right-click a row." />
              <DocScreenshot src="/docs/user-spc.svg" alt="Illustrated SPC and SQC analysis modal" caption="Illustrated guide: SPC/SQC adds statistical center and control limits to each numerical attribute trend." />
            </WikiSection>
            <WikiSection title="7. Filter, sort and page through grids">
              <ol><li>Use the grid <b>Filter</b> box for a quick search across the visible register.</li><li>Select a business field under <b>Sort by</b>, then choose Ascending or Descending.</li><li>Choose 10, 25, 50 or 100 rows per page.</li><li>Use First, Previous, Next and Last to move through the filtered result set.</li><li>Page automatically returns to 1 whenever the filter, sort direction, page size or dataset changes.</li></ol>
              <DocScreenshot src="/docs/user-grid-controls.svg" alt="Illustrated shared grid controls" caption="Illustrated guide: the same filter, sort and pagination controls appear across operational and configuration grids." />
            </WikiSection>
            <WikiSection title="8. Use the Material Quality Register">
              <ol><li>Choose <b>Report</b> from the sidebar.</li><li>Filter by material, supplier, quality status or receipt-date range.</li><li>Use Search for receipt number, batch number or PO.</li><li>Read the <b>Exception</b> column for failed attributes, observed value, expected aim and permitted range.</li><li>Select a row to return to its Batch Quality Record.</li></ol>
              <DocScreenshot src="/docs/user-report.png" alt="Material Quality Register with filters" caption="Material Quality Register: filter receipt transactions and review off-spec exceptions." />
            </WikiSection>
            <WikiSection title="9. Use the Attention Engine">
              <ol><li>Choose <b>Attention Engine</b> and run evaluation after results are submitted or approved.</li><li>Switch between Material and Supplier perspectives.</li><li>Use Event Register to see the exact rule, severity, reference and source evidence.</li><li>Open an event for specification, baseline and rule evidence, then acknowledge it after review.</li><li>Use Reports R01-R05 for formatted operational and audit views.</li></ol>
              <DocScreenshot src="/docs/user-attention.png" alt="Attention Engine cockpit" caption="Attention Cockpit: prioritise explainable quality signals without replacing disposition decisions." />
            </WikiSection>
            <WikiSection title="Common messages">
              <table>
                <thead>
                  <tr>
                    <th>Message</th>
                    <th>What to do</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>No specification existed</td>
                    <td>
                      Create a material quality specification before creating
                      the receipt, or correct the receipt date.
                    </td>
                  </tr>
                  <tr>
                    <td>All mandatory results are required</td>
                    <td>Enter every mandatory result and submit again.</td>
                  </tr>
                  <tr>
                    <td>Quality results are locked</td>
                    <td>Submitted or approved results are immutable. Create an authorised retest sample rather than editing the completed result.</td>
                  </tr>
                  <tr>
                    <td>No attention events</td>
                    <td>
                      Confirm submitted/approved results exist, then run
                      Attention Evaluation.
                    </td>
                  </tr>
                  <tr>
                    <td>Insufficient baseline</td>
                    <td>
                      The process does not yet have enough independent
                      references for stable statistical rules; specification
                      checks still apply.
                    </td>
                  </tr>
                </tbody>
              </table>
            </WikiSection>
          </>
        )}
        {section === "api" && (
          <>
            <WikiTitle
              title="API Documentation"
              intro="The FastAPI service is available under /api/v1. Interactive OpenAPI documentation is available at /docs."
            />
            <div className="apiLinkRow">
              <a
                href="http://127.0.0.1:8000/docs"
                target="_blank"
                className="primary apiLink"
              >
                Open Swagger UI ↗
              </a>
              <a
                href="http://127.0.0.1:8000/openapi.json"
                target="_blank"
                className="apiLink"
              >
                OpenAPI JSON ↗
              </a>
            </div>
            <ApiGroup
              title="Transactions"
              rows={[
                ["GET", "/receipts", "List receipt transactions"],
                [
                  "POST",
                  "/receipts",
                  "Create and lock a receipt to its specification",
                ],
                ["GET", "/receipts/{id}", "Batch Quality Record detail"],
                ["POST", "/receipts/{id}/submit", "Submit a draft receipt"],
                ["POST", "/receipts/{id}/samples", "Create a sample"],
                ["PUT", "/samples/{id}/results", "Save laboratory results"],
                [
                  "POST",
                  "/samples/{id}/results/submit",
                  "Validate and submit results",
                ],
                [
                  "POST",
                  "/receipts/{id}/disposition",
                  "Accept, accept with deviation, hold or reject a batch",
                ],
              ]}
            />
            <ApiGroup
              title="Configuration"
              rows={[
                ["GET/POST", "/config/materials", "Material master"],
                ["GET/POST", "/config/suppliers", "Supplier master"],
                ["GET/POST", "/config/plants", "Plant master"],
                ["GET/POST", "/config/sms-locations", "Plant-to-SMS mapping"],
                ["GET/POST", "/config/store-locations", "SMS-to-store mapping"],
                ["GET/POST", "/config/attribute-groups", "Attribute groups"],
                [
                  "GET/POST",
                  "/config/quality-attributes",
                  "Quality attributes",
                ],
                [
                  "GET/POST",
                  "/config/specifications",
                  "Specification versions and history",
                ],
                ["POST", "/config/reset-masters", "Archive active masters while preserving transactions"],
                ["POST", "/config/reset-app", "Permanently delete all application data"],
                ["POST", "/config/load-demo", "Replace data with the 50,100-sample demonstration dataset"],
              ]}
            />
            <ApiGroup
              title="Analysis"
              rows={[
                ["GET", "/analysis/batches", "Search receipt references and calculate numerical trends or SPC/SQC statistics"],
                ["QUERY", "reference_fields", "Comma-separated receipt fields forming the composite reference identity"],
                ["QUERY", "consolidation=ALL|LATEST|MEAN", "Control repeated observations for the same reference"],
                ["QUERY", "supplier_id, material_id, search", "Limit results using supplier and receipt attributes"],
              ]}
            />
            <ApiGroup
              title="Attention Engine and Reports"
              rows={[
                [
                  "GET",
                  "/attention/summary?view=material|supplier",
                  "Attention Cockpit aggregation",
                ],
                ["GET", "/attention/events", "Filterable event register"],
                [
                  "GET",
                  "/attention/events/{id}",
                  "Rule evidence and source lineage",
                ],
                [
                  "POST",
                  "/attention/events/{id}/acknowledge",
                  "Acknowledge an event",
                ],
                [
                  "GET/PUT",
                  "/attention/config",
                  "Read or version engine configuration",
                ],
                [
                  "GET",
                  "/attention/reference-profiler",
                  "Reference-field quality statistics",
                ],
                ["POST", "/attention/evaluate", "Run deterministic evaluation"],
                [
                  "GET",
                  "/attention/reports/R01…R05",
                  "Structured attention reports",
                ],
                [
                  "GET",
                  "/reports/material-quality-register",
                  "Receipt-based quality register",
                ],
              ]}
            />
            <WikiNote>
              Requests and responses use JSON. Validation errors use HTTP
              400/409 with a <code>detail</code> message. Missing resources use
              HTTP 404.
            </WikiNote>
          </>
        )}
      </article>
    </div>
  );
}

function WikiTitle({ title, intro }: { title: string; intro: string }) {
  return (
    <div className="wikiHero">
      <h2>{title}</h2>
      <p>{intro}</p>
    </div>
  );
}
function WikiSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="wikiSection">
      <h2>{title}</h2>
      {children}
    </section>
  );
}
function WikiCard({ title, text }: { title: string; text: string }) {
  return (
    <div className="wikiCard">
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}
function WikiNote({ children }: { children: React.ReactNode }) {
  return (
    <div className="wikiNote">
      <b>Note</b>
      {children}
    </div>
  );
}
function DocScreenshot({ src, alt, caption }: { src: string; alt: string; caption: string }) {
  return <figure className="docScreenshot"><img src={src} alt={alt} /><figcaption>{caption}</figcaption></figure>;
}
function WikiSteps({ items }: { items: string[][] }) {
  return (
    <div className="wikiSteps">
      {items.map(([n, title, text]) => (
        <div className="wikiStep" key={n}>
          <span>{n}</span>
          <div>
            <h3>{title}</h3>
            <p>{text}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
function ApiGroup({ title, rows }: { title: string; rows: string[][] }) {
  return (
    <WikiSection title={title}>
      <DataGrid rows={rows} searchText={(row) => row.join(" ")} sortOptions={[["Endpoint", (row) => row[1]], ["Method", (row) => row[0]], ["Purpose", (row) => row[2]]]}>
      {(gridRows) =>
      <div className="tablewrap">
        <table>
          <thead>
            <tr>
              <th>Method</th>
              <th>Endpoint</th>
              <th>Purpose</th>
            </tr>
          </thead>
          <tbody>
            {gridRows.map(([method, path, purpose]) => (
              <tr key={method + path}>
                <td>
                  <Badge>{method}</Badge>
                </td>
                <td>
                  <code>{path}</code>
                </td>
                <td>{purpose}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      }
      </DataGrid>
    </WikiSection>
  );
}

const ANALYSIS_REFERENCE_OPTIONS = [
  ["supplier_batch_no", "Supplier Batch"],
  ["internal_batch_no", "Internal Batch"],
  ["grn_no", "GRN No"],
  ["po_no", "PO No"],
  ["vehicle_no", "Vehicle No"],
  ["receipt_no", "Receipt No"],
  ["plant_code", "Plant"],
  ["sms_code", "SMS"],
  ["store_code", "Store"],
];

function AnalysisTrendChart({ series, selectedReference, spc }: any) {
  const width = 720,
    height = 210,
    pad = 34;
  const points = series.points || [];
  const extra = spc
    ? [series.stats?.lcl, series.stats?.ucl]
    : points.flatMap((point: any) => [point.lsl, point.usl, point.aim]);
  const values = [
    ...points.map((point: any) => Number(point.value)),
    ...extra.filter((value: any) => value != null).map(Number),
  ].filter(Number.isFinite);
  if (!values.length)
    return <div className="analysisNoData">No numerical results available.</div>;
  let low = Math.min(...values),
    high = Math.max(...values);
  if (low === high) {
    low -= Math.abs(low || 1) * 0.1;
    high += Math.abs(high || 1) * 0.1;
  }
  const margin = (high - low) * 0.12;
  low -= margin;
  high += margin;
  const x = (index: number) =>
    pad + (points.length < 2 ? (width - pad * 2) / 2 : (index * (width - pad * 2)) / (points.length - 1));
  const y = (value: number) => pad + ((high - value) * (height - pad * 2)) / (high - low);
  const line = points.map((point: any, index: number) => `${x(index)},${y(Number(point.value))}`).join(" ");
  const guides = spc
    ? [
        [series.stats?.ucl, "UCL", "#d9485f"],
        [series.stats?.mean, "Mean", "#213a8f"],
        [series.stats?.lcl, "LCL", "#d9485f"],
      ]
    : [
        [points[points.length - 1]?.usl, "USL", "#d9485f"],
        [points[points.length - 1]?.aim, "Aim", "#213a8f"],
        [points[points.length - 1]?.lsl, "LSL", "#d9485f"],
      ];
  return (
    <svg className="trendChart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${series.name} trend`}>
      {[0, 0.25, 0.5, 0.75, 1].map((ratio) => (
        <line key={ratio} x1={pad} x2={width - pad} y1={pad + ratio * (height - pad * 2)} y2={pad + ratio * (height - pad * 2)} className="chartGrid" />
      ))}
      {guides.map(([value, label, color]: any) =>
        value == null ? null : (
          <g key={label}>
            <line x1={pad} x2={width - pad} y1={y(Number(value))} y2={y(Number(value))} stroke={color} strokeDasharray="6 5" />
            <text x={width - pad + 4} y={y(Number(value)) + 3} fill={color}>{label}</text>
          </g>
        ),
      )}
      {points.length > 1 && <polyline points={line} className="trendLine" />}
      {points.map((point: any, index: number) => (
        <g key={`${point.reference_id}-${point.receipt_id}-${index}`}>
          <circle cx={x(index)} cy={y(Number(point.value))} r={point.reference_id === selectedReference ? 6 : 4} className={point.reference_id === selectedReference ? "trendPoint selected" : "trendPoint"} />
          <title>{[
            `Supplier: ${point.supplier_code || "—"} · ${point.supplier_name || "—"}`,
            `Material: ${point.material_code || "—"} · ${point.material_name || "—"}`,
            `Reference: ${point.reference_id} · Receipt: ${point.receipt_no}`,
            `Attribute: ${series.code} · ${series.name}`,
            `Specification: ${point.lsl ?? "—"} / Aim ${point.aim ?? "—"} / ${point.usl ?? "—"} ${series.uom || ""}`,
            `Actual: ${point.value} ${series.uom || ""} · ${point.status || "PENDING"}`,
          ].join("\n")}</title>
        </g>
      ))}
      <text x={pad} y={height - 7} className="chartAxisText">{points[0]?.reference_id || ""}</text>
      <text x={width - pad} y={height - 7} textAnchor="end" className="chartAxisText">{points[points.length - 1]?.reference_id || ""}</text>
    </svg>
  );
}

const WESTERN_ELECTRIC_RULES = [
  ["WE1", "One point beyond 3σ", "A single result is more than three standard deviations from the centre line."],
  ["WE2", "Two of three beyond 2σ", "Two of three consecutive results are beyond two standard deviations on the same side."],
  ["WE3", "Four of five beyond 1σ", "Four of five consecutive results are beyond one standard deviation on the same side."],
  ["WE4", "Eight on one side", "Eight consecutive results are all above or all below the centre line."],
];

function westernElectricViolations(series: any) {
  const points = series.points || [], meanValue = series.stats?.mean, sigma = series.stats?.sigma;
  if (meanValue == null || !sigma || points.length < 2) return [];
  const z = points.map((point: any) => (Number(point.value) - meanValue) / sigma);
  const violations: any[] = [];
  const add = (rule: string, index: number, start: number) => violations.push({
    rule, index, reference_id: points[index].reference_id, value: points[index].value,
    z_score: z[index], window: points.slice(start, index + 1).map((point: any) => point.reference_id).join(" → "),
  });
  z.forEach((score: number, index: number) => {
    if (Math.abs(score) > 3) add("WE1", index, index);
    if (index >= 2) {
      const window = z.slice(index - 2, index + 1);
      if (window.filter((value: number) => value > 2).length >= 2 || window.filter((value: number) => value < -2).length >= 2) add("WE2", index, index - 2);
    }
    if (index >= 4) {
      const window = z.slice(index - 4, index + 1);
      if (window.filter((value: number) => value > 1).length >= 4 || window.filter((value: number) => value < -1).length >= 4) add("WE3", index, index - 4);
    }
    if (index >= 7) {
      const window = z.slice(index - 7, index + 1);
      if (window.every((value: number) => value > 0) || window.every((value: number) => value < 0)) add("WE4", index, index - 7);
    }
  });
  return violations;
}

function WesternElectricPanel({ series }: any) {
  const rows = series.flatMap((item: any) => westernElectricViolations(item).map((violation: any) => ({ ...violation, code: item.code, name: item.name, uom: item.uom })));
  return <>
    <div className="weRuleCards">{WESTERN_ELECTRIC_RULES.map(([code, title, description]) => {
      const count = rows.filter((row: any) => row.rule === code).length;
      return <section className={count ? "weRuleCard alert" : "weRuleCard"} key={code}><Badge>{code}</Badge><strong>{title}</strong><span>{description}</span><b>{count} violation{count === 1 ? "" : "s"}</b></section>;
    })}</div>
    <section className="analysisChartCard">
      <div className="panelTitle"><div><h3>Detected Rule Violations</h3><p className="muted">Rules are evaluated chronologically for each numerical attribute using the displayed population mean and sigma.</p></div><Badge>{rows.length} SIGNALS</Badge></div>
      <div className="tablewrap"><table><thead><tr><th>Rule</th><th>Attribute</th><th>Reference</th><th>Value</th><th>Z-score</th><th>Evaluation Window</th></tr></thead><tbody>{rows.map((row: any, index: number) => <tr key={`${row.code}-${row.rule}-${row.index}-${index}`}><td><Badge>{row.rule}</Badge></td><td><b>{row.code}</b><br/><small>{row.name}</small></td><td>{row.reference_id}</td><td>{Number(row.value).toFixed(3)} {row.uom}</td><td>{row.z_score.toFixed(2)}σ</td><td><small>{row.window}</small></td></tr>)}</tbody></table>{!rows.length && <div className="empty">No Western Electric rule violations were detected in the selected population.</div>}</div>
    </section>
  </>;
}

function AnalysisPage({ materials, suppliers, notify }: any) {
  const [referenceFields, setReferenceFields] = useState(["supplier_batch_no"]),
    [consolidation, setConsolidation] = useState("ALL"),
    [filters, setFilters] = useState({ supplier_id: "", material_id: "", search: "" }),
    [data, setData] = useState<any>({ batches: [], series: [] }),
    [loading, setLoading] = useState(false),
    [selectedBatch, setSelectedBatch] = useState<any>(null),
    [detailSeries, setDetailSeries] = useState<any[]>([]),
    [detailLoading, setDetailLoading] = useState(false),
    [analysisMode, setAnalysisMode] = useState("TREND"),
    [spcTab, setSpcTab] = useState("CHARTS"),
    [contextMenu, setContextMenu] = useState<any>(null);
  const loadAnalysis = async () => {
    setLoading(true);
    const params = new URLSearchParams({
      reference_fields: referenceFields.join(","),
      consolidation,
      include_series: "false",
    });
    if (filters.supplier_id) params.set("supplier_id", filters.supplier_id);
    if (filters.material_id) params.set("material_id", filters.material_id);
    if (filters.search.trim()) params.set("search", filters.search.trim());
    try {
      const response = await fetch(API + `/analysis/batches?${params}`);
      const body = await response.json();
      if (!response.ok) {
        notify(body.detail || "Unable to load batch analysis");
        return;
      }
      setData(body);
    } catch {
      notify("Unable to load batch analysis. Check that the backend service is running.");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    loadAnalysis();
  }, [referenceFields.join("|"), consolidation]);
  const openAnalysis = async (batch: any, mode: string) => {
    setSelectedBatch(batch);
    setAnalysisMode(mode);
    setSpcTab("CHARTS");
    setContextMenu(null);
    setDetailSeries([]);
    setDetailLoading(true);
    const params = new URLSearchParams({
      reference_fields: referenceFields.join(","), consolidation,
      selected_reference: batch.reference_id, include_series: "true",
    });
    if (filters.supplier_id) params.set("supplier_id", filters.supplier_id);
    if (filters.material_id) params.set("material_id", filters.material_id);
    if (filters.search.trim()) params.set("search", filters.search.trim());
    try {
      const response = await fetch(API + `/analysis/batches?${params}`);
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Unable to load analysis detail");
      setDetailSeries(body.series || []);
    } catch (error) {
      notify(error instanceof Error ? error.message : "Unable to load analysis detail");
    } finally {
      setDetailLoading(false);
    }
  };
  return (
    <>
      <section className="panel analysisHeader">
        <div className="panelTitle">
          <div>
            <h2>Reference Identity & Consolidation</h2>
            <p className="muted">Choose the receipt fields that identify a supplier batch before searching.</p>
          </div>
          <Badge>{data.batches.length} REFERENCES</Badge>
        </div>
        <div className="analysisReferenceBar">
          <div className="referenceChecks">
            {ANALYSIS_REFERENCE_OPTIONS.map(([field, label]) => (
              <label className="check" key={field}>
                <input
                  type="checkbox"
                  checked={referenceFields.includes(field)}
                  onChange={(event) =>
                    setReferenceFields(
                      event.target.checked
                        ? [...referenceFields, field]
                        : referenceFields.length === 1
                          ? referenceFields
                          : referenceFields.filter((item) => item !== field),
                    )
                  }
                />
                {label}
              </label>
            ))}
          </div>
          <label className="analysisPolicy">
            Multiple batches for the same reference
            <select value={consolidation} onChange={(event) => setConsolidation(event.target.value)}>
              <option value="ALL">Consider all results</option>
              <option value="LATEST">Use latest result</option>
              <option value="MEAN">Use average mean value</option>
            </select>
          </label>
        </div>
      </section>
      <section className="panel">
        <div className="panelTitle">
          <div>
            <h2>Find a Batch</h2>
            <p className="muted">Search using supplier and receipt attributes. Click for trends; right-click for SPC/SQC.</p>
          </div>
          <button type="button" onClick={() => setFilters({ supplier_id: "", material_id: "", search: "" })}>Clear</button>
        </div>
        <div className="analysisFilters">
          <label>Supplier<select value={filters.supplier_id} onChange={(event) => setFilters({ ...filters, supplier_id: event.target.value })}><option value="">All suppliers</option>{suppliers.map((supplier: any) => <option key={supplier.id} value={supplier.id}>{supplier.supplier_code} · {supplier.supplier_name}</option>)}</select></label>
          <label>Material<select value={filters.material_id} onChange={(event) => setFilters({ ...filters, material_id: event.target.value })}><option value="">All materials</option>{materials.map((material: any) => <option key={material.id} value={material.id}>{material.material_code} · {material.material_name}</option>)}</select></label>
          <label>Receipt Attributes<input value={filters.search} placeholder="Batch, receipt, GRN, PO or vehicle" onChange={(event) => setFilters({ ...filters, search: event.target.value })} onKeyDown={(event) => event.key === "Enter" && loadAnalysis()} /></label>
          <button className="primary" type="button" onClick={loadAnalysis}>{loading ? "Searching…" : "Search Batches"}</button>
        </div>
      </section>
      <section className="panel">
        <div className="panelTitle"><div><h2>Matching Batch References</h2><p className="muted">Grouped by {referenceFields.map((field) => ANALYSIS_REFERENCE_OPTIONS.find((item) => item[0] === field)?.[1]).join(" + ")} · {consolidation}</p></div></div>
        {data.truncated && <div className="groupNotice">Showing references from the latest {data.loaded_receipts.toLocaleString()} of {data.total_receipts.toLocaleString()} matching receipts. Use supplier, material, or receipt-attribute filters to narrow the analysis.</div>}
        <DataGrid rows={data.batches} searchText={(batch) => `${batch.reference_id} ${batch.latest_receipt_no} ${batch.supplier_code} ${batch.supplier_name} ${batch.material_code} ${batch.material_name} ${batch.status}`} sortOptions={[["Receipt date", (batch) => batch.receipt_datetime], ["Reference ID", (batch) => batch.reference_id], ["Supplier", (batch) => batch.supplier_name], ["Material", (batch) => batch.material_name], ["Receipt matches", (batch) => batch.receipt_count]]} initialPageSize={25}>
        {(gridRows) =>
        <div className="tablewrap">
          <table className="analysisTable">
            <thead><tr><th>Reference ID</th><th>Latest Receipt</th><th>Supplier</th><th>Material</th><th>Receipt Matches</th><th>Numeric Attributes</th><th>Status</th></tr></thead>
            <tbody>{gridRows.map((batch: any) => (
              <tr key={batch.reference_id} onClick={() => openAnalysis(batch, "TREND")} onContextMenu={(event) => { event.preventDefault(); setContextMenu({ x: event.clientX, y: event.clientY, batch }); }}>
                <td className="link">{batch.reference_id}</td><td>{batch.latest_receipt_no}<br/><small>{new Date(batch.receipt_datetime).toLocaleString()}</small></td><td><b>{batch.supplier_code}</b><br/><small>{batch.supplier_name}</small></td><td><b>{batch.material_code}</b><br/><small>{batch.material_name}</small></td><td>{batch.receipt_count}</td><td>{batch.numeric_attributes}</td><td><Badge>{batch.status}</Badge></td>
              </tr>
            ))}</tbody>
          </table>
          {!gridRows.length && <div className="empty">{loading ? "Loading batch references…" : "No batches match the selected grid filter."}</div>}
        </div>
        }
        </DataGrid>
      </section>
      {contextMenu && <div className="analysisContextMenu" style={{ left: contextMenu.x, top: contextMenu.y }}><button type="button" onClick={() => openAnalysis(contextMenu.batch, "SPC")}>Open SPC / SQC Analysis</button><button type="button" onClick={() => setContextMenu(null)}>Cancel</button></div>}
      {selectedBatch && (
        <div className="modalBackdrop" onClick={() => setSelectedBatch(null)}>
          <div className="analysisModal" onClick={(event) => event.stopPropagation()}>
            <div className="panelTitle"><div><span className="eyebrow">{analysisMode === "SPC" ? "SPC / SQC ANALYSIS" : "NUMERICAL ATTRIBUTE TRENDS"}</span><h2>{selectedBatch.reference_id}</h2><p className="muted">{selectedBatch.supplier_name} · {selectedBatch.material_name} · {consolidation}</p></div><button type="button" onClick={() => setSelectedBatch(null)}>×</button></div>
            {detailLoading && <div className="empty">Loading numerical analysis…</div>}
            {!detailLoading && !detailSeries.length && <div className="empty">No numerical test results are available for the matching batches.</div>}
            {analysisMode === "SPC" && !detailLoading && !!detailSeries.length && <div className="configTabs analysisTabs"><button className={spcTab === "CHARTS" ? "active" : ""} onClick={() => setSpcTab("CHARTS")}>SPC / SQC Charts</button><button className={spcTab === "WESTERN_ELECTRIC" ? "active" : ""} onClick={() => setSpcTab("WESTERN_ELECTRIC")}>Western Electric Rules</button></div>}
            {analysisMode === "SPC" && spcTab === "WESTERN_ELECTRIC" && !detailLoading ? <WesternElectricPanel series={detailSeries} /> : <div className="analysisCharts">{detailSeries.map((series: any) => (
              <section className="analysisChartCard" key={series.attribute_id}>
                <div className="analysisChartTitle"><div><h3>{series.code} · {series.name}</h3><small>{series.stats.count} consolidated observation{series.stats.count === 1 ? "" : "s"} · {series.uom || "No UOM"}</small></div>{analysisMode === "SPC" && <div className="spcStats"><span>Mean<b>{series.stats.mean?.toFixed(3) ?? "—"}</b></span><span>Sigma<b>{series.stats.sigma?.toFixed(3) ?? "—"}</b></span><span>LCL / UCL<b>{series.stats.lcl?.toFixed(3) ?? "—"} / {series.stats.ucl?.toFixed(3) ?? "—"}</b></span><span>Cpk<b>{series.stats.cpk?.toFixed(2) ?? "—"}</b></span></div>}</div>
                <AnalysisTrendChart series={series} selectedReference={selectedBatch.reference_id} spc={analysisMode === "SPC"} />
              </section>
            ))}</div>}
          </div>
        </div>
      )}
    </>
  );
}

function MaterialQualityReport({ openReceipt, materials, suppliers }: any) {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    material: "",
    supplier: "",
    status: "",
    from: "",
    to: "",
    search: "",
  });
  useEffect(() => {
    const params = new URLSearchParams({ limit: "1000" });
    if (filters.material) params.set("material_id", filters.material);
    if (filters.supplier) params.set("supplier_id", filters.supplier);
    if (filters.status) params.set("status", filters.status);
    if (filters.from) params.set("date_from", filters.from);
    if (filters.to) params.set("date_to", filters.to);
    if (filters.search.trim()) params.set("search", filters.search.trim());
    setLoading(true);
    fetch(API + `/reports/material-quality-register?${params}`)
      .then((r) => r.json())
      .then(setRows)
      .finally(() => setLoading(false));
  }, [filters.material, filters.supplier, filters.status, filters.from, filters.to, filters.search]);
  return (
    <>
      <section className="panel reportFilters">
        <div className="panelTitle">
          <div>
            <h2>Report Filters</h2>
            <p className="muted">
              Filter receipt transactions without changing the underlying
              register.
            </p>
          </div>
          <button
            onClick={() =>
              setFilters({
                material: "",
                supplier: "",
                status: "",
                from: "",
                to: "",
                search: "",
              })
            }
          >
            Clear Filters
          </button>
        </div>
        <div className="reportFilterGrid">
          <label>
            Material
            <select
              value={filters.material}
              onChange={(e) =>
                setFilters({ ...filters, material: e.target.value })
              }
            >
              <option value="">All materials</option>
              {materials.map((x: any) => (
                <option key={x.id} value={x.id}>
                  {x.material_code} · {x.material_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Supplier
            <select
              value={filters.supplier}
              onChange={(e) =>
                setFilters({ ...filters, supplier: e.target.value })
              }
            >
              <option value="">All suppliers</option>
              {suppliers.map((x: any) => (
                <option key={x.id} value={x.id}>
                  {x.supplier_code} · {x.supplier_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Quality Status
            <select
              value={filters.status}
              onChange={(e) =>
                setFilters({ ...filters, status: e.target.value })
              }
            >
              <option value="">All statuses</option>
              {["DRAFT","PENDING_SAMPLING","SAMPLING_IN_PROGRESS","SAMPLE_SENT_TO_LAB","LAB_IN_PROGRESS","RESULTS_AVAILABLE","UNDER_REVIEW","ACCEPTED","ACCEPTED_WITH_DEVIATION","REJECTED","ON_HOLD"].map((x) => <option key={x} value={x}>{x}</option>)}
            </select>
          </label>
          <label>
            From Date
            <input
              type="date"
              value={filters.from}
              onChange={(e) => setFilters({ ...filters, from: e.target.value })}
            />
          </label>
          <label>
            To Date
            <input
              type="date"
              min={filters.from}
              value={filters.to}
              onChange={(e) => setFilters({ ...filters, to: e.target.value })}
            />
          </label>
          <label>
            Search
            <input
              placeholder="Receipt, batch or PO"
              value={filters.search}
              onChange={(e) =>
                setFilters({ ...filters, search: e.target.value })
              }
            />
          </label>
        </div>
      </section>
      <section className="panel">
        <div className="panelTitle">
          <div>
            <h2>Material Quality Register</h2>
            <p className="muted">
              {loading ? "Loading filtered transactions…" : `${rows.length} matching receipt transactions${rows.length === 1000 ? " (first 1,000)" : ""}`}
            </p>
          </div>
        </div>
        <DataGrid rows={rows} searchText={(row) => `${row.receipt_no} ${row.material_code} ${row.material_name} ${row.supplier_code} ${row.supplier_name} ${row.supplier_batch_no} ${row.internal_batch_no} ${row.po_no} ${row.grn_no || ""} ${row.inspection_status} ${row.release_state}`} sortOptions={[["Receipt date", (row) => row.receipt_datetime], ["Material", (row) => row.material_name], ["Supplier", (row) => row.supplier_name], ["Quantity", (row) => Number(row.quantity)], ["Quality status", (row) => row.inspection_status]]} initialPageSize={25}>
        {(gridRows) =>
        <div className="tablewrap">
          <table>
            <thead>
              <tr>
                <th>Receipt / Date</th>
                <th>Material</th>
                <th>Supplier</th>
                <th>Supplier Batch</th>
                <th>Internal Batch / PO / GRN</th>
                <th>Location</th>
                <th>Specification</th>
                <th>Quantity</th>
                <th>Exception</th>
                <th>Quality Status</th>
                <th>Release</th>
              </tr>
            </thead>
            <tbody>
              {gridRows.map((row) => (
                <tr key={row.id} onClick={() => openReceipt(row.id)}>
                  <td className="link">
                    {row.receipt_no}
                    <br />
                    <small>
                      {new Date(row.receipt_datetime).toLocaleString()}
                    </small>
                  </td>
                  <td>
                    <b>{row.material_code}</b>
                    <br />
                    <small>{row.material_name}</small>
                  </td>
                  <td>
                    <b>{row.supplier_code}</b>
                    <br />
                    <small>{row.supplier_name}</small>
                  </td>
                  <td>{row.supplier_batch_no}</td>
                  <td>
                    {row.internal_batch_no}
                    <br />
                    <small>PO {row.po_no}</small>
                    <br />
                    <small>GRN {row.grn_no || "—"}</small>
                  </td>
                  <td>
                    {row.plant}
                    <br />
                    <small>
                      {row.sms} · {row.store}
                    </small>
                  </td>
                  <td>
                    <Badge>{row.specification_version}</Badge>
                  </td>
                  <td>
                    {row.quantity} {row.uom}
                  </td>
                  <td className="exceptionCell">
                    {row.exceptions.length ? (
                      row.exceptions.map((item: any) => (
                        <div
                          className="exceptionItem"
                          key={`${item.sample_no}-${item.attribute_code}`}
                        >
                          <b>{item.attribute_code}</b> · {item.attribute_name}
                          <span>
                            Value:{" "}
                            <strong>
                              {item.observed_value} {item.uom || ""}
                            </strong>
                          </span>
                          <span>
                            Aim: {item.aim_value ?? "—"} {item.uom || ""}
                          </span>
                          <span>
                            Range: {item.lsl ?? "—"} to {item.usl ?? "—"}{" "}
                            {item.uom || ""}
                          </span>
                        </div>
                      ))
                    ) : (
                      <span className="noException">No exception</span>
                    )}
                  </td>
                  <td>
                    <Badge>{row.inspection_status}</Badge>
                  </td>
                  <td>
                    <Badge>{row.release_state}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!gridRows.length && (
            <div className="empty">
              No receipt transactions match the selected filters.
            </div>
          )}
        </div>
        }
        </DataGrid>
      </section>
    </>
  );
}

function FormattedAttentionReport({ data }: any) {
  const titles: AnyObj = {
    R01: "Executive Attention Summary",
    R02: "Supplier Attention Report",
    R03: "Ferro Alloy Attention Report",
    R04: "Attribute Trend & Rule Evidence",
    R05: "Batch/Test Consolidation Audit",
  };
  const rows = data.rows || [];
  return (
    <div className="formattedReport">
      <div className="reportHeader">
        <div>
          <span className="eyebrow">
            FAIQMS ATTENTION ENGINE · {data.report_code}
          </span>
          <h2>{titles[data.report_code]}</h2>
          <p>Generated {new Date(data.generated_at).toLocaleString()}</p>
        </div>
        <div className="reportMeta">
          <span>
            Config Version<b>{data.config.version}</b>
          </span>
          <span>
            Test Policy<b>{data.config.test_selection_mode}</b>
          </span>
          <span>
            Reference Key<b>{data.config.reference_fields.join(" + ")}</b>
          </span>
        </div>
      </div>
      <DataGrid rows={rows} searchText={(row) => `${row.material_code || ""} ${row.material_name || ""} ${row.supplier_code || ""} ${row.supplier_name || ""} ${row.attribute_code || ""} ${row.attribute_name || ""} ${row.reference_id || ""} ${row.rule_code || ""} ${row.severity || ""} ${row.status || ""}`} sortOptions={[["Event time", (row) => row.event_time || ""], ["Severity", (row) => row.severity || ""], ["Material", (row) => row.material_name || ""], ["Supplier", (row) => row.supplier_name || ""], ["Attribute", (row) => row.attribute_name || ""]]} initialPageSize={25}>
      {(gridRows) =>
      <div className="tablewrap">
        <table>
          <thead>
            <tr>
              {data.report_code === "R01" && (
                <>
                  <th>Severity</th>
                  <th>Material</th>
                  <th>Supplier</th>
                  <th>Attribute</th>
                  <th>Rule / Reason</th>
                  <th>Status</th>
                </>
              )}
              {data.report_code === "R02" && (
                <>
                  <th>Supplier</th>
                  <th>Material</th>
                  <th>Attribute</th>
                  <th>Severity</th>
                  <th>Reference</th>
                  <th>Rule / Reason</th>
                </>
              )}
              {data.report_code === "R03" && (
                <>
                  <th>Material</th>
                  <th>Attribute</th>
                  <th>Supplier</th>
                  <th>Severity</th>
                  <th>Current Value</th>
                  <th>Specification</th>
                  <th>Rule</th>
                </>
              )}
              {data.report_code === "R04" && (
                <>
                  <th>Time</th>
                  <th>Supplier / Material / Attribute</th>
                  <th>Reference</th>
                  <th>Result</th>
                  <th>Specification</th>
                  <th>Baseline</th>
                  <th>Rule Evidence</th>
                </>
              )}
              {data.report_code === "R05" && (
                <>
                  <th>Reference</th>
                  <th>Receipt</th>
                  <th>Sample</th>
                  <th>Test Result</th>
                  <th>Policy</th>
                  <th>Decision / Evidence</th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {gridRows.map((row: any) => (
              <tr key={row.id}>
                {data.report_code === "R01" && (
                  <>
                    <td>
                      <Badge>{row.severity}</Badge>
                    </td>
                    <td>
                      {row.material_code} · {row.material_name}
                    </td>
                    <td>
                      {row.supplier_code} · {row.supplier_name}
                    </td>
                    <td>
                      {row.attribute_code} · {row.attribute_name}
                    </td>
                    <td>
                      <b>{row.rule_code}</b>
                      <br />
                      <small>{row.message}</small>
                    </td>
                    <td>{row.status}</td>
                  </>
                )}
                {data.report_code === "R02" && (
                  <>
                    <td>
                      <b>{row.supplier_code}</b>
                      <br />
                      <small>{row.supplier_name}</small>
                    </td>
                    <td>
                      {row.material_code} · {row.material_name}
                    </td>
                    <td>
                      {row.attribute_code} · {row.attribute_name}
                    </td>
                    <td>
                      <Badge>{row.severity}</Badge>
                    </td>
                    <td>{row.reference_id}</td>
                    <td>
                      <b>{row.rule_code}</b>
                      <br />
                      <small>{row.message}</small>
                    </td>
                  </>
                )}
                {data.report_code === "R03" && (
                  <>
                    <td>
                      <b>{row.material_code}</b>
                      <br />
                      <small>{row.material_name}</small>
                    </td>
                    <td>
                      {row.attribute_code} · {row.attribute_name}
                    </td>
                    <td>{row.supplier_name}</td>
                    <td>
                      <Badge>{row.severity}</Badge>
                    </td>
                    <td>{row.observed_value}</td>
                    <td>
                      {row.lsl ?? "—"} to {row.usl ?? row.target_value ?? "—"}
                    </td>
                    <td>{row.rule_code}</td>
                  </>
                )}
                {data.report_code === "R04" && (
                  <>
                    <td>{new Date(row.event_time).toLocaleString()}</td>
                    <td>
                      {row.supplier_name}
                      <br />
                      {row.material_name}
                      <br />
                      <b>{row.attribute_name}</b>
                    </td>
                    <td>{row.reference_id}</td>
                    <td>{row.observed_value}</td>
                    <td>
                      {row.lsl ?? "—"} / {row.usl ?? row.target_value ?? "—"}
                    </td>
                    <td>
                      N={row.baseline_n ?? 0}
                      <br />
                      {row.baseline_mean ?? "Insufficient data"}
                      {row.baseline_sigma != null
                        ? ` ± ${row.baseline_sigma}`
                        : ""}
                    </td>
                    <td>
                      <b>{row.rule_code}</b>
                      <br />
                      <small>{row.message}</small>
                    </td>
                  </>
                )}
                {data.report_code === "R05" && (
                  <>
                    <td>{row.reference_id}</td>
                    <td>{row.receipt_id}</td>
                    <td>{row.sample_id}</td>
                    <td>{row.test_result_id}</td>
                    <td>{row.evidence.test_selection_mode}</td>
                    <td>
                      USED
                      <br />
                      <small>
                        {row.evidence.source_result_ids?.join(", ")}
                      </small>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        {!gridRows.length && (
          <div className="empty">
            No attention events are available for this report.
          </div>
        )}
      </div>
      }
      </DataGrid>
      <div className="reportFooter">
        System-generated attention; disposition remains governed by the quality
        process.
      </div>
    </div>
  );
}

function AttentionPage({ notify }: any) {
  const [view, setView] = useState("material");
  const [area, setArea] = useState("cockpit");
  const [summary, setSummary] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [config, setConfig] = useState<any>(null);
  const [profiler, setProfiler] = useState<any[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<any>(null);
  const [reportData, setReportData] = useState<any>(null);
  const [evaluating, setEvaluating] = useState(false);
  const get = async (path: string) => (await fetch(API + path)).json();
  const load = async () => {
    setSummary(await get(`/attention/summary?view=${view}`));
    setEvents(await get("/attention/events"));
    setConfig(await get("/attention/config"));
    setProfiler(await get("/attention/reference-profiler"));
  };
  useEffect(() => {
    load();
  }, [view]);
  const evaluate = async () => {
    setEvaluating(true);
    notify("Attention rule evaluation is running. The large demo dataset may take several seconds.");
    try {
      const r = await fetch(API + "/attention/evaluate", { method: "POST" });
      const d = await r.json();
      notify(r.ok ? `Attention evaluation complete: ${d.observations_used.toLocaleString()} observations, ${d.events_created.toLocaleString()} new events.` : d.detail || "Evaluation failed");
      if (r.ok) await load();
    } catch {
      notify("Attention evaluation could not reach the backend service.");
    } finally {
      setEvaluating(false);
    }
  };
  const saveConfig = async () => {
    const r = await fetch(API + "/attention/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...config,
        reason: "Configuration updated in UI",
      }),
    });
    notify(
      r.ok
        ? "Attention configuration version saved."
        : "Unable to save configuration",
    );
    if (r.ok) load();
  };
  const acknowledge = async (id: string) => {
    await fetch(API + `/attention/events/${id}/acknowledge`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ acknowledged_by: "Quality User" }),
    });
    setSelectedEvent(null);
    load();
  };
  const openReport = async (code: string) => {
    setReportData(await get(`/attention/reports/${code}`));
  };
  return (
    <>
      <div className="configTabs attentionTabs">
        {[
          ["cockpit", "Cockpit"],
          ["events", "Event Register"],
          ["reports", "Reports R01-R05"],
          ["config", "Configuration"],
        ].map(([key, label]) => (
          <button
            className={area === key ? "active" : ""}
            onClick={() => setArea(key)}
            key={key}
          >
            {label}
          </button>
        ))}
      </div>
      {area === "cockpit" && (
        <>
          <section className="hero attentionHero">
            <div>
              <span className="eyebrow">EXPLAINABLE QUALITY ATTENTION</span>
              <h2>What needs attention now?</h2>
              <p>
                Advisory signals supplement - and never replace - specification
                evaluation and disposition.
              </p>
            </div>
            <button className="primary" onClick={evaluate} disabled={evaluating}>
              {evaluating ? "Evaluating Rules…" : "Run Evaluation"}
            </button>
          </section>
          <div className="perspectiveSwitch">
            <button
              className={view === "material" ? "active" : ""}
              onClick={() => setView("material")}
            >
              Material perspective
            </button>
            <button
              className={view === "supplier" ? "active" : ""}
              onClick={() => setView("supplier")}
            >
              Supplier perspective
            </button>
          </div>
          <section className="cards attentionCards">
            {["CRITICAL", "HIGH", "MEDIUM", "WATCH"].map((level) => (
              <div
                className={`card severityCard ${level.toLowerCase()}`}
                key={level}
              >
                <small>{level}</small>
                <strong>
                  {
                    events.filter(
                      (e) => e.severity === level && e.status === "OPEN",
                    ).length
                  }
                </strong>
              </div>
            ))}
          </section>
          <section className="panel">
            <h2>
              {view === "material"
                ? "FA → Attribute → Supplier"
                : "Supplier → FA → Attribute"}
            </h2>
            <DataGrid rows={summary} searchText={(row) => `${row.code} ${row.name} ${row.severity} ${row.reason}`} sortOptions={[[view === "material" ? "Material" : "Supplier", (row) => row.name], ["Severity", (row) => row.severity], ["Open events", (row) => row.open_events], ["Latest event", (row) => row.latest_event]]}>
            {(gridRows) =>
            <div className="tablewrap">
              <table>
                <thead>
                  <tr>
                    <th>{view === "material" ? "Material" : "Supplier"}</th>
                    <th>Severity</th>
                    <th>Open Events</th>
                    <th>Attributes</th>
                    <th>{view === "material" ? "Suppliers" : "Materials"}</th>
                    <th>Latest Reason</th>
                    <th>Since</th>
                  </tr>
                </thead>
                <tbody>
                  {gridRows.map((row) => (
                    <tr key={row.id}>
                      <td>
                        <b>{row.code}</b>
                        <br />
                        <small>{row.name}</small>
                      </td>
                      <td>
                        <Badge>{row.severity}</Badge>
                      </td>
                      <td>{row.open_events}</td>
                      <td>{row.attributes}</td>
                      <td>{row.counterparties}</td>
                      <td>{row.reason}</td>
                      <td>{new Date(row.latest_event).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!gridRows.length && (
                <div className="empty">
                  No attention events. Run the engine after approved or
                  submitted laboratory results are available.
                </div>
              )}
            </div>
            }
            </DataGrid>
          </section>
        </>
      )}
      {area === "events" && (
        <section className="panel">
          <h2>Attention Event Register</h2>
          <p className="muted">
            Every signal retains its rule, source lineage, specification and
            configuration version. The latest 500 matching events are shown for responsive review.
          </p>
          <DataGrid rows={events} searchText={(event) => `${event.material_code} ${event.attribute_code} ${event.attribute_name} ${event.supplier_name} ${event.reference_id} ${event.rule_code} ${event.severity} ${event.status}`} sortOptions={[["Time", (event) => event.event_time], ["Material", (event) => event.material_code], ["Supplier", (event) => event.supplier_name], ["Severity", (event) => event.severity], ["Status", (event) => event.status]]} initialPageSize={25}>
          {(gridRows) =>
          <div className="tablewrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Material</th>
                  <th>Attribute</th>
                  <th>Supplier</th>
                  <th>Reference</th>
                  <th>Rule</th>
                  <th>Severity</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {gridRows.map((event) => (
                  <tr key={event.id} onClick={() => setSelectedEvent(event)}>
                    <td>{new Date(event.event_time).toLocaleString()}</td>
                    <td>{event.material_code}</td>
                    <td>
                      {event.attribute_code} · {event.attribute_name}
                    </td>
                    <td>{event.supplier_name}</td>
                    <td>{event.reference_id}</td>
                    <td>{event.rule_code}</td>
                    <td>
                      <Badge>{event.severity}</Badge>
                    </td>
                    <td>{event.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          }
          </DataGrid>
        </section>
      )}
      {selectedEvent && (
        <div className="modalBackdrop">
          <div className="specModal">
            <div className="panelTitle">
              <div>
                <h2>
                  {selectedEvent.rule_code} · {selectedEvent.severity}
                </h2>
                <p className="muted">{selectedEvent.message}</p>
              </div>
              <button onClick={() => setSelectedEvent(null)}>×</button>
            </div>
            <div className="versionSummary">
              <span>
                Reference<b>{selectedEvent.reference_id}</b>
              </span>
              <span>
                Observed<b>{selectedEvent.observed_value}</b>
              </span>
              <span>
                Specification
                <b>
                  {selectedEvent.lsl ?? "—"} /{" "}
                  {selectedEvent.usl ?? selectedEvent.target_value ?? "—"}
                </b>
              </span>
              <span>
                Baseline
                <b>
                  N={selectedEvent.baseline_n ?? 0} ·{" "}
                  {selectedEvent.baseline_mean ?? "Insufficient"}
                </b>
              </span>
            </div>
            <pre className="evidenceJson">
              {JSON.stringify(selectedEvent.evidence, null, 2)}
            </pre>
            <div className="actions">
              <button onClick={() => setSelectedEvent(null)}>Close</button>
              {selectedEvent.status === "OPEN" && (
                <button
                  className="primary"
                  onClick={() => acknowledge(selectedEvent.id)}
                >
                  Acknowledge
                </button>
              )}
            </div>
          </div>
        </div>
      )}
      {area === "reports" && (
        <section className="panel">
          <h2>Operational Reports</h2>
          <p className="muted">
            The same event population reconciles across all report perspectives.
          </p>
          <div className="reportGrid">
            {[
              ["R01", "Executive Attention Summary"],
              ["R02", "Supplier Attention Report"],
              ["R03", "Ferro Alloy Attention Report"],
              ["R04", "Attribute Trend & Rule Evidence"],
              ["R05", "Batch/Test Consolidation Audit"],
            ].map(([code, name]) => (
              <button
                className="reportCard"
                key={code}
                onClick={() => openReport(code)}
              >
                <Badge>{code}</Badge>
                <b>{name}</b>
                <span>Open formatted report →</span>
              </button>
            ))}
          </div>
          {reportData && <FormattedAttentionReport data={reportData} />}
        </section>
      )}
      {area === "config" && config && (
        <>
          <section className="panel">
            <div className="panelTitle">
              <div>
                <h2>
                  Engine Configuration <small>Version {config.version}</small>
                </h2>
                <p className="muted">
                  Configuration changes are versioned and do not reinterpret
                  historical events.
                </p>
              </div>
              <button className="primary" onClick={saveConfig}>
                Save New Config Version
              </button>
            </div>
            <div className="formgrid">
              <label>
                Test Selection Mode
                <select
                  value={config.test_selection_mode}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      test_selection_mode: e.target.value,
                    })
                  }
                >
                  <option>LATEST_PER_REFERENCE</option>
                  <option>ALL_TESTS</option>
                  <option>FIRST_PER_REFERENCE</option>
                  <option>AGGREGATE_PER_REFERENCE</option>
                </select>
              </label>
              <label>
                Numeric Aggregator
                <select
                  value={config.numeric_aggregate_method}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      numeric_aggregate_method: e.target.value,
                    })
                  }
                >
                  <option>MEAN</option>
                  <option>MEDIAN</option>
                  <option>MIN</option>
                  <option>MAX</option>
                </select>
              </label>
              <label>
                Baseline Window
                <input
                  type="number"
                  value={config.baseline_window_n}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      baseline_window_n: Number(e.target.value),
                    })
                  }
                />
              </label>
              <label>
                Minimum Stable Baseline
                <input
                  type="number"
                  value={config.min_baseline_n}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      min_baseline_n: Number(e.target.value),
                    })
                  }
                />
              </label>
              <label>
                Near-Spec Margin (%)
                <input
                  type="number"
                  value={config.near_spec_margin_value}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      near_spec_margin_value: Number(e.target.value),
                    })
                  }
                />
              </label>
              <label className="check">
                <input
                  type="checkbox"
                  checked={config.enabled}
                  onChange={(e) =>
                    setConfig({ ...config, enabled: e.target.checked })
                  }
                />{" "}
                Engine enabled
              </label>
            </div>
            <h3>Enabled Rules</h3>
            <div className="ruleChecks">
              {Object.entries(config.rules).map(([rule, enabled]) => (
                <label className="check" key={rule}>
                  <input
                    type="checkbox"
                    checked={Boolean(enabled)}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        rules: { ...config.rules, [rule]: e.target.checked },
                      })
                    }
                  />
                  {rule}
                </label>
              ))}
            </div>
          </section>
          <section className="panel">
            <h2>Reference Identity Profiler</h2>
            <p className="muted">
              Default: supplier + material + supplier batch; fallback internal
              batch, then receipt number.
            </p>
            <DataGrid rows={profiler} searchText={(row) => `${row.field} ${row.examples.join(" ")}`} sortOptions={[["Field", (row) => row.field], ["Populated", (row) => row.populated_percent], ["Distinct", (row) => row.distinct], ["Duplicates", (row) => row.duplicate_records]]}>
            {(gridRows) => <div className="tablewrap">
            <table>
              <thead>
                <tr>
                  <th>Eligible Field</th>
                  <th>Populated</th>
                  <th>Distinct</th>
                  <th>Duplicates</th>
                  <th>Max / Reference</th>
                  <th>Examples</th>
                </tr>
              </thead>
              <tbody>
                {gridRows.map((row) => (
                  <tr key={row.field}>
                    <td>
                      <label className="check">
                        <input
                          type="checkbox"
                          checked={config.reference_fields.includes(row.field)}
                          onChange={(e) =>
                            setConfig({
                              ...config,
                              reference_fields: e.target.checked
                                ? [...config.reference_fields, row.field]
                                : config.reference_fields.filter(
                                    (field: string) => field !== row.field,
                                  ),
                            })
                          }
                        />
                        <b>{row.field}</b>
                      </label>
                    </td>
                    <td>{row.populated_percent}%</td>
                    <td>{row.distinct}</td>
                    <td>{row.duplicate_records}</td>
                    <td>{row.max_records_per_reference}</td>
                    <td>{row.examples.join(", ") || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>}
            </DataGrid>
          </section>
        </>
      )}
    </>
  );
}
function ReceiptTable({
  rows,
  open,
  emptyText = "No incoming receipts match the grid filter.",
}: {
  rows: any[];
  open: (id: string) => void;
  emptyText?: string;
}) {
  return (
    <DataGrid
      rows={rows}
      searchText={(r) => `${r.receipt_no} ${r.material.material_code} ${r.material.material_name} ${r.supplier.supplier_name} ${r.supplier_batch_no} ${r.inspection_status} ${r.release_state}`}
      sortOptions={[
        ["Receipt date / number", (r) => r.receipt_datetime || r.receipt_no],
        ["Material", (r) => r.material.material_name],
        ["Supplier", (r) => r.supplier.supplier_name],
        ["Quantity", (r) => Number(r.quantity)],
        ["Quality status", (r) => r.inspection_status],
      ]}
    >
      {(gridRows) => <div className="tablewrap">
      <table>
        <thead>
          <tr>
            <th>Receipt</th>
            <th>Material</th>
            <th>Supplier</th>
            <th>Supplier Batch</th>
            <th>Spec Version</th>
            <th>Qty</th>
            <th>Quality Status</th>
            <th>Release</th>
          </tr>
        </thead>
        <tbody>
          {gridRows.map((r) => (
            <tr key={r.id} onClick={() => open(r.id)}>
              <td className="link">{r.receipt_no}</td>
              <td>
                <b>{r.material.material_code}</b>
                <br />
                <small>{r.material.material_name}</small>
              </td>
              <td>{r.supplier.supplier_name}</td>
              <td>{r.supplier_batch_no}</td>
              <td>
                <Badge>{r.specification_version}</Badge>
              </td>
              <td>
                {r.quantity} {r.uom}
              </td>
              <td>
                <Badge>{r.inspection_status}</Badge>
              </td>
              <td>
                <Badge>{r.release_state}</Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!gridRows.length && <div className="empty">{emptyText}</div>}
    </div>}
    </DataGrid>
  );
}
function ConfigPage({ notify, refreshApp }: any) {
  const [section, setSection] = useState("locations"),
    [mats, setMats] = useState<any[]>([]),
    [sups, setSups] = useState<any[]>([]),
    [locPlants, setLocPlants] = useState<any[]>([]),
    [smsRows, setSmsRows] = useState<any[]>([]),
    [storeRows, setStoreRows] = useState<any[]>([]),
    [groups, setGroups] = useState<any[]>([]),
    [attrs, setAttrs] = useState<any[]>([]),
    [specs, setSpecs] = useState<any[]>([]),
    [specLogs, setSpecLogs] = useState<any[]>([]);
  const [demoLoading, setDemoLoading] = useState(false);
  const [mat, setMat] = useState({
    material_code: "",
    material_name: "",
    material_description: "",
    base_uom: "MT",
    batch_managed: true,
    active: true,
  });
  const [sup, setSup] = useState({
    supplier_code: "",
    supplier_name: "",
    active: true,
  });
  const [group, setGroup] = useState({
    group_code: "",
    group_name: "",
    description: "",
    active: true,
  });
  const [plant, setPlant] = useState({
    plant_code: "",
    plant_name: "",
    active: true,
  });
  const [sms, setSms] = useState({
    plant_id: "",
    sms_code: "",
    sms_name: "",
    active: true,
  });
  const [store, setStore] = useState({
    sms_id: "",
    store_code: "",
    store_name: "",
    active: true,
  });
  const emptyAttr = {
    group_id: "",
    attribute_code: "",
    attribute_name: "",
    uom: "%",
    data_type: "NUMERIC",
    precision_scale: 3,
    test_method: "",
    category_options: "",
    active: true,
  };
  const [attr, setAttr] = useState<any>(emptyAttr);
  const [spec, setSpec] = useState<any>({
    material_id: "",
    version: "V1",
    status: "",
    effective_from: "",
    effective_to: "",
    attributes: [],
  });
  const [specGroupId, setSpecGroupId] = useState("");
  const [specGroupNotice, setSpecGroupNotice] = useState("");
  const [newSpecOpen, setNewSpecOpen] = useState(false),
    [newSpecMaterialId, setNewSpecMaterialId] = useState(""),
    [latestSpec, setLatestSpec] = useState<any>(null);
  const get = async (p: string) => (await fetch(API + p)).json();
  const reload = async () => {
    setMats(await get("/config/materials"));
    setSups(await get("/config/suppliers"));
    setLocPlants(await get("/config/plants"));
    setSmsRows(await get("/config/sms-locations"));
    setStoreRows(await get("/config/store-locations"));
    setGroups(await get("/config/attribute-groups"));
    setAttrs(await get("/config/quality-attributes"));
    setSpecs(await get("/config/specifications"));
    setSpecLogs(await get("/config/specification-version-logs"));
    refreshApp();
  };
  useEffect(() => {
    reload();
  }, []);
  const post = async (path: string, body: any) => {
    const r = await fetch(API + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const d = await r.json();
    if (!r.ok) {
      notify(d.detail || "Save failed");
      return false;
    }
    notify("Master data saved successfully.");
    await reload();
    return true;
  };
  const resetMasters = async () => {
    const confirmed = window.confirm(
      "Reset all master data?\n\nPlant locations, materials, suppliers, quality attributes and specification sheets will be cleared from configuration and new transactions. Existing receipt and quality transactions will remain unchanged. This action cannot be undone from the UI.",
    );
    if (!confirmed) return;
    const response = await fetch(API + "/config/reset-masters", {
      method: "POST",
    });
    const data = await response.json();
    if (!response.ok) {
      notify(data.detail || "Master reset failed");
      return;
    }
    setSpec({
      material_id: "",
      version: "V1",
      status: "",
      effective_from: "",
      effective_to: "",
      attributes: [],
    });
    setSpecGroupId("");
    notify(data.message);
    await reload();
  };
  const resetApp = async () => {
    const confirmed = window.confirm(
      "Reset the entire application?\n\nThis permanently deletes ALL master data, specifications, receipts, samples, quality results, dispositions, attention events, configuration and audit history. This cannot be undone.",
    );
    if (!confirmed) return;
    const response = await fetch(API + "/config/reset-app", { method: "POST" });
    const data = await response.json();
    if (!response.ok) {
      notify(data.detail || "Application reset failed");
      return;
    }
    setSpec({ material_id: "", version: "V1", status: "", effective_from: "", effective_to: "", attributes: [] });
    setSpecGroupId("");
    notify(data.message);
    await reload();
  };
  const loadDemo = async () => {
    const confirmed = window.confirm(
      "Load the large ferro-alloy demonstration dataset?\n\nThis replaces ALL current application data and generates 50,100 completed samples with approximately 250,500 quality results. Generation may take up to a minute.",
    );
    if (!confirmed) return;
    setDemoLoading(true);
    try {
      const response = await fetch(API + "/config/load-demo", { method: "POST" });
      const data = await response.json();
      if (!response.ok) {
        notify(data.detail || "Demo data generation failed");
        return;
      }
      notify(`${data.message} ${data.samples.toLocaleString()} samples and ${data.test_results.toLocaleString()} quality results created.`);
      await reload();
    } finally {
      setDemoLoading(false);
    }
  };
  const selectSpecGroup = (groupId: string) => {
    setSpecGroupId(groupId);
    setSpecGroupNotice("");
    if (!groupId) return;
    const groupName =
      groups.find((g) => g.id === groupId)?.group_name || "Selected group";
    const available = attrs.filter((a) => a.active && a.group_id === groupId);
    if (!available.length) {
      setSpecGroupNotice(`No attributes are available in ${groupName}.`);
      return;
    }
    const existing = new Set(spec.attributes.map((a: any) => a.attribute_id));
    const additions = available
      .filter((a) => !existing.has(a.id))
      .map((a: any, i: number) => ({
        group_id: groupId,
        attribute_id: a.id,
        mandatory: true,
        lsl: "",
        aim_value: "",
        usl: "",
        target_value: "",
        display_sequence: spec.attributes.length + i + 1,
      }));
    setSpecGroupNotice(
      additions.length
        ? `${additions.length} attribute${additions.length === 1 ? "" : "s"} loaded from ${groupName}.`
        : `All attributes from ${groupName} are already added.`,
    );
    if (additions.length) {
      setSpec({ ...spec, attributes: [...spec.attributes, ...additions] });
      setSpecGroupId("");
    }
  };
  const loadSpecification = (materialId: string) => {
    const scoped = specs
      .filter((s) => s.material_id === materialId)
      .sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );
    const latest = scoped[0];
    const nextVersion = `V${scoped.length + 1}`;
    setSpec({
      ...spec,
      material_id: materialId,
      version: nextVersion,
      attributes: latest
        ? latest.attributes.map((a: any, i: number) => ({
            group_id:
              attrs.find((x) => x.id === a.attribute_id)?.group_id || "",
            attribute_id: a.attribute_id,
            mandatory: a.mandatory,
            lsl: a.lsl ?? "",
            aim_value: a.aim_value ?? "",
            usl: a.usl ?? "",
            target_value: a.target_value ?? "",
            display_sequence: i + 1,
          }))
        : [],
    });
    setSpecGroupId("");
    setSpecGroupNotice(
      latest
        ? `${latest.version} loaded. Modify its attributes and save to create ${nextVersion}.`
        : `No existing specification. Configure attributes to create ${nextVersion}.`,
    );
  };
  const saveSpec = async (e: any) => {
    e.preventDefault();
    const body = {
      material_id: spec.material_id,
      attributes: spec.attributes.map((a: any, i: number) => ({
        ...a,
        lsl: a.lsl === "" ? null : Number(a.lsl),
        aim_value: a.aim_value === "" ? null : Number(a.aim_value),
        usl: a.usl === "" ? null : Number(a.usl),
        target_value: a.target_value || null,
        display_sequence: i + 1,
      })),
    };
    if (await post("/config/specifications", body)) {
      setSpec({
        material_id: "",
        version: "V1",
        status: "",
        effective_from: "",
        effective_to: "",
        attributes: [],
      });
      setSpecGroupId("");
    }
  };
  const visibleAttrs = attr.group_id
    ? attrs.filter((a) => a.group_id === attr.group_id)
    : [];
  const chooseNewSpecMaterial = async (materialId: string) => {
    setNewSpecMaterialId(materialId);
    setLatestSpec(null);
    if (!materialId) return;
    const r = await fetch(API + `/config/specifications/latest/${materialId}`);
    const d = await r.json();
    if (!r.ok) {
      notify(d.detail || "Unable to find latest specification");
      return;
    }
    setLatestSpec(d);
  };
  const closeNewSpec = () => {
    setNewSpecOpen(false);
    setNewSpecMaterialId("");
    setLatestSpec(null);
  };
  const isSpecSheet = section === "specs";
  return (
    <>
      <div className="configTabs configPrimaryTabs">
        <button
          className={!isSpecSheet ? "active" : ""}
          onClick={() => isSpecSheet && setSection("locations")}
        >
          Masters
        </button>
        <button
          className={isSpecSheet ? "active" : ""}
          onClick={() => setSection("specs")}
        >
          Quality Spec Sheet
        </button>
      </div>
      {newSpecOpen && (
        <div className="modalBackdrop">
          <div className="specModal">
            <div className="panelTitle">
              <div>
                <h2>New Specification Version</h2>
                <p className="muted">
                  Select a material to review its latest approved specification.
                </p>
              </div>
              <button type="button" onClick={closeNewSpec}>
                ×
              </button>
            </div>
            <label>
              Material
              <select
                value={newSpecMaterialId}
                onChange={(e) => chooseNewSpecMaterial(e.target.value)}
              >
                <option value="">Select material</option>
                {mats
                  .filter((m) => m.active)
                  .map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.material_code} · {m.material_name}
                    </option>
                  ))}
              </select>
            </label>
            {latestSpec && (
              <>
                <div className="versionSummary">
                  <span>
                    Latest Version<b>{latestSpec.version}</b>
                  </span>
                  <span>
                    New Version<b>{latestSpec.next_version}</b>
                  </span>
                  <span>
                    Status<b>DRAFT</b>
                  </span>
                  <span>
                    Validity
                    <b>
                      {new Date(latestSpec.effective_from).toLocaleDateString()}{" "}
                      – {new Date(latestSpec.effective_to).toLocaleDateString()}
                    </b>
                  </span>
                </div>
                <DataGrid rows={latestSpec.attributes} searchText={(a) => `${a.code} ${a.name} ${a.data_type} ${a.uom || ""}`} sortOptions={[["Attribute", (a) => a.name], ["Code", (a) => a.code], ["Type", (a) => a.data_type]]}>
                {(gridRows) =>
                <div className="tablewrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Attribute</th>
                        <th>Type</th>
                        <th>Minimum</th>
                        <th>Aim / Required</th>
                        <th>Maximum</th>
                        <th>Mandatory</th>
                      </tr>
                    </thead>
                    <tbody>
                      {gridRows.map((a: any) => (
                        <tr key={a.code}>
                          <td>
                            <b>{a.code}</b> · {a.name}
                          </td>
                          <td>{a.data_type}</td>
                          <td>{a.lsl ?? "—"}</td>
                          <td>{a.aim_value ?? a.target_value ?? "—"}</td>
                          <td>{a.usl ?? "—"}</td>
                          <td>{a.mandatory ? "Yes" : "No"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                }
                </DataGrid>
                <p className="confirmText">
                  Create version <b>{latestSpec.next_version}</b> as an
                  unapproved draft?
                </p>
                <div className="actions">
                  <button type="button" onClick={closeNewSpec}>
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="primary"
                    onClick={async () => {
                      if (
                        await post(
                          `/config/specifications/${latestSpec.id}/new-version`,
                          {},
                        )
                      )
                        closeNewSpec();
                    }}
                  >
                    Confirm New Version
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
      <div className={isSpecSheet ? "configContent" : "configMasterLayout"}>
        {!isSpecSheet && (
          <nav className="masterSidebar">
            <div className="masterSidebarTitle">Master Data</div>
            {[
              ["locations", "Plant"],
              ["materials", "Material"],
              ["suppliers", "Supplier"],
              ["attributes", "Quality Attributes"],
            ].map(([k, l]) => (
              <button
                key={k}
                className={section === k ? "active" : ""}
                onClick={() => setSection(k)}
              >
                {l}
              </button>
            ))}
            <div className="masterResetArea">
              <button
                type="button"
                className="dangerAction masterResetButton"
                onClick={resetMasters}
              >
                Reset Master Data
              </button>
              <small>Transactions are preserved.</small>
              <div className="appDataActions">
                <button
                  type="button"
                  className="demoAction"
                  disabled={demoLoading}
                  onClick={loadDemo}
                >
                  {demoLoading ? "Generating Demo…" : "Load Demo Data"}
                </button>
                <button
                  type="button"
                  className="dangerAction masterResetButton"
                  disabled={demoLoading}
                  onClick={resetApp}
                >
                  Reset Entire App
                </button>
              </div>
              <small>These actions replace or delete transactions.</small>
            </div>
          </nav>
        )}
        <div className="configSection">
          {section === "locations" && (
            <>
              <section className="panel">
                <h2>Plant Master</h2>
                <form
                  className="inlineForm locationForm"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    if (await post("/config/plants", plant))
                      setPlant({
                        plant_code: "",
                        plant_name: "",
                        active: true,
                      });
                  }}
                >
                  <label>
                    Plant Code
                    <input
                      required
                      value={plant.plant_code}
                      onChange={(e) =>
                        setPlant({ ...plant, plant_code: e.target.value })
                      }
                    />
                  </label>
                  <label>
                    Plant Name
                    <input
                      required
                      value={plant.plant_name}
                      onChange={(e) =>
                        setPlant({ ...plant, plant_name: e.target.value })
                      }
                    />
                  </label>
                  <button className="primary">Add Plant</button>
                </form>
                <DataGrid rows={locPlants} searchText={(x) => `${x.plant_code} ${x.plant_name} ${x.active ? "active" : "inactive"}`} sortOptions={[["Plant code", (x) => x.plant_code], ["Plant name", (x) => x.plant_name], ["Status", (x) => x.active ? 0 : 1]]}>
                {(gridRows) => <div className="tablewrap">
                <table>
                  <thead>
                    <tr>
                      <th>Plant Code</th>
                      <th>Plant Name</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {gridRows.map((x) => (
                      <tr key={x.id}>
                        <td>
                          <b>{x.plant_code}</b>
                        </td>
                        <td>{x.plant_name}</td>
                        <td>
                          <Badge>{x.active ? "ACTIVE" : "INACTIVE"}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>}
                </DataGrid>
              </section>
              <section className="panel">
                <h2>SMS Locations</h2>
                <p className="muted">
                  Map one or more Steel Melting Shop locations to a plant.
                </p>
                <form
                  className="inlineForm locationForm"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    if (await post("/config/sms-locations", sms))
                      setSms({
                        plant_id: "",
                        sms_code: "",
                        sms_name: "",
                        active: true,
                      });
                  }}
                >
                  <label>
                    Plant
                    <select
                      required
                      value={sms.plant_id}
                      onChange={(e) =>
                        setSms({ ...sms, plant_id: e.target.value })
                      }
                    >
                      <option value="">Select plant</option>
                      {locPlants
                        .filter((x) => x.active)
                        .map((x) => (
                          <option key={x.id} value={x.id}>
                            {x.plant_code} · {x.plant_name}
                          </option>
                        ))}
                    </select>
                  </label>
                  <label>
                    SMS Code
                    <input
                      required
                      value={sms.sms_code}
                      onChange={(e) =>
                        setSms({ ...sms, sms_code: e.target.value })
                      }
                    />
                  </label>
                  <label>
                    SMS Name
                    <input
                      required
                      value={sms.sms_name}
                      onChange={(e) =>
                        setSms({ ...sms, sms_name: e.target.value })
                      }
                    />
                  </label>
                  <button className="primary">Add SMS</button>
                </form>
                <DataGrid rows={smsRows} searchText={(x) => `${x.plant_code} ${x.plant_name} ${x.sms_code} ${x.sms_name}`} sortOptions={[["SMS code", (x) => x.sms_code], ["SMS name", (x) => x.sms_name], ["Plant", (x) => x.plant_name]]}>
                {(gridRows) => <div className="tablewrap">
                <table>
                  <thead>
                    <tr>
                      <th>Plant</th>
                      <th>SMS Code</th>
                      <th>SMS Name</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {gridRows.map((x) => (
                      <tr key={x.id}>
                        <td>
                          {x.plant_code} · {x.plant_name}
                        </td>
                        <td>
                          <b>{x.sms_code}</b>
                        </td>
                        <td>{x.sms_name}</td>
                        <td>
                          <Badge>{x.active ? "ACTIVE" : "INACTIVE"}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>}
                </DataGrid>
              </section>
              <section className="panel">
                <h2>Store Locations</h2>
                <p className="muted">
                  Map one or more store locations to an SMS.
                </p>
                <form
                  className="inlineForm locationForm"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    if (await post("/config/store-locations", store))
                      setStore({
                        sms_id: "",
                        store_code: "",
                        store_name: "",
                        active: true,
                      });
                  }}
                >
                  <label>
                    SMS Location
                    <select
                      required
                      value={store.sms_id}
                      onChange={(e) =>
                        setStore({ ...store, sms_id: e.target.value })
                      }
                    >
                      <option value="">Select SMS</option>
                      {smsRows
                        .filter((x) => x.active)
                        .map((x) => (
                          <option key={x.id} value={x.id}>
                            {x.plant_code} · {x.sms_code} · {x.sms_name}
                          </option>
                        ))}
                    </select>
                  </label>
                  <label>
                    Store Code
                    <input
                      required
                      value={store.store_code}
                      onChange={(e) =>
                        setStore({ ...store, store_code: e.target.value })
                      }
                    />
                  </label>
                  <label>
                    Store Name
                    <input
                      required
                      value={store.store_name}
                      onChange={(e) =>
                        setStore({ ...store, store_name: e.target.value })
                      }
                    />
                  </label>
                  <button className="primary">Add Store</button>
                </form>
                <DataGrid rows={storeRows} searchText={(x) => `${x.plant_code} ${x.sms_code} ${x.sms_name} ${x.store_code} ${x.store_name}`} sortOptions={[["Store code", (x) => x.store_code], ["Store name", (x) => x.store_name], ["SMS", (x) => x.sms_name], ["Plant", (x) => x.plant_code]]}>
                {(gridRows) => <div className="tablewrap">
                <table>
                  <thead>
                    <tr>
                      <th>Plant</th>
                      <th>SMS</th>
                      <th>Store Code</th>
                      <th>Store Name</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {gridRows.map((x) => (
                      <tr key={x.id}>
                        <td>{x.plant_code}</td>
                        <td>
                          {x.sms_code} · {x.sms_name}
                        </td>
                        <td>
                          <b>{x.store_code}</b>
                        </td>
                        <td>{x.store_name}</td>
                        <td>
                          <Badge>{x.active ? "ACTIVE" : "INACTIVE"}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>}
                </DataGrid>
              </section>
            </>
          )}
          {section === "materials" && (
            <section className="panel">
              <h2>Ferro Alloy Material Master</h2>
              <p className="muted">
                Maintain materials independently from their quality
                specifications.
              </p>
              <form
                className="inlineForm materialForm"
                onSubmit={async (e) => {
                  e.preventDefault();
                  if (await post("/config/materials", mat))
                    setMat({
                      material_code: "",
                      material_name: "",
                      material_description: "",
                      base_uom: "MT",
                      batch_managed: true,
                      active: true,
                    });
                }}
              >
                <label>
                  Material Code
                  <input
                    required
                    value={mat.material_code}
                    onChange={(e) =>
                      setMat({ ...mat, material_code: e.target.value })
                    }
                  />
                </label>
                <label>
                  Material Name
                  <input
                    required
                    value={mat.material_name}
                    onChange={(e) =>
                      setMat({ ...mat, material_name: e.target.value })
                    }
                  />
                </label>
                <label>
                  Material Description
                  <input
                    required
                    value={mat.material_description}
                    onChange={(e) =>
                      setMat({ ...mat, material_description: e.target.value })
                    }
                  />
                </label>
                <label>
                  Base UOM
                  <input
                    required
                    value={mat.base_uom}
                    onChange={(e) =>
                      setMat({ ...mat, base_uom: e.target.value })
                    }
                  />
                </label>
                <button className="primary">Add Material</button>
              </form>
              <DataGrid rows={mats} searchText={(m) => `${m.material_code} ${m.material_name} ${m.material_description} ${m.base_uom}`} sortOptions={[["Material code", (m) => m.material_code], ["Material name", (m) => m.material_name], ["Base UOM", (m) => m.base_uom], ["Status", (m) => m.active ? 0 : 1]]}>
              {(gridRows) =>
              <div className="tablewrap">
                <table>
                  <thead>
                    <tr>
                      <th>Material Code</th>
                      <th>Material Name</th>
                      <th>Description</th>
                      <th>Base UOM</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {gridRows.map((m) => (
                      <tr key={m.id}>
                        <td>
                          <b>{m.material_code}</b>
                        </td>
                        <td>{m.material_name}</td>
                        <td>{m.material_description}</td>
                        <td>{m.base_uom}</td>
                        <td>
                          <Badge>{m.active ? "ACTIVE" : "INACTIVE"}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              }
              </DataGrid>
            </section>
          )}
          {section === "specs" && (
            <>
              <div className="newSpecAction">
                <button
                  type="button"
                  className="primary"
                  onClick={() => setNewSpecOpen(true)}
                >
                  + New Spec
                </button>
              </div>
              <section className="panel">
                <div className="panelTitle">
                  <div>
                    <h2>Quality Specification</h2>
                    <p className="muted">
                      Select a material to load its latest specification, then
                      change the attributes and create the next version.
                    </p>
                  </div>
                </div>
                <form onSubmit={saveSpec} className="formgrid">
                  <label>
                    Material
                    <select
                      required
                      value={spec.material_id}
                      onChange={(e) => loadSpecification(e.target.value)}
                    >
                      <option value="">Select material</option>
                      {mats.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.material_code} · {m.material_name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    New Version
                    <input readOnly value={spec.version || "V1"} />
                    <span className="hint">
                      Assigned automatically when this working copy is saved.
                    </span>
                  </label>
                  <div className="full specAttrs">
                    <div className="panelTitle">
                      <div>
                        <h2>Specification Attributes</h2>
                        <p className="muted">
                          Select a group to load all of its attributes, then
                          enter the specification values.
                        </p>
                      </div>
                      <label className="specGroupPicker">
                        Attribute Group
                        <select
                          value={specGroupId}
                          onChange={(e) => selectSpecGroup(e.target.value)}
                        >
                          <option value="">Select attribute group</option>
                          {groups
                            .filter((g) => g.active)
                            .map((g) => (
                              <option key={g.id} value={g.id}>
                                {g.group_code} · {g.group_name}
                              </option>
                            ))}
                        </select>
                      </label>
                    </div>
                    {specGroupNotice && (
                      <div className="groupNotice">{specGroupNotice}</div>
                    )}
                    {spec.attributes.map((a: any, i: number) => {
                      const definition = attrs.find(
                        (x) => x.id === a.attribute_id,
                      );
                      const groupName =
                        groups.find((g) => g.id === a.group_id)?.group_name ||
                        "";
                      if (!definition) return null;
                      return (
                        <div className="specRow" key={a.attribute_id}>
                          <span className="groupTag">{groupName}</span>
                          <span>
                            <b>{definition.attribute_code}</b> ·{" "}
                            {definition.attribute_name}
                            <small>
                              {definition.data_type === "NUMERIC"
                                ? ` (${definition.uom || "No UOM"})`
                                : ` (${definition.data_type})`}
                            </small>
                          </span>
                          {definition.data_type === "NUMERIC" ? (
                            <>
                              <input
                                type="number"
                                step="any"
                                placeholder="Minimum value"
                                value={a.lsl}
                                onChange={(e) => {
                                  const x = [...spec.attributes];
                                  x[i] = { ...a, lsl: e.target.value };
                                  setSpec({ ...spec, attributes: x });
                                }}
                              />
                              <input
                                required
                                type="number"
                                step="any"
                                min={a.lsl || undefined}
                                max={a.usl || undefined}
                                placeholder="Aim value *"
                                value={a.aim_value}
                                onChange={(e) => {
                                  const x = [...spec.attributes];
                                  x[i] = { ...a, aim_value: e.target.value };
                                  setSpec({ ...spec, attributes: x });
                                }}
                              />
                              <input
                                type="number"
                                step="any"
                                placeholder="Maximum value"
                                value={a.usl}
                                onChange={(e) => {
                                  const x = [...spec.attributes];
                                  x[i] = { ...a, usl: e.target.value };
                                  setSpec({ ...spec, attributes: x });
                                }}
                              />
                            </>
                          ) : definition.data_type === "CATEGORY" ? (
                            <>
                              <select
                                required
                                value={a.target_value}
                                onChange={(e) => {
                                  const x = [...spec.attributes];
                                  x[i] = { ...a, target_value: e.target.value };
                                  setSpec({ ...spec, attributes: x });
                                }}
                              >
                                <option value="">Select required value</option>
                                {definition.category_options.map(
                                  (option: string) => (
                                    <option key={option}>{option}</option>
                                  ),
                                )}
                              </select>
                              <span />
                              <span />
                            </>
                          ) : (
                            <>
                              <select
                                required
                                value={a.target_value}
                                onChange={(e) => {
                                  const x = [...spec.attributes];
                                  x[i] = { ...a, target_value: e.target.value };
                                  setSpec({ ...spec, attributes: x });
                                }}
                              >
                                <option value="">Select required value</option>
                                <option value="YES">Yes</option>
                                <option value="NO">No</option>
                              </select>
                              <span />
                              <span />
                            </>
                          )}
                          <label className="check">
                            <input
                              type="checkbox"
                              checked={a.mandatory}
                              onChange={(e) => {
                                const x = [...spec.attributes];
                                x[i] = { ...a, mandatory: e.target.checked };
                                setSpec({ ...spec, attributes: x });
                              }}
                            />{" "}
                            Mandatory
                          </label>
                          <button
                            type="button"
                            onClick={() =>
                              setSpec({
                                ...spec,
                                attributes: spec.attributes.filter(
                                  (_: any, j: number) => j !== i,
                                ),
                              })
                            }
                          >
                            Remove
                          </button>
                        </div>
                      );
                    })}
                    {!spec.attributes.length && (
                      <div className="empty smallEmpty">
                        Select an attribute group to load its attributes.
                      </div>
                    )}
                  </div>
                  <div className="full actions">
                    <button className="primary">
                      Save Dated Specification
                    </button>
                  </div>
                </form>
              </section>
              <section className="panel">
                <h2>Specification Version History</h2>
                <p className="muted">
                  The latest version is enabled for new transactions. Older
                  versions remain available only for historical transaction
                  traceability.
                </p>
                <DataGrid rows={specs} searchText={(s) => `${s.material_code} ${s.material_name} ${s.version} ${s.status} ${s.attributes.map((a: any) => a.code).join(" ")}`} sortOptions={[["Created at", (s) => s.created_at], ["Material", (s) => s.material_name], ["Version", (s) => s.version], ["Status", (s) => s.is_current ? 0 : 1]]}>
                {(gridRows) =>
                <div className="tablewrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Material</th>
                        <th>Version</th>
                        <th>Created At</th>
                        <th>Attributes</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {gridRows.map((s) => (
                        <tr key={s.id}>
                          <td>
                            <b>{s.material_code}</b>
                            <br />
                            <small>{s.material_name}</small>
                          </td>
                          <td>
                            <Badge>{s.version}</Badge>
                          </td>
                          <td>{new Date(s.created_at).toLocaleString()}</td>
                          <td>
                            {s.attributes.map((a: any) => a.code).join(", ")}
                          </td>
                          <td>
                            <Badge>
                              {s.is_current ? "ENABLED" : "DISABLED"}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                }
                </DataGrid>
              </section>
              <section className="panel">
                <h2>Version Change Audit Log</h2>
                <p className="muted">
                  Permanent change history retained for the specification audit
                  report.
                </p>
                <DataGrid rows={specLogs} searchText={(x) => `${x.material_code} ${x.material_name} ${x.previous_version || ""} ${x.new_version} ${x.changed_by}`} sortOptions={[["Changed at", (x) => x.changed_at], ["Material", (x) => x.material_name], ["New version", (x) => x.new_version], ["Changed by", (x) => x.changed_by]]}>
                {(gridRows) =>
                <div className="tablewrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Changed At</th>
                        <th>Material</th>
                        <th>Version Change</th>
                        <th>Added</th>
                        <th>Modified</th>
                        <th>Deleted</th>
                        <th>Changed By</th>
                      </tr>
                    </thead>
                    <tbody>
                      {gridRows.map((x) => (
                        <tr key={x.id}>
                          <td>{new Date(x.changed_at).toLocaleString()}</td>
                          <td>
                            <b>{x.material_code}</b>
                            <br />
                            <small>{x.material_name}</small>
                          </td>
                          <td>
                            {x.previous_version || "—"} → <b>{x.new_version}</b>
                          </td>
                          <td>{x.change_summary.added}</td>
                          <td>{x.change_summary.modified}</td>
                          <td>{x.change_summary.removed}</td>
                          <td>{x.changed_by}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {!gridRows.length && (
                    <div className="empty smallEmpty">
                      Version changes will appear here after the next
                      specification is created.
                    </div>
                  )}
                </div>
                }
                </DataGrid>
              </section>
            </>
          )}
          {section === "suppliers" && (
            <section className="panel">
              <h2>Supplier Master</h2>
              <p className="muted">
                Disable a supplier to prevent it from being selected for new
                incoming receipts. Historical receipts remain unchanged and
                traceable.
              </p>
              <form
                className="inlineForm"
                onSubmit={async (e) => {
                  e.preventDefault();
                  if (await post("/config/suppliers", sup))
                    setSup({
                      supplier_code: "",
                      supplier_name: "",
                      active: true,
                    });
                }}
              >
                <label>
                  Supplier Code
                  <input
                    required
                    value={sup.supplier_code}
                    onChange={(e) =>
                      setSup({ ...sup, supplier_code: e.target.value })
                    }
                  />
                </label>
                <label>
                  Supplier Name
                  <input
                    required
                    value={sup.supplier_name}
                    onChange={(e) =>
                      setSup({ ...sup, supplier_name: e.target.value })
                    }
                  />
                </label>
                <button className="primary">Add Supplier</button>
              </form>
              <DataGrid rows={sups} searchText={(s) => `${s.supplier_code} ${s.supplier_name} ${s.active ? "active" : "inactive"}`} sortOptions={[["Supplier code", (s) => s.supplier_code], ["Supplier name", (s) => s.supplier_name], ["Status", (s) => s.active ? 0 : 1]]}>
              {(gridRows) => <div className="tablewrap">
              <table>
                <thead>
                  <tr>
                    <th>Code</th>
                    <th>Supplier</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {gridRows.map((s) => (
                    <tr key={s.id}>
                      <td>
                        <b>{s.supplier_code}</b>
                      </td>
                      <td>{s.supplier_name}</td>
                      <td>
                        <Badge>{s.active ? "ACTIVE" : "INACTIVE"}</Badge>
                      </td>
                      <td>
                        <button
                          type="button"
                          className={s.active ? "dangerAction" : "primary"}
                          onClick={async () => {
                            const action = s.active ? "disable" : "enable";
                            if (
                              !confirm(
                                `Are you sure you want to ${action} ${s.supplier_name}?`,
                              )
                            )
                              return;
                            const r = await fetch(
                              API + `/config/suppliers/${s.id}/status`,
                              {
                                method: "PATCH",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ active: !s.active }),
                              },
                            );
                            if (r.ok) {
                              notify(
                                `Supplier ${s.supplier_name} ${s.active ? "disabled" : "enabled"}.`,
                              );
                              await reload();
                            } else {
                              const e = await r.json();
                              notify(
                                e.detail || "Unable to update supplier status",
                              );
                            }
                          }}
                        >
                          {s.active ? "Disable" : "Enable"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>}
              </DataGrid>
            </section>
          )}
          {section === "attributes" && (
            <>
              <section className="panel">
                <h2>Attribute Groups</h2>
                <p className="muted">
                  Create logical groups such as Chemistry, Physical Properties,
                  or Visual Inspection.
                </p>
                <form
                  className="inlineForm groupForm"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    if (await post("/config/attribute-groups", group))
                      setGroup({
                        group_code: "",
                        group_name: "",
                        description: "",
                        active: true,
                      });
                  }}
                >
                  <label>
                    Group Code
                    <input
                      required
                      value={group.group_code}
                      onChange={(e) =>
                        setGroup({ ...group, group_code: e.target.value })
                      }
                    />
                  </label>
                  <label>
                    Group Name
                    <input
                      required
                      value={group.group_name}
                      onChange={(e) =>
                        setGroup({ ...group, group_name: e.target.value })
                      }
                    />
                  </label>
                  <label>
                    Description
                    <input
                      value={group.description}
                      onChange={(e) =>
                        setGroup({ ...group, description: e.target.value })
                      }
                    />
                  </label>
                  <button className="primary">Add Group</button>
                </form>
                <DataGrid rows={groups} searchText={(g) => `${g.group_code} ${g.group_name} ${g.description || ""}`} sortOptions={[["Group code", (g) => g.group_code], ["Group name", (g) => g.group_name], ["Status", (g) => g.active ? 0 : 1]]}>
                {(gridRows) => <div className="tablewrap">
                <table>
                  <thead>
                    <tr>
                      <th>Code</th>
                      <th>Attribute Group</th>
                      <th>Description</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {gridRows.map((g) => (
                      <tr key={g.id}>
                        <td>
                          <b>{g.group_code}</b>
                        </td>
                        <td>{g.group_name}</td>
                        <td>{g.description || "—"}</td>
                        <td>
                          <Badge>{g.active ? "ACTIVE" : "INACTIVE"}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>}
                </DataGrid>
              </section>
              <section className="panel">
                <h2>Quality Attributes</h2>
                <p className="muted">
                  Select an attribute group to view its attributes or add a new
                  one.
                </p>
                <form
                  className="attributeForm"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    const body = {
                      ...attr,
                      category_options:
                        attr.data_type === "CATEGORY"
                          ? attr.category_options
                              .split(",")
                              .map((x: string) => x.trim())
                              .filter(Boolean)
                          : [],
                    };
                    if (await post("/config/quality-attributes", body))
                      setAttr(emptyAttr);
                  }}
                >
                  <label>
                    Attribute Group
                    <select
                      required
                      value={attr.group_id}
                      onChange={(e) =>
                        setAttr({ ...attr, group_id: e.target.value })
                      }
                    >
                      <option value="">Select group</option>
                      {groups
                        .filter((g) => g.active)
                        .map((g) => (
                          <option key={g.id} value={g.id}>
                            {g.group_code} · {g.group_name}
                          </option>
                        ))}
                    </select>
                  </label>
                  <label>
                    Attribute Code
                    <input
                      required
                      value={attr.attribute_code}
                      onChange={(e) =>
                        setAttr({ ...attr, attribute_code: e.target.value })
                      }
                    />
                  </label>
                  <label>
                    Attribute Name
                    <input
                      required
                      value={attr.attribute_name}
                      onChange={(e) =>
                        setAttr({ ...attr, attribute_name: e.target.value })
                      }
                    />
                  </label>
                  <label>
                    Attribute Type
                    <select
                      value={attr.data_type}
                      onChange={(e) =>
                        setAttr({ ...attr, data_type: e.target.value })
                      }
                    >
                      <option value="NUMERIC">Numeric</option>
                      <option value="CATEGORY">Category</option>
                      <option value="BOOLEAN">Yes / No</option>
                    </select>
                  </label>
                  {attr.data_type === "NUMERIC" && (
                    <>
                      <label>
                        UOM
                        <input
                          value={attr.uom}
                          onChange={(e) =>
                            setAttr({ ...attr, uom: e.target.value })
                          }
                        />
                      </label>
                      <label>
                        Decimal Places
                        <input
                          type="number"
                          min="0"
                          max="6"
                          value={attr.precision_scale}
                          onChange={(e) =>
                            setAttr({
                              ...attr,
                              precision_scale: Number(e.target.value),
                            })
                          }
                        />
                      </label>
                    </>
                  )}
                  {attr.data_type === "CATEGORY" && (
                    <label className="wideField">
                      Allowed Values
                      <input
                        required
                        placeholder="Example: Red, Amber, Green"
                        value={attr.category_options}
                        onChange={(e) =>
                          setAttr({ ...attr, category_options: e.target.value })
                        }
                      />
                      <span className="hint">Separate values with commas.</span>
                    </label>
                  )}
                  <label>
                    Test Method
                    <input
                      value={attr.test_method}
                      onChange={(e) =>
                        setAttr({ ...attr, test_method: e.target.value })
                      }
                    />
                  </label>
                  <button className="primary">Add Attribute</button>
                </form>
                <DataGrid rows={visibleAttrs} searchText={(a) => `${a.group_name} ${a.attribute_code} ${a.attribute_name} ${a.data_type} ${a.uom || ""}`} sortOptions={[["Attribute code", (a) => a.attribute_code], ["Attribute name", (a) => a.attribute_name], ["Type", (a) => a.data_type], ["Status", (a) => a.active ? 0 : 1]]}>
                {(gridRows) =>
                <div className="tablewrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Group</th>
                        <th>Code</th>
                        <th>Quality Attribute</th>
                        <th>Type</th>
                        <th>Configuration</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {gridRows.map((a) => (
                        <tr key={a.id}>
                          <td>{a.group_name}</td>
                          <td>
                            <b>{a.attribute_code}</b>
                          </td>
                          <td>{a.attribute_name}</td>
                          <td>{a.data_type}</td>
                          <td>
                            {a.data_type === "NUMERIC"
                              ? a.uom || "No UOM"
                              : a.data_type === "CATEGORY"
                                ? a.category_options.join(", ")
                                : "Yes / No"}
                          </td>
                          <td>
                            <Badge>{a.active ? "ACTIVE" : "INACTIVE"}</Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {!attr.group_id && (
                    <div className="empty smallEmpty">
                      Select an attribute group to view its attributes.
                    </div>
                  )}
                  {attr.group_id && !gridRows.length && (
                    <div className="empty smallEmpty">
                      No attributes are available in this group.
                    </div>
                  )}
                </div>
                }
                </DataGrid>
              </section>
            </>
          )}
        </div>
      </div>
    </>
  );
}
function Detail({ r, act, tests, setTests, openTests, saveTests }: any) {
  const [comparisonOpen, setComparisonOpen] = useState(false),
    [comparisonTests, setComparisonTests] = useState<any[]>([]),
    [dispositionRemark, setDispositionRemark] = useState("");
  const sample = r.samples?.[0];
  const resultsLocked = sample?.sample_status !== "TESTING";
  const qualitySummary = r.quality_summary || { total: 0, pass: 0, fail: 0, pending: 0 };
  const allWithinSpecification = qualitySummary.total > 0 && qualitySummary.fail === 0 && qualitySummary.pending === 0;
  const hasDeviation = qualitySummary.fail > 0;
  return (
    <>
      <section className="hero">
        <div>
          <span className="eyebrow">{r.receipt_no}</span>
          <h2>
            {r.material.code} · {r.material.description}
          </h2>
          <p>
            {r.supplier.name} · Supplier Batch {r.supplier_batch_no}
          </p>
        </div>
        <div>
          <Badge>{r.status}</Badge> <Badge>{r.release_state}</Badge>
        </div>
      </section>
      <section className="detailgrid">
        <div className="panel">
          <h2>Batch Information</h2>
          <div className="kv">
            <span>
              Internal Batch<b>{r.internal_batch_no}</b>
            </span>
            <span>
              PO Number<b>{r.po_no}</b>
            </span>
            <span>
              GRN Number<b>{r.grn_no || "—"}</b>
            </span>
            <span>
              Quantity
              <b>
                {r.quantity} {r.uom}
              </b>
            </span>
            <span>
              Receipt Date<b>{new Date(r.receipt_datetime).toLocaleString()}</b>
            </span>
            <span>
              Specification<b>{r.specification.version}</b>
            </span>
            <span>
              Spec Validity
              <b>
                {new Date(r.specification.effective_from).toLocaleDateString()}{" "}
                – {new Date(r.specification.effective_to).toLocaleDateString()}
              </b>
            </span>
          </div>
        </div>
        <div className="panel">
          <h2>Workflow</h2>
          <div className="workflow">
            {r.status === "DRAFT" && (
              <button
                className="primary"
                onClick={() => act(`/receipts/${r.id}/submit`)}
              >
                Submit for Sampling
              </button>
            )}
            {r.status === "PENDING_SAMPLING" && (
              <button
                className="primary"
                onClick={() =>
                  act(`/receipts/${r.id}/samples`, "POST", {
                    sample_type: "INITIAL",
                    sampling_location: "Ferro Alloy Store",
                    sampling_method: "Composite",
                  })
                }
              >
                Create Sample
              </button>
            )}
            {sample?.sample_status === "CREATED" && (
              <button
                className="primary"
                onClick={() => act(`/samples/${sample.id}/collect`)}
              >
                Mark Sample Collected
              </button>
            )}
            {sample?.sample_status === "COLLECTED" && (
              <button
                className="primary"
                onClick={() => act(`/samples/${sample.id}/send-to-lab`)}
              >
                Send to Laboratory
              </button>
            )}
            {sample?.sample_status === "SENT_TO_LAB" && (
              <button
                className="primary"
                onClick={() => act(`/samples/${sample.id}/receive-at-lab`)}
              >
                Receive at Laboratory
              </button>
            )}
            {sample?.sample_status === "RECEIVED_AT_LAB" && (
              <button
                className="primary"
                onClick={() => act(`/samples/${sample.id}/start-testing`)}
              >
                Start Testing
              </button>
            )}
            {sample &&
              ["TESTING", "RESULTS_SUBMITTED", "RESULTS_APPROVED"].includes(
                sample.sample_status,
              ) && (
                <>
                  <button onClick={() => openTests(sample)}>
                    Open Laboratory Workbench
                  </button>
                  <button className="comparisonAction" onClick={async () => { const response = await fetch(API + `/samples/${sample.id}/required-tests`); if (response.ok) setComparisonTests(await response.json()); setComparisonOpen(true); }}>
                    Specification vs Actual
                  </button>
                </>
              )}
            {sample?.sample_status === "RESULTS_SUBMITTED" && (
              <button
                className="primary"
                onClick={() => act(`/samples/${sample.id}/results/approve`)}
              >
                Approve Lab Results
              </button>
            )}
            {r.status === "UNDER_REVIEW" && (
              <>
                <label className="dispositionRemark">
                  Disposition Remarks
                  <textarea value={dispositionRemark} onChange={(event) => setDispositionRemark(event.target.value)} placeholder="Enter the quality review remarks…" rows={3} />
                </label>
                <button
                  className="primary"
                  disabled={!allWithinSpecification}
                  title={!allWithinSpecification ? "Accept is available only when all quality results are within specification" : "Accept batch"}
                  onClick={() =>
                    act(`/receipts/${r.id}/disposition`, "POST", {
                      disposition: "ACCEPTED",
                      reason_text: dispositionRemark.trim() || null,
                    })
                  }
                >
                  Accept Batch
                </button>
                <button
                  className="deviationAction"
                  disabled={!hasDeviation || !dispositionRemark.trim()}
                  title={!hasDeviation ? "Available only when one or more results are outside specification" : !dispositionRemark.trim() ? "Enter disposition remarks" : "Accept with deviation"}
                  onClick={() =>
                      act(`/receipts/${r.id}/disposition`, "POST", {
                        disposition: "ACCEPTED_WITH_DEVIATION",
                        reason_text: dispositionRemark.trim(),
                      })}
                >
                  Accept with Deviation
                </button>
                <button
                  className="rejectAction"
                  disabled={!hasDeviation || !dispositionRemark.trim()}
                  title={!hasDeviation ? "Reject is available only when one or more results are outside specification" : !dispositionRemark.trim() ? "Enter disposition remarks" : "Reject batch"}
                  onClick={() =>
                      act(`/receipts/${r.id}/disposition`, "POST", {
                        disposition: "REJECTED",
                        reason_text: dispositionRemark.trim(),
                      })}
                >
                  Reject
                </button>
              </>
            )}
          </div>
          {r.status === "UNDER_REVIEW" && <div className={hasDeviation ? "dispositionRule deviation" : "dispositionRule pass"}>{hasDeviation ? `${qualitySummary.fail} result${qualitySummary.fail === 1 ? " is" : "s are"} outside specification. Accept with Deviation or Reject is available after entering remarks.` : allWithinSpecification ? "All quality results are within specification. Accept Batch is available." : "Disposition is unavailable until all mandatory approved results are complete."}</div>}
          {sample && (
            <p className="muted">
              Sample: <b>{sample.sample_no}</b> · {sample.sample_status}
            </p>
          )}
        </div>
      </section>
      <section className="panel">
        <h2>
          Locked Applicable Quality Specification{" "}
          <small>{r.specification.version}</small>
        </h2>
        <DataGrid rows={r.specification.attributes} searchText={(a) => `${a.code} ${a.name} ${a.data_type || ""} ${a.uom || ""}`} sortOptions={[["Attribute", (a) => a.name], ["Code", (a) => a.code], ["Type", (a) => a.data_type || ""]]}>
        {(gridRows) => <div className="tablewrap">
        <table>
          <thead>
            <tr>
              <th>Attribute</th>
              <th>Unit</th>
              <th>Minimum</th>
              <th>Aim</th>
              <th>Maximum</th>
            </tr>
          </thead>
          <tbody>
            {gridRows.map((a: any) => (
              <tr key={a.id}>
                <td>
                  {a.code} · {a.name}
                </td>
                <td>{a.uom}</td>
                <td>{a.lsl ?? "—"}</td>
                <td>{a.aim_value ?? a.target_value ?? "—"}</td>
                <td>{a.usl ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>}
        </DataGrid>
      </section>
      {comparisonOpen && sample && (
        <div className="modalBackdrop" onClick={() => setComparisonOpen(false)}>
          <div className="specModal comparisonModal" onClick={(event) => event.stopPropagation()}>
            <div className="panelTitle">
              <div><span className="eyebrow">QUALITY RESULT COMPARISON</span><h2>Specification vs Actual</h2><p className="muted">{r.receipt_no} · {sample.sample_no} · Specification {r.specification.version}</p></div>
              <button type="button" onClick={() => setComparisonOpen(false)}>×</button>
            </div>
            <div className="comparisonLegend"><span><i className="comparisonDot pass"/>Within specification</span><span><i className="comparisonDot fail"/>Deviation</span><span><i className="comparisonDot pending"/>Result pending</span></div>
            <div className="tablewrap"><table className="comparisonTable"><thead><tr><th>Attribute</th><th>Unit</th><th>Minimum</th><th>Aim / Required</th><th>Maximum</th><th>Actual</th><th>Evaluation</th></tr></thead><tbody>{comparisonTests.map((test: any) => <tr className={test.evaluation === "FAIL" ? "comparisonFail" : test.evaluation === "PASS" ? "comparisonPass" : "comparisonPending"} key={test.specification_attribute_id}><td><b>{test.code}</b><br/><small>{test.name}</small></td><td>{test.uom || "—"}</td><td>{test.lsl ?? "—"}</td><td>{test.aim_value ?? test.target_value ?? "—"}</td><td>{test.usl ?? "—"}</td><td className="actualValue">{test.result ?? "Pending"}</td><td><Badge>{test.evaluation}</Badge></td></tr>)}</tbody></table>{!comparisonTests.length && <div className="empty">No quality attributes are available for comparison.</div>}</div>
            <div className="actions"><button type="button" onClick={() => setComparisonOpen(false)}>Close</button></div>
          </div>
        </div>
      )}
      {tests.length > 0 && sample && (
        <section className="panel lab">
          <div className="panelTitle">
            <div>
              <h2>Laboratory Result Entry</h2>
              <p className="muted">
                {sample.sample_no} · Validation uses the specification locked at
                material receipt.
              </p>
              {resultsLocked && (
                <p className="resultLockNotice">
                  Results are locked because laboratory testing has been completed.
                </p>
              )}
            </div>
          </div>
          <DataGrid rows={tests} searchText={(t) => `${t.code} ${t.name} ${t.data_type} ${t.evaluation} ${t.result ?? ""}`} sortOptions={[["Attribute", (t) => t.name], ["Code", (t) => t.code], ["Evaluation", (t) => t.evaluation], ["Type", (t) => t.data_type]]}>
          {(gridRows) => <div className="tablewrap">
          <table>
            <thead>
              <tr>
                <th>Attribute</th>
                <th>Specification</th>
                <th>Result</th>
                <th>Evaluation</th>
              </tr>
            </thead>
            <tbody>
              {gridRows.map((t: any) => (
                <tr key={t.specification_attribute_id}>
                  <td>
                    <b>{t.code}</b> · {t.name}
                  </td>
                  <td>
                    {t.lsl ?? "—"} / Aim {t.aim_value ?? "—"} / {t.usl ?? "—"}{" "}
                    {t.uom}
                  </td>
                  <td>
                    {t.data_type === "BOOLEAN" ? (
                      <select
                        disabled={resultsLocked}
                        value={t.result ?? ""}
                        onChange={(e) => {
                          setTests(tests.map((item: any) => item.specification_attribute_id === t.specification_attribute_id ? { ...item, result: e.target.value } : item));
                        }}
                      >
                        <option value="">Select result</option>
                        <option value="YES">Yes</option>
                        <option value="NO">No</option>
                      </select>
                    ) : t.data_type === "CATEGORY" ? (
                      <select
                        disabled={resultsLocked}
                        value={t.result ?? ""}
                        onChange={(e) => {
                          setTests(tests.map((item: any) => item.specification_attribute_id === t.specification_attribute_id ? { ...item, result: e.target.value } : item));
                        }}
                      >
                        <option value="">Select result</option>
                        {t.category_options.map((option: string) => (
                          <option key={option}>{option}</option>
                        ))}
                      </select>
                    ) : (
                      <input
                        disabled={resultsLocked}
                        type="number"
                        step="any"
                        value={t.result ?? ""}
                        onChange={(e) => {
                          setTests(tests.map((item: any) => item.specification_attribute_id === t.specification_attribute_id ? { ...item, result: e.target.value } : item));
                        }}
                      />
                    )}{" "}
                    {t.uom}
                  </td>
                  <td>
                    <Badge>{t.evaluation}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>}
          </DataGrid>
          <div className="actions">
            {!resultsLocked && (
              <button onClick={() => saveTests(sample.id)}>Save Draft</button>
            )}
            {sample.sample_status === "TESTING" && (
              <button
                className="primary"
                onClick={async () => {
                  await saveTests(sample.id);
                  await act(`/samples/${sample.id}/results/submit`);
                }}
              >
                Submit Results
              </button>
            )}
          </div>
        </section>
      )}
    </>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
