import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm.ollama import OllamaProvider
from src.llm.foundry import FoundryLocalProvider
from src.llm.analyzer import IncidentAnalyzer
from src.llm.scorers import QualityScorer
from src.llm.telemetry import TelemetryTracker, calculate_token_rate
from src.schemas.analysis import LogAnalysis
from src.schemas.rag import DocumentChunk


async def run_benchmark():
    cases_dir = Path("tests/benchmark/cases")
    results_dir = Path("docs/benchmark_results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Load cases
    cases = []
    if cases_dir.exists():
        for file in sorted(cases_dir.glob("*.json")):
            with open(file, "r", encoding="utf-8") as f:
                cases.append(json.load(f))
                
    if not cases:
        print("No benchmark cases found. Run generate_benchmark_cases.py first.")
        return

    # Define profiles
    profiles = [
        {
            "id": "foundation-sec-8b-reasoning-q4",
            "provider": OllamaProvider(model_name="foundation-sec-8b-reasoning:q4_k_m"), # Assuming this name or similar
            "process_name": "ollama"
        },
        {
            "id": "qwen3.5-9b-q4",
            "provider": OllamaProvider(model_name="qwen3.5:9b"),
            "process_name": "ollama"
        },
        {
            "id": "foundry-local-default",
            "provider": FoundryLocalProvider(base_url="http://127.0.0.1:39251", model_name="Phi-3-mini-4k-instruct"), # Placeholder for resolved profile
            "process_name": "foundrylocald"
        }
    ]

    all_results = []
    benchmark_timestamp = datetime.now(timezone.utc).isoformat()

    for profile in profiles:
        print(f"\n--- Benchmarking Profile: {profile['id']} ---")
        analyzer = IncidentAnalyzer(provider=profile['provider'], max_retries=0)
        
        telemetry = TelemetryTracker(process_name=profile["process_name"])
        telemetry.start()
        
        profile_results = {
            "profile_id": profile["id"],
            "cases": [],
            "summary": {
                "total_cases": len(cases),
                "successful_cases": 0,
                "failed_cases": 0
            }
        }
        
        for case in cases:
            print(f"  Running case: {case['case_id']}")
            analysis = LogAnalysis.model_validate(case["analysis"])
            chunks = [DocumentChunk.model_validate(c) for c in case["chunks"]]
            
            telemetry.poll()
            try:
                report = await analyzer.analyze_incident(
                    incident_id=case["case_id"],
                    analysis=analysis,
                    chunks=chunks
                )
                
                telemetry.poll()
                scores = QualityScorer.evaluate(report, case)
                
                token_rate = calculate_token_rate(
                    report.performance_metrics.get("completion_tokens"),
                    report.performance_metrics.get("total_latency_ms"),
                    report.performance_metrics.get("time_to_first_token_ms")
                )
                
                if report.status == "invalid_model_output":
                    profile_results["summary"]["failed_cases"] += 1
                else:
                    profile_results["summary"]["successful_cases"] += 1
                    
                profile_results["cases"].append({
                    "case_id": case["case_id"],
                    "status": report.status,
                    "scores": scores,
                    "metrics": {
                        "total_latency_ms": report.performance_metrics.get("total_latency_ms"),
                        "time_to_first_token_ms": report.performance_metrics.get("time_to_first_token_ms"),
                        "token_rate": token_rate
                    },
                    "error": report.risk_reasoning if report.status == "invalid_model_output" else None
                })
                
            except Exception as e:
                print(f"    Failed: {e}")
                profile_results["summary"]["failed_cases"] += 1
                profile_results["cases"].append({
                    "case_id": case["case_id"],
                    "status": "error",
                    "error": str(e)
                })
        
        telemetry.poll()
        telemetry_metrics = telemetry.get_metrics()
        profile_results["telemetry"] = telemetry_metrics
        
        all_results.append(profile_results)
        print(f"Profile {profile['id']} finished. Peak RAM: {telemetry_metrics['peak_memory_mb']} MB")

    # Save full results
    results_file = results_dir / f"benchmark_run_{benchmark_timestamp.replace(':', '-')}.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": benchmark_timestamp,
            "profiles": all_results
        }, f, indent=2)
        
    print(f"\nBenchmark completed. Results saved to {results_file}")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
