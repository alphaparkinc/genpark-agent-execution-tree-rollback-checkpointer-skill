"""Client module for ExecutionTreeRollbackCheckpointer (100% Python Standard Library)."""
import json
import time
import uuid
import copy
from typing import Dict, Any, List, Optional

class ExecutionTreeRollbackCheckpointer:
    """Manages an in-memory Tree-of-Thoughts execution graph with state snapshotting,
    branch evaluation, backtracking rollback, and pruning of failed trajectories."""
    
    def __init__(self, root_state: Optional[Dict[str, Any]] = None):
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.root_id = "root"
        self.current_node_id = self.root_id
        
        # Initialize root node
        self.nodes[self.root_id] = {
            "node_id": self.root_id,
            "parent_id": None,
            "children": [],
            "timestamp": time.time(),
            "state": copy.deepcopy(root_state or {"step": 0, "plan": [], "scratchpad": "", "variables": {}}),
            "status": "active",
            "viability_score": 1.0,
            "is_pruned": False,
            "error_count": 0
        }

    def snapshot_checkpoint(self, state: Dict[str, Any], parent_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Creates a snapshot node branching from parent_id (or current_node_id)."""
        pid = parent_id if parent_id and parent_id in self.nodes else self.current_node_id
        new_node_id = f"node_{uuid.uuid4().hex[:8]}"
        
        node_record = {
            "node_id": new_node_id,
            "parent_id": pid,
            "children": [],
            "timestamp": time.time(),
            "state": copy.deepcopy(state),
            "metadata": metadata or {},
            "status": "active",
            "viability_score": 1.0,
            "is_pruned": False,
            "error_count": 0
        }
        
        self.nodes[new_node_id] = node_record
        self.nodes[pid]["children"].append(new_node_id)
        self.current_node_id = new_node_id
        
        return {
            "status": "success",
            "action": "snapshot",
            "node_id": new_node_id,
            "parent_id": pid,
            "depth": self._get_depth(new_node_id),
            "active_node": self.current_node_id
        }

    def rollback_checkpoint(self, target_node_id: Optional[str] = None) -> Dict[str, Any]:
        """Rolls back the active execution pointer to a designated target node or the immediate parent."""
        if not target_node_id:
            curr = self.nodes.get(self.current_node_id)
            target_node_id = curr.get("parent_id") if curr else self.root_id
            
        if target_node_id not in self.nodes:
            return {"status": "error", "message": f"Target node '{target_node_id}' does not exist in execution tree."}
            
        target = self.nodes[target_node_id]
        if target["is_pruned"]:
            return {"status": "error", "message": f"Cannot rollback to pruned node '{target_node_id}'."}
            
        previous_node = self.current_node_id
        self.current_node_id = target_node_id
        
        return {
            "status": "success",
            "action": "rollback",
            "previous_node": previous_node,
            "restored_node": target_node_id,
            "restored_state": copy.deepcopy(target["state"]),
            "depth": self._get_depth(target_node_id)
        }

    def evaluate_branch(self, node_id: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates branch viability based on heuristic error counts and confidence score."""
        if node_id not in self.nodes:
            return {"status": "error", "message": f"Node '{node_id}' not found."}
            
        node = self.nodes[node_id]
        error_count = metrics.get("errors_encountered", 0)
        confidence = float(metrics.get("confidence_score", 0.8))
        progress = float(metrics.get("progress_metric", 0.5))
        
        # Penalize errors, reward confidence & progress
        penalty = min(0.9, error_count * 0.25)
        viability = max(0.0, (confidence * 0.6 + progress * 0.4) - penalty)
        
        node["error_count"] = error_count
        node["viability_score"] = round(viability, 3)
        
        recommendation = "continue"
        if viability < 0.35:
            recommendation = "prune_and_rollback"
        elif viability < 0.6:
            recommendation = "caution_retry"
            
        return {
            "status": "success",
            "node_id": node_id,
            "viability_score": node["viability_score"],
            "recommendation": recommendation,
            "is_viable": viability >= 0.35
        }

    def prune_dead_ends(self, node_id: str) -> Dict[str, Any]:
        """Marks a subtree as dead-end and prunes it from future traversal."""
        if node_id not in self.nodes:
            return {"status": "error", "message": f"Node '{node_id}' not found."}
            
        pruned_nodes = []
        def _prune_recursive(nid: str):
            self.nodes[nid]["is_pruned"] = True
            self.nodes[nid]["status"] = "pruned_dead_end"
            pruned_nodes.append(nid)
            for child in self.nodes[nid]["children"]:
                _prune_recursive(child)
                
        _prune_recursive(node_id)
        
        # If current active node was in pruned tree, rollback to nearest healthy ancestor
        if self.current_node_id in pruned_nodes:
            parent = self.nodes[node_id].get("parent_id") or self.root_id
            self.current_node_id = parent
            
        return {
            "status": "success",
            "action": "prune_dead_ends",
            "pruned_count": len(pruned_nodes),
            "pruned_nodes": pruned_nodes,
            "current_active_node": self.current_node_id
        }

    def get_tree_summary(self) -> Dict[str, Any]:
        """Returns the current state and structure of the execution tree."""
        return {
            "status": "success",
            "total_nodes": len(self.nodes),
            "active_node": self.current_node_id,
            "tree_structure": {
                nid: {
                    "parent": n["parent_id"],
                    "children": n["children"],
                    "viability": n["viability_score"],
                    "is_pruned": n["is_pruned"]
                }
                for nid, n in self.nodes.items()
            }
        }

    def _get_depth(self, node_id: str) -> int:
        depth = 0
        curr = node_id
        while curr and self.nodes.get(curr, {}).get("parent_id"):
            curr = self.nodes[curr]["parent_id"]
            depth += 1
        return depth
