# -*- coding: utf-8 -*-
"""
ASCET Context Provider - Gathers comprehensive context for LLM
Combines code, diagram info, and metadata in a single call
"""

import sys
import json
from typing import Dict, Optional


class ContextProvider:
    """Provides rich context about ASCET classes for LLM interaction"""
    
    def __init__(self, version: str = "6.1.4"):
        self.version = version
    
    def gather_context(self, class_path: str) -> Dict:
        """
        Gather comprehensive context for a class.
        Returns dict with: code, calc_method, diagram_info, metadata
        """
        context = {
            "class_path": class_path,
            "version": self.version,
            "code": {},
            "diagram": {},
            "metadata": {}
        }
        
        try:
            # Try to get calc code
            self._gather_code_context(class_path, context)
        except Exception as e:
            print(f"[Context] Warning getting code: {e}", file=sys.stderr)
        
        try:
            # Try to get diagram info
            self._gather_diagram_context(class_path, context)
        except Exception as e:
            print(f"[Context] Warning getting diagram: {e}", file=sys.stderr)
        
        try:
            # Gather metadata
            self._gather_metadata(class_path, context)
        except Exception as e:
            print(f"[Context] Warning getting metadata: {e}", file=sys.stderr)
        
        return context
    
    def _gather_code_context(self, class_path: str, context: Dict):
        """Extract ESDL code and calc method information"""
        try:
            from src.ascet.connection import ASCETConnectionAPI
            
            scanner = ASCETConnectionAPI(version=self.version)
            if scanner.connect():
                code_data = scanner.extract_calc_code(class_path)
                context["code"] = {
                    "path": class_path,
                    "calc_method": code_data.get("code", ""),
                    "language": "esdl"
                }
                scanner.disconnect()
                print(f"[Context] Code context gathered for {class_path}", file=sys.stderr)
        except ImportError:
            print(f"[Context] ASCETConnectionAPI not available", file=sys.stderr)
        except Exception as e:
            print(f"[Context] Error gathering code: {e}", file=sys.stderr)
    
    def _gather_diagram_context(self, class_path: str, context: Dict):
        """Extract diagram structure and block information"""
        try:
            from src.diagrams.netlist import DiagramNetlistExtractor
            
            try:
                connections, oid_map = DiagramNetlistExtractor.extract_connections(class_path)
                diagram_data = DiagramNetlistExtractor.to_diagram_data(connections, oid_map)
                
                context["diagram"] = {
                    "path": class_path,
                    "blocks": len(diagram_data.get("blocks", [])),
                    "connections": len(connections),
                    "structure": diagram_data
                }
                print(f"[Context] Diagram context gathered: {len(connections)} connections", file=sys.stderr)
            except FileNotFoundError:
                print(f"[Context] No diagram file found for {class_path}", file=sys.stderr)
        except ImportError:
            print(f"[Context] DiagramNetlistExtractor not available", file=sys.stderr)
        except Exception as e:
            print(f"[Context] Error gathering diagram: {e}", file=sys.stderr)
    
    def _gather_metadata(self, class_path: str, context: Dict):
        """Gather class metadata and attributes"""
        try:
            parts = class_path.split("/")
            context["metadata"] = {
                "class_name": parts[-1] if parts else "",
                "folder_path": "/".join(parts[:-1]) if len(parts) > 1 else "",
                "depth": len(parts),
                "module_type": self._infer_module_type(class_path)
            }
        except Exception as e:
            print(f"[Context] Error gathering metadata: {e}", file=sys.stderr)
    
    def _infer_module_type(self, class_path: str) -> str:
        """Infer the module type from path patterns"""
        path_lower = class_path.lower()
        
        if any(x in path_lower for x in ["arbitrator", "error", "check"]):
            return "error_handler"
        elif any(x in path_lower for x in ["state", "machine", "flow"]):
            return "state_machine"
        elif any(x in path_lower for x in ["calc", "algorithm", "compute"]):
            return "calculator"
        elif any(x in path_lower for x in ["filter", "process", "pipeline"]):
            return "data_processor"
        else:
            return "utility"
    
    def estimate_token_count(self, context: Dict) -> int:
        """Rough estimate of tokens for this context (for API cost planning)"""
        # Simple heuristic: ~4 chars per token
        token_estimate = 0
        
        # Code context: ~1 token per 4 chars
        if context.get("code", {}).get("calc_method"):
            token_estimate += len(context["code"]["calc_method"]) // 4
        
        # Diagram: ~1 token per connection + 50 base
        token_estimate += context.get("diagram", {}).get("connections", 0) * 10 + 50
        
        # Metadata and structure
        token_estimate += json.dumps(context.get("metadata", {}), ensure_ascii=False).__len__() // 4
        
        return max(100, token_estimate)  # Min 100 tokens estimate


# Convenience function
def get_context(class_path: str, version: str = "6.1.4") -> Dict:
    """Helper function to gather context"""
    provider = ContextProvider(version=version)
    return provider.gather_context(class_path)
