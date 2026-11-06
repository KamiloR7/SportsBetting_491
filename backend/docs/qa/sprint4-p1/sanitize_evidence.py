"""Project only sanitized, synthetic assessment outputs and test case identities."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assessment", type=Path, required=True)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assessment = json.loads(args.assessment.read_text())
    scenarios = assessment["invalid_scenarios"]
    if len(scenarios) != 12 or len({row["id"] for row in scenarios}) != 12:
        raise ValueError("Evidence must contain exactly twelve distinct invalid scenarios")
    if not all(row["actual_status"] == row["expected_status"] and row["actual_code"] == row["expected_code"]
               and row["model_executions"] == row["inference_calls"] == 0 and not row["prediction_generated"]
               for row in scenarios):
        raise ValueError("Refusing to publish an assessment as passing after a failed rejection")
    repeats = assessment["consistency"]
    if {row["sport"] for row in repeats} != {"NFL", "MLB", "EPL"} or len(repeats) != 3:
        raise ValueError("Missing accepted sport fixture")
    if not all(row["execution_count"] == row["model_executions"] == 10
               and row["unique_input_hashes"] == row["unique_feature_orders"] == row["unique_model_versions"]
               == row["unique_probability_vectors"] == 1 and row["all_probabilities_valid"] for row in repeats):
        raise ValueError("Repeated execution acceptance failed")
    root = ET.parse(args.junit).getroot()
    cases = root.findall(".//testcase")
    failures = sum(case.find("failure") is not None or case.find("error") is not None for case in cases)
    skipped = sum(case.find("skipped") is not None for case in cases)
    if failures:
        raise ValueError("Backend regression contains failures; preserve raw results privately for remediation")
    clean = ET.Element("testsuite", name="sanitized_backend_regression", tests=str(len(cases)),
                       failures="0", errors="0", skipped=str(skipped))
    for case in cases:
        target = ET.SubElement(clean, "testcase", classname=case.get("classname", ""), name=case.get("name", ""))
        if case.find("skipped") is not None:
            ET.SubElement(target, "skipped", message="Disposable PostgreSQL integration target not configured")
    args.output.mkdir(parents=True, exist_ok=True)
    ET.indent(clean)
    xml_path = args.output / "backend-regression.xml"
    ET.ElementTree(clean).write(xml_path, encoding="utf-8", xml_declaration=True)
    xml_path.write_bytes(xml_path.read_bytes() + b"\n")
    # All fields below originate in controlled synthetic tests. No request bodies,
    # filesystem paths, hostnames, credentials or raw traceback/log output is copied.
    keys = ("evidence_version", "synthetic_fixtures_only", "proposal_source", "invalid_scenarios",
            "consistency", "leakage", "freshness", "transparency")
    sanitized = {key: assessment[key] for key in keys}
    sanitized["backend_regression"] = {"passed": len(cases) - skipped, "failed": failures, "skipped": skipped}
    (args.output / "assessment-results.json").write_text(json.dumps(sanitized, indent=2, sort_keys=True, allow_nan=False) + "\n")
    events = [dict(event="invalid_input_rejected", scenario_id=row["id"], status=row["actual_status"],
                   error_code=row["actual_code"], model_executions=row["model_executions"],
                   inference_calls=row["inference_calls"], prediction_generated=row["prediction_generated"])
              for row in sorted(scenarios, key=lambda row: row["id"])]
    (args.output / "rejection-events.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in events))
    print(json.dumps(sanitized["backend_regression"], sort_keys=True))


if __name__ == "__main__":
    main()
