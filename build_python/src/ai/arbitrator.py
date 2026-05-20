# -*- coding: utf-8 -*-
"""
AI Error Arbitrator - Reduces false positives in AI-detected defects
Uses dual-model verification or single-model with severity filtering
"""

import sys
from datetime import datetime
from typing import List, Dict, Optional


class AIErrorArbitrator:
    """
    Arbitrates AI errors using configurable strategies
    to reduce false positives and improve accuracy
    """
    
    def __init__(self, primary_model_config=None, fallback_model_config=None, 
                 strategy: str = "conservative"):
        self.primary_model_config = primary_model_config
        self.fallback_model_config = fallback_model_config
        self.arbitration_enabled = True
        self.arbitration_log = []
        self.current_strategy = strategy
        
        # Available arbitration strategies
        self.strategies = {
            "conservative": self._conservative_strategy,
            "severity_based": self._severity_based_strategy,
            "pass_through": self._pass_through_strategy,
        }
        
        # Standard error types
        self.fixed_error_types = [
            "Variable Mapping Error",
            "Parameter Type Mismatch",
            "Uninitialized Variable",
            "Array Index Out of Bounds",
            "Integer Overflow/Underflow",
            "Logic Error",
        ]
        
        # Severity levels
        self.severity_levels = {
            "low": 1, "l": 1, "info": 1, "minor": 1,
            "medium": 2, "med": 2, "m": 2, "warning": 2, "warn": 2,
            "high": 3, "h": 3, "error": 3, "critical": 3,
        }
    
    def log_step(self, step: str, details: str = ""):
        """Log an arbitration step"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "details": details
        }
        self.arbitration_log.append(entry)
        print(f"[Arbitrator] {step}: {details}", file=sys.stderr)
    
    def arbitrate_errors(self, primary_errors: List[Dict], 
                        fallback_errors: List[Dict] = None) -> List[Dict]:
        """
        Main arbitration entry point.
        
        Args:
            primary_errors: Errors from primary analysis
            fallback_errors: Errors from fallback/secondary analysis (optional)
        
        Returns:
            Confirmed errors after arbitration
        """
        self.log_step("START", 
            f"Arbitrating {len(primary_errors)} primary errors, "
            f"{len(fallback_errors) if fallback_errors else 0} fallback")
        
        if not self.arbitration_enabled:
            self.log_step("DISABLED", "Arbitration disabled, returning primary errors")
            return primary_errors
        
        # Use configured strategy
        strategy_func = self.strategies.get(self.current_strategy, self._conservative_strategy)
        
        if fallback_errors:
            confirmed = strategy_func(primary_errors, fallback_errors)
        else:
            # No fallback, use filtering strategy
            confirmed = self._filter_by_severity(primary_errors)
        
        self.log_step("COMPLETE", f"Confirmed {len(confirmed)} errors after arbitration")
        return confirmed
    
    def _conservative_strategy(self, primary_errors: List[Dict], 
                              fallback_errors: List[Dict]) -> List[Dict]:
        """
        Conservative: Only errors confirmed by both models are kept.
        Reduces false positives at cost of missing some real issues.
        """
        self.log_step("STRATEGY", "Using conservative (dual-model confirmation)")
        
        confirmed = []
        for p_error in primary_errors:
            for f_error in fallback_errors:
                if self._errors_match(p_error, f_error):
                    # Merge information
                    merged = {
                        "type": p_error.get("type"),
                        "severity": self._merge_severity(
                            p_error.get("severity"),
                            f_error.get("severity")
                        ),
                        "description": p_error.get("description", ""),
                        "location": p_error.get("location", ""),
                        "confirmed_by": ["primary", "fallback"],
                        "arbitration_method": "conservative"
                    }
                    confirmed.append(merged)
                    self.log_step("CONFIRMED", 
                        f"Error '{p_error.get('type')}' confirmed by both models")
                    break
            else:
                self.log_step("DISPUTED", 
                    f"Error '{p_error.get('type')}' only in primary (potential false positive)")
        
        return confirmed
    
    def _severity_based_strategy(self, primary_errors: List[Dict], 
                                fallback_errors: List[Dict]) -> List[Dict]:
        """
        Severity-based: High/critical errors kept even if only primary model found them.
        Medium/low errors only kept if confirmed by both.
        """
        self.log_step("STRATEGY", "Using severity-based filtering")
        
        # First apply conservative strategy
        confirmed = self._conservative_strategy(primary_errors, fallback_errors)
        
        # Add high-severity unconfirmed errors
        confirmed_types = {e.get("type") for e in confirmed}
        
        for p_error in primary_errors:
            if p_error.get("type") in confirmed_types:
                continue  # Already confirmed
            
            severity = self._parse_severity(p_error.get("severity", ""))
            if severity >= 3:  # HIGH or CRITICAL
                p_error_copy = p_error.copy()
                p_error_copy["arbitration_method"] = "severity_override"
                p_error_copy["confirmed_by"] = ["primary"]
                confirmed.append(p_error_copy)
                
                self.log_step("SEVERITY_OVERRIDE",
                    f"High-severity error '{p_error.get('type')}' kept despite single-model detection")
        
        return confirmed
    
    def _pass_through_strategy(self, primary_errors: List[Dict], 
                              fallback_errors: List[Dict] = None) -> List[Dict]:
        """Pass-through: Return all errors with metadata about confirmation"""
        self.log_step("STRATEGY", "Using pass-through (all errors returned)")
        
        for error in primary_errors:
            error["arbitration_method"] = "pass_through"
        
        return primary_errors
    
    def _filter_by_severity(self, errors: List[Dict]) -> List[Dict]:
        """Filter errors by minimum severity when no fallback available"""
        # Keep only HIGH and above severity
        filtered = []
        for error in errors:
            severity = self._parse_severity(error.get("severity", ""))
            if severity >= 2:  # MEDIUM and above
                filtered.append(error)
                self.log_step("FILTERED", f"Keeping {error.get('type')} ({severity})")
        
        return filtered
    
    def _errors_match(self, error1: Dict, error2: Dict) -> bool:
        """Check if two errors match (same type and similar location)"""
        type1 = error1.get("type", "").lower().strip()
        type2 = error2.get("type", "").lower().strip()
        
        if not type1 or not type2:
            return False
        
        # Exact or partial match
        return type1 == type2 or type1 in type2 or type2 in type1
    
    def _merge_severity(self, sev1: str, sev2: str) -> str:
        """Merge two severity levels (take higher)"""
        s1 = self._parse_severity(sev1)
        s2 = self._parse_severity(sev2)
        
        max_severity = max(s1, s2)
        severity_names = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}
        return severity_names.get(max_severity, "Unknown")
    
    def _parse_severity(self, severity_str: str) -> int:
        """Parse severity string to numeric level"""
        if not severity_str:
            return 2  # Default to medium
        
        severity_lower = severity_str.lower().strip()
        return self.severity_levels.get(severity_lower, 2)
    
    def get_arbitration_report(self) -> Dict:
        """Get arbitration log and statistics"""
        return {
            "strategy": self.current_strategy,
            "enabled": self.arbitration_enabled,
            "log_entries": len(self.arbitration_log),
            "logs": self.arbitration_log[-10:],  # Last 10 entries
        }


# Module-level convenience functions
def create_arbitrator(strategy: str = "conservative") -> AIErrorArbitrator:
    """Factory function to create arbitrator"""
    return AIErrorArbitrator(strategy=strategy)

def arbitrate_errors(errors: List[Dict], strategy: str = "conservative") -> List[Dict]:
    """Convenience function for quick arbitration"""
    arbitrator = create_arbitrator(strategy=strategy)
    return arbitrator.arbitrate_errors(errors)