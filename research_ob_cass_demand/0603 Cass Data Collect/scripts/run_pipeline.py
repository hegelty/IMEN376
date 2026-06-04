from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Cass data/model pipeline end to end.")
    parser.add_argument("--skip-collect", action="store_true", help="Do not refresh public data CSVs.")
    parser.add_argument("--skip-chronos", action="store_true", help="Run model pipeline without Chronos-2 inference.")
    parser.add_argument(
        "--overwrite-templates",
        action="store_true",
        help="Overwrite Phase 1 template CSVs. Default preserves existing template data.",
    )
    return parser.parse_args()


def run_step(name: str, args: list[str]) -> None:
    print(f"\n=== {name} ===", flush=True)
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def main() -> None:
    args = parse_args()
    if not args.skip_collect:
        run_step("collect public data", [str(SCRIPTS / "collect_cass_data.py")])

    template_args = [str(SCRIPTS / "prepare_phase1_templates.py")]
    if args.overwrite_templates:
        template_args.append("--overwrite")
    run_step("prepare Phase 1 templates", template_args)

    run_step("check Phase 1 inputs", [str(SCRIPTS / "check_phase1_inputs.py")])
    run_step("build Phase 1 model input", [str(SCRIPTS / "build_phase1_model_input.py")])

    model_args = [str(SCRIPTS / "model_cass_demand.py")]
    if args.skip_chronos:
        model_args.append("--skip-chronos")
    run_step("run demand model", model_args)

    print("\nPipeline completed.", flush=True)
    print(f"Model summary: {ROOT / 'model_outputs' / 'model_run_summary.md'}", flush=True)


if __name__ == "__main__":
    main()
