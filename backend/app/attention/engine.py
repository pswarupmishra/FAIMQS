import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime
from statistics import mean, median, pstdev

from sqlalchemy.orm import joinedload

from ..models import (
    AttentionEngineConfig, AttentionEvent, AttentionRunLog, Material, QualityAttribute,
    Receipt, Sample, SpecificationAttribute, Supplier, TestResult,
)

SEVERITY_RANK = {"NORMAL": 0, "WATCH": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
REFERENCE_FIELDS = ["supplier_batch_no", "internal_batch_no", "receipt_no", "grn_no", "po_no", "vehicle_no", "plant_code", "sms_code", "store_code"]


def config_dict(config):
    return {
        "id": config.id, "config_name": config.config_name, "enabled": config.enabled,
        "test_selection_mode": config.test_selection_mode,
        "numeric_aggregate_method": config.numeric_aggregate_method,
        "baseline_window_n": config.baseline_window_n, "min_baseline_n": config.min_baseline_n,
        "near_spec_margin_type": config.near_spec_margin_type,
        "near_spec_margin_value": float(config.near_spec_margin_value),
        "reference_fields": json.loads(config.reference_fields_json),
        "fallback_fields": json.loads(config.fallback_fields_json),
        "include_sample_types": json.loads(config.include_sample_types_json),
        "include_result_statuses": json.loads(config.include_result_statuses_json),
        "rules": json.loads(config.rules_json), "discrete": json.loads(config.discrete_json),
        "version": config.version, "updated_at": config.updated_at,
    }


def get_config(db):
    config = db.query(AttentionEngineConfig).order_by(AttentionEngineConfig.version.desc()).first()
    if not config:
        config = AttentionEngineConfig()
        db.add(config); db.commit(); db.refresh(config)
    return config


def resolve_reference(receipt, primary, fallback):
    parts = [str(getattr(receipt, field, "") or "").strip() for field in primary]
    if parts and all(parts):
        return " | ".join(parts), primary
    for field in fallback:
        value = str(getattr(receipt, field, "") or "").strip()
        if value:
            return value, [field]
    return receipt.receipt_no, ["receipt_no"]


def build_observations(db, config):
    cfg = config_dict(config)
    rows = (db.query(TestResult)
        .options(joinedload(TestResult.specification_attribute).joinedload(SpecificationAttribute.attribute))
        .join(Sample, TestResult.sample_id == Sample.id)
        .join(Receipt, Sample.receipt_id == Receipt.id)
        .filter(Sample.sample_type.in_(cfg["include_sample_types"]), TestResult.result_status.in_(cfg["include_result_statuses"]))
        .all())
    observations = []
    for result in rows:
        sample = db.get(Sample, result.sample_id); receipt = db.get(Receipt, sample.receipt_id)
        spec_attr = result.specification_attribute; attribute = spec_attr.attribute
        reference, reference_fields = resolve_reference(receipt, cfg["reference_fields"], cfg["fallback_fields"])
        value = float(result.numeric_result) if attribute.data_type == "NUMERIC" and result.numeric_result is not None else result.text_result
        if value is None: continue
        observations.append({
            "result_id": result.id, "sample_id": sample.id, "receipt_id": receipt.id,
            "specification_id": receipt.specification_id, "supplier_id": receipt.supplier_id,
            "material_id": receipt.material_id, "attribute_id": attribute.id,
            "data_type": attribute.data_type, "value": value, "reference_id": reference,
            "reference_fields": reference_fields,
            "time": result.entered_at or sample.sample_datetime or receipt.receipt_datetime,
            "lsl": float(spec_attr.lsl) if spec_attr.lsl is not None else None,
            "usl": float(spec_attr.usl) if spec_attr.usl is not None else None,
            "aim": float(spec_attr.aim_value) if spec_attr.aim_value is not None else None,
            "target": spec_attr.target_value, "sample_type": sample.sample_type,
        })
    return rows, observations


def select_observations(observations, mode, aggregate_method="MEAN"):
    groups = defaultdict(list)
    for item in observations:
        groups[(item["supplier_id"], item["material_id"], item["attribute_id"], item["reference_id"])].append(item)
    selected, audit = [], []
    for values in groups.values():
        values.sort(key=lambda x: (x["time"], x["result_id"]))
        if mode == "ALL_TESTS": used = values
        elif mode == "FIRST_PER_REFERENCE": used = [values[0]]
        elif mode == "AGGREGATE_PER_REFERENCE" and values[0]["data_type"] == "NUMERIC":
            agg = {"MEAN": mean, "MEDIAN": median, "MIN": min, "MAX": max}.get(aggregate_method, mean)
            merged = dict(values[-1]); merged["value"] = agg([x["value"] for x in values]); merged["source_result_ids"] = [x["result_id"] for x in values]
            used = [merged]
        else: used = [values[-1]]
        used_ids = {x["result_id"] for x in used}
        selected.extend(used)
        for item in values:
            audit.append({**item, "used": item["result_id"] in used_ids, "reason": "Selected by policy" if item["result_id"] in used_ids else f"Excluded by {mode}"})
    return selected, audit


def numeric_signals(history, config):
    current = history[-1]; value = current["value"]; signals = []
    if (current["lsl"] is not None and value < current["lsl"]) or (current["usl"] is not None and value > current["usl"]):
        signals.append(("SPEC_FAIL", "CRITICAL", "Result is outside the specification limits", {}))
    tolerance = (current["usl"] - current["lsl"]) if current["usl"] is not None and current["lsl"] is not None else None
    margin = tolerance * float(config.near_spec_margin_value) / 100 if tolerance and config.near_spec_margin_type == "PERCENT_TOLERANCE" else float(config.near_spec_margin_value)
    if margin and ((current["lsl"] is not None and value <= current["lsl"] + margin) or (current["usl"] is not None and value >= current["usl"] - margin)):
        signals.append(("NEAR_SPEC", "WATCH", "Result is inside the configured near-specification margin", {"margin": margin}))
    baseline = history[max(0, len(history)-config.baseline_window_n-1):-1]
    values = [x["value"] for x in baseline]
    if len(values) < config.min_baseline_n: return signals, None
    center, sigma = mean(values), pstdev(values)
    stats = {"mean": center, "sigma": sigma, "n": len(values)}
    if sigma <= 0: return signals, stats
    z = [(x["value"]-center)/sigma for x in history]
    if abs(z[-1]) > 3: signals.append(("WE1", "CRITICAL", "One point is beyond 3 sigma", {"z_scores":z[-1:]}))
    if len(z)>=3 and (sum(v>2 for v in z[-3:])>=2 or sum(v<-2 for v in z[-3:])>=2): signals.append(("WE2", "HIGH", "Two of three points are beyond 2 sigma on the same side", {"z_scores":z[-3:]}))
    if len(z)>=5 and (sum(v>1 for v in z[-5:])>=4 or sum(v<-1 for v in z[-5:])>=4): signals.append(("WE3", "MEDIUM", "Four of five points are beyond 1 sigma on the same side", {"z_scores":z[-5:]}))
    if len(z)>=8 and (all(v>0 for v in z[-8:]) or all(v<0 for v in z[-8:])): signals.append(("WE4", "MEDIUM", "Eight consecutive points are on one side of the centre line", {"z_scores":z[-8:]}))
    return signals, stats


def discrete_signals(history, config):
    current = history[-1]; observed = str(current["value"]); adverse = observed != str(current["target"])
    signals = []
    if adverse: signals.append(("DISCRETE_SPEC_FAIL", "CRITICAL", f"Observed state {observed} differs from required state {current['target']}", {}))
    params = json.loads(config.discrete_json); recent = history[-params["consecutive_n"]:]
    if len(recent) == params["consecutive_n"] and all(str(x["value"]) != str(x["target"]) for x in recent):
        signals.append(("CONSECUTIVE_ADVERSE", "HIGH", f"{len(recent)} consecutive references are adverse", {"references":[x["reference_id"] for x in recent]}))
    window = history[-params["rate_window_n"]:]; rate = sum(str(x["value"]) != str(x["target"]) for x in window)/len(window)
    if len(window)>=3 and rate >= params["critical_rate"]: signals.append(("ADVERSE_RATE", "HIGH", f"Adverse rate is {rate:.0%} over {len(window)} references", {"rate":rate,"n":len(window)}))
    elif len(window)>=3 and rate >= params["warning_rate"]: signals.append(("ADVERSE_RATE", "WATCH", f"Adverse rate is {rate:.0%} over {len(window)} references", {"rate":rate,"n":len(window)}))
    return signals, None


def evaluate(db):
    config = get_config(db); run = AttentionRunLog(config_version=config.version); db.add(run); db.flush()
    try:
        if not config.enabled:
            run.status="COMPLETED"; run.completed_at=datetime.utcnow(); db.commit()
            return {"run_id":run.id,"records_scanned":0,"observations_used":0,"events_created":0,"consolidation_audit":[],"message":"Attention Engine is disabled"}
        raw_rows, observations = build_observations(db, config)
        selected, audit = select_observations(observations, config.test_selection_mode, config.numeric_aggregate_method)
        partitions = defaultdict(list)
        for item in selected: partitions[(item["supplier_id"],item["material_id"],item["attribute_id"])].append(item)
        created = 0; enabled = json.loads(config.rules_json)
        for history in partitions.values():
            history.sort(key=lambda x:(x["time"],x["result_id"]))
            for index in range(len(history)):
                series = history[:index+1]; current=series[-1]
                signals, stats = numeric_signals(series, config) if current["data_type"]=="NUMERIC" else discrete_signals(series, config)
                for rule,severity,message,evidence in signals:
                    if not enabled.get(rule, True): continue
                    source_ids=current.get("source_result_ids",[current["result_id"]])
                    fingerprint=hashlib.sha256(f"{config.version}|{rule}|{current['supplier_id']}|{current['material_id']}|{current['attribute_id']}|{current['reference_id']}|{'|'.join(source_ids)}".encode()).hexdigest()
                    if db.query(AttentionEvent).filter_by(fingerprint=fingerprint).first(): continue
                    evidence.update({"reference_fields":current["reference_fields"],"source_result_ids":source_ids,"test_selection_mode":config.test_selection_mode})
                    event=AttentionEvent(fingerprint=fingerprint,event_time=current["time"],supplier_id=current["supplier_id"],material_id=current["material_id"],attribute_id=current["attribute_id"],reference_id=current["reference_id"],receipt_id=current["receipt_id"],sample_id=current["sample_id"],test_result_id=current["result_id"],specification_id=current["specification_id"],rule_code=rule,severity=severity,observed_value=str(current["value"]),message=message,lsl=current["lsl"],usl=current["usl"],target_value=current["target"],baseline_mean=stats["mean"] if stats else None,baseline_sigma=stats["sigma"] if stats else None,baseline_n=stats["n"] if stats else len(series)-1,config_version=config.version,rule_evidence_json=json.dumps(evidence))
                    db.add(event); created += 1
        run.status="COMPLETED"; run.completed_at=datetime.utcnow(); run.records_scanned=len(raw_rows); run.observations_used=len(selected); run.events_created=created
        db.commit(); return {"run_id":run.id,"records_scanned":len(raw_rows),"observations_used":len(selected),"events_created":created,"consolidation_audit":audit}
    except Exception as exc:
        run.status="FAILED"; run.completed_at=datetime.utcnow(); run.error_text=str(exc); db.commit(); raise
