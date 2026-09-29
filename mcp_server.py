"""MCP JSON-RPC stdio server for genpark-agent-execution-tree-rollback-checkpointer-skill."""
import sys
import json
from client import ExecutionTreeRollbackCheckpointer

checkpointer = ExecutionTreeRollbackCheckpointer()

def handle_call_tool(params):
    name = params.get("name")
    args = params.get("arguments", {})
    if name != "manage_execution_tree":
        return {"error": f"Unknown tool '{name}'"}
        
    action = args.get("action")
    if action == "snapshot":
        return checkpointer.snapshot_checkpoint(
            state=args.get("state_payload", {}),
            parent_id=args.get("parent_id")
        )
    elif action == "rollback":
        return checkpointer.rollback_checkpoint(
            target_node_id=args.get("node_id")
        )
    elif action == "evaluate_branch":
        return checkpointer.evaluate_branch(
            node_id=args.get("node_id", checkpointer.current_node_id),
            metrics=args.get("branch_metrics", {})
        )
    elif action == "prune_dead_ends":
        return checkpointer.prune_dead_ends(
            node_id=args.get("node_id", checkpointer.current_node_id)
        )
    elif action == "get_tree":
        return checkpointer.get_tree_summary()
    else:
        return {"error": f"Unknown action '{action}'"}

def main():
    if "--test" in sys.argv:
        print("[TEST] Running self-test for ExecutionTreeRollbackCheckpointer...")
        s1 = checkpointer.snapshot_checkpoint({"step": 1, "action": "scrape_page"})
        node1 = s1["node_id"]
        checkpointer.evaluate_branch(node1, {"errors_encountered": 0, "confidence_score": 0.95})
        s2 = checkpointer.snapshot_checkpoint({"step": 2, "action": "failed_extract"})
        node2 = s2["node_id"]
        eval2 = checkpointer.evaluate_branch(node2, {"errors_encountered": 4, "confidence_score": 0.1})
        assert eval2["recommendation"] == "prune_and_rollback"
        checkpointer.prune_dead_ends(node2)
        assert checkpointer.current_node_id == node1
        print(f"[TEST] Success! Current node: {checkpointer.current_node_id}")
        return

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            method = req.get("method")
            msg_id = req.get("id")
            
            if method == "tools/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": [
                            {
                                "name": "manage_execution_tree",
                                "description": "Manage agent execution tree checkpoints, state rollbacks, branch viability evaluations, and dead-end pruning.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "action": {"type": "string", "enum": ["snapshot", "rollback", "evaluate_branch", "prune_dead_ends", "get_tree"]},
                                        "node_id": {"type": "string"},
                                        "parent_id": {"type": "string"},
                                        "state_payload": {"type": "object"},
                                        "branch_metrics": {"type": "object"}
                                    },
                                    "required": ["action"]
                                }
                            }
                        ]
                    }
                }
            elif method == "tools/call":
                res = handle_call_tool(req.get("params", {}))
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}
                }
            else:
                resp = {"jsonrpc": "2.0", "id": msg_id, "result": {}}
            print(json.dumps(resp), flush=True)
        except Exception as e:
            err_resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": str(e)}}
            print(json.dumps(err_resp), flush=True)

if __name__ == "__main__":
    main()
