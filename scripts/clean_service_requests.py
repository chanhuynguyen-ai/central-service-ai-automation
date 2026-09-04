#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.data_quality import clean_csv  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean and validate CentralOps service-request CSV data.")
    parser.add_argument("input", type=Path, nargs="?", default=ROOT / "data" / "service_requests_sample.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "generated" / "service_requests_clean.csv")
    parser.add_argument("--report", type=Path, default=ROOT / "data" / "generated" / "data_quality_report.json")
    args = parser.parse_args()

    report = clean_csv(args.input, args.output, args.report)
    print(f"Rows: {report['rows_read']}")
    print(f"Issues: {report['issue_count']}")
    print(f"Completed SLA compliance: {report['completed_sla_compliance_pct']}%")
    print(f"Cleaned CSV: {args.output}")
    print(f"Quality report: {args.report}")


if __name__ == "__main__":
    main()
