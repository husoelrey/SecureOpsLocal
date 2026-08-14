import logging
from typing import Any, Dict

from src.schemas.incident_report import IncidentReportCreate

logger = logging.getLogger(__name__)

class QualityScorer:
    """Deterministic quality scorers for LLM outputs in the benchmark."""
    
    @staticmethod
    def score_schema_compliance(report: IncidentReportCreate) -> float:
        """
        Returns 1.0 if the model produced valid output, 0.0 otherwise.
        """
        if report.status == "invalid_model_output":
            return 0.0
        return 1.0

    @staticmethod
    def score_risk_consistency(report: IncidentReportCreate, expected_risk: str) -> float:
        """
        Returns 1.0 if the risk_level matches the expected risk level, 0.0 otherwise.
        """
        if report.status == "invalid_model_output":
            return 0.0
        return 1.0 if report.risk_level.lower() == expected_risk.lower() else 0.0

    @staticmethod
    def score_citation_validity(report: IncidentReportCreate, valid_chunk_ids: set[str]) -> float:
        """
        Returns 1.0 if all citations are valid (exist in chunks), 0.0 if there are invalid citations.
        Returns 1.0 if there are no citations (though ideally we might want to penalize lack of citations).
        """
        if report.status == "invalid_model_output":
            return 0.0
            
        if not report.citations:
            return 0.0 # Expecting at least some citation
            
        for citation in report.citations:
            if citation not in valid_chunk_ids:
                return 0.0
        return 1.0

    @staticmethod
    def evaluate(report: IncidentReportCreate, case_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Evaluate a report against the case data and return a dictionary of scores.
        """
        valid_chunk_ids = {chunk["chunk_id"] for chunk in case_data.get("chunks", [])}
        expected_risk = case_data.get("expected_risk_level", "unknown")
        
        return {
            "schema_compliance": QualityScorer.score_schema_compliance(report),
            "risk_consistency": QualityScorer.score_risk_consistency(report, expected_risk),
            "citation_validity": QualityScorer.score_citation_validity(report, valid_chunk_ids),
        }
