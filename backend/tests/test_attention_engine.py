import unittest
from types import SimpleNamespace

from app.attention.engine import discrete_signals, numeric_signals, resolve_reference, select_observations


class AttentionEngineTests(unittest.TestCase):
    def config(self, **overrides):
        values={"near_spec_margin_value":10,"near_spec_margin_type":"PERCENT_TOLERANCE","baseline_window_n":30,"min_baseline_n":3,"discrete_json":'{"consecutive_n":3,"rate_window_n":10,"warning_rate":0.2,"critical_rate":0.4}'}
        values.update(overrides); return SimpleNamespace(**values)

    def observation(self, result_id, reference, value, data_type="NUMERIC", time=1, target=None):
        return {"result_id":result_id,"supplier_id":"s","material_id":"m","attribute_id":"a","reference_id":reference,"value":value,"data_type":data_type,"time":time,"target":target,"lsl":0,"usl":10,"aim":5}

    def test_reference_fallback_never_merges_blank_primary(self):
        receipt=SimpleNamespace(supplier_batch_no="",internal_batch_no="IB-1",receipt_no="R-1")
        value, fields=resolve_reference(receipt,["supplier_batch_no"],["internal_batch_no","receipt_no"])
        self.assertEqual("IB-1",value); self.assertEqual(["internal_batch_no"],fields)

    def test_latest_per_reference_is_deterministic(self):
        first=self.observation("1","B1",1,time=1); latest=self.observation("2","B1",2,time=2)
        selected,audit=select_observations([latest,first],"LATEST_PER_REFERENCE")
        self.assertEqual(["2"],[x["result_id"] for x in selected]); self.assertEqual(1,sum(x["used"] for x in audit))

    def test_spec_failure_is_independent_of_statistical_baseline(self):
        signals,stats=numeric_signals([self.observation("1","B1",11)],self.config(min_baseline_n=20))
        self.assertIn("SPEC_FAIL",[x[0] for x in signals]); self.assertIsNone(stats)

    def test_we1_fires_only_with_sufficient_numeric_history(self):
        history=[self.observation(str(i),str(i),v,time=i) for i,v in enumerate([4,5,6,10],1)]
        signals,stats=numeric_signals(history,self.config())
        self.assertIn("WE1",[x[0] for x in signals]); self.assertEqual(3,stats["n"])

    def test_boolean_uses_discrete_rules(self):
        history=[self.observation(str(i),str(i),"YES","BOOLEAN",i,"NO") for i in range(1,4)]
        signals,_=discrete_signals(history,self.config())
        self.assertIn("DISCRETE_SPEC_FAIL",[x[0] for x in signals]); self.assertIn("CONSECUTIVE_ADVERSE",[x[0] for x in signals])


if __name__ == "__main__": unittest.main()
