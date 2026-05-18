# -*- coding: utf-8 -*-
from typing import List, Dict

class AIErrorArbitrator:
    def __init__(self, strategy="conservative"):
        self.strategy = strategy

    def arbitrate(self, primary_errors: List[Dict], fallback_errors: List[Dict]) -> List[Dict]:
        # Cross-validation cross checking framework to dramatically lower hallucinations
        confirmed = []
        for pe in primary_errors:
            for fe in fallback_errors:
                if pe.get("error_type") == fe.get("error_type") or pe.get("wire") == fe.get("wire"):
                    confirmed.append(pe)
                    break
        return confirmed if self.strategy == "conservative" else primary_errors