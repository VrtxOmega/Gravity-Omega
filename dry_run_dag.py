import json
import sys
import os
from pathlib import Path

# Add backend directory to sys.path
sys.path.append(os.path.abspath('backend'))
sys.path.append(os.path.abspath('backend/modules'))

from modules.workflow_engine import WorkflowPipeline, WorkflowStep

class MockRegistry:
    def get(self, module_id):
        class MockModule:
            def execute(self, args):
                if "GOLIATH" in module_id:
                    out = "Found target facilities in Wood River: PFHxS at 13ppt."
                elif "edge_audit" in module_id:
                    out = '{"pfhxs": 13.0}'
                elif "alpha" in module_id:
                    out = "[SEALED] Mathematical deviation identified. True value > Public Threshold."
                else:
                    out = "Generated Dossier."
                return out, "", 0
        return MockModule()

class MockQueue:
    def put(self, dict_event):
        try:
            if dict_event.get("type") == "step_status":
                print(f"[{dict_event.get('status')}] {dict_event.get('label')}")
        except:
            pass

class MockLLM:
    def __init__(self):
        pass
    def query(self, sys, user):
        return f"[MOCK_SUMMARY] Data processed.", "mock", ""

if __name__ == "__main__":
    dag_path = Path("backend/dags/madison_pfas_strike.json")
    dag_def = json.loads(dag_path.read_text())
    
    steps = [WorkflowStep(**s) for s in dag_def["steps"]]
    
    pipeline = WorkflowPipeline(
        steps=steps,
        registry=MockRegistry(),
        security=None,
        llm=MockLLM(),
        queue=MockQueue(),
        request_id="dry_run_testing_123"
    )
    
    print("========================================")
    print(f"EXECUTING KILL-CHAIN DAG: {dag_def['name']}")
    print("========================================")
    result = pipeline.execute()
    
    print("\n--- CHAIN COMPLETE ---")
    print(f"Verdict: {result['final_verdict']}")
    print(f"Seal Hash: {result.get('seal_hash', 'N/A')}")
