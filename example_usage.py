"""Example usage for ExecutionTreeRollbackCheckpointer."""
import json
from client import ExecutionTreeRollbackCheckpointer

def main():
    print("=== Execution Tree Rollback Checkpointer Demo ===")
    chk = ExecutionTreeRollbackCheckpointer({"goal": "Analyze financial report", "step": 0})
    
    # 1. Take Snapshot Step 1
    s1 = chk.snapshot_checkpoint({"step": 1, "tool": "fetch_pdf", "status": "ok"})
    print("Snapshot 1:", s1)
    
    # 2. Take Snapshot Step 2 (bad branch)
    s2 = chk.snapshot_checkpoint({"step": 2, "tool": "parse_ocr_corrupted", "status": "syntax_error"})
    print("Snapshot 2:", s2)
    
    # 3. Evaluate Step 2
    eval_res = chk.evaluate_branch(s2["node_id"], {"errors_encountered": 3, "confidence_score": 0.2})
    print("Branch Evaluation:", eval_res)
    
    # 4. Prune dead-end and rollback
    prune_res = chk.prune_dead_ends(s2["node_id"])
    print("Pruned & Backtracked:", prune_res)
    
    # 5. Branch new healthy step from Step 1
    s3 = chk.snapshot_checkpoint({"step": 2, "tool": "parse_native_text", "status": "ok"})
    print("New Healthy Branch:", s3)
    
    # 6. Tree Summary
    summary = chk.get_tree_summary()
    print("Final Execution Tree Summary:", json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
