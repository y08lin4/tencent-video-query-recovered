from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from collections import OrderedDict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT / "tools"
ANALYSIS_DIR = ROOT / "analysis"

MODE_TO_ENV_KEYS = {
    "real": ["pc_web_real_cookie_replay", "mobile_h5_real_cookie_replay"],
    "aged": ["pc_web_aged_cookie_replay", "mobile_h5_aged_cookie_replay"],
    "login": ["pc_web_login_state_replay", "mobile_h5_login_state_replay"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build and run a Tencent Video replay bundle for real/aged/login "
            "closure: env JSON + environment matrix + authish semantics."
        )
    )
    parser.add_argument(
        "--mode",
        choices=sorted(MODE_TO_ENV_KEYS.keys()),
        required=True,
        help="Replay environment family to run.",
    )
    parser.add_argument("--desktop-cookie-header", help="Desktop Cookie header text.")
    parser.add_argument("--desktop-cookie-file", help="Text file containing the desktop Cookie header.")
    parser.add_argument("--mobile-cookie-header", help="Mobile Cookie header text.")
    parser.add_argument("--mobile-cookie-file", help="Text file containing the mobile Cookie header.")
    parser.add_argument(
        "--env-json",
        help="Optional prebuilt replay env JSON. When omitted, build one from cookie inputs.",
    )
    parser.add_argument(
        "--date-tag",
        default=datetime.now().strftime("%Y%m%d"),
        help="Date tag for output file names. Default: today in local time.",
    )
    parser.add_argument("--timeout", type=float, default=12.0, help="HTTP timeout for downstream probes.")
    parser.add_argument(
        "--http-retries",
        type=int,
        default=1,
        help="Retry count for the environment matrix probe.",
    )
    parser.add_argument(
        "--retry-sleep",
        type=float,
        default=0.5,
        help="Retry sleep base for the environment matrix probe.",
    )
    parser.add_argument(
        "--skip-semantics",
        action="store_true",
        help="Skip authish semantics replay and run only env-json + matrix.",
    )
    parser.add_argument(
        "--skip-matrix",
        action="store_true",
        help="Skip environment matrix and run only env-json + authish semantics.",
    )
    parser.add_argument(
        "--semantics-profile",
        choices=("authish", "full"),
        default="authish",
        help=(
            "Semantics case profile for tencent_param_semantics_probe.py. "
            "Default keeps the lighter authish closure pass."
        ),
    )
    parser.add_argument(
        "--probe-extra-callback-value",
        action="append",
        default=[],
        help=(
            "Optional extra callback value forwarded into "
            "tencent_param_semantics_probe.py. Can be passed multiple times."
        ),
    )
    parser.add_argument(
        "--probe-extra-callback-file",
        help=(
            "Optional callback-value file forwarded into "
            "tencent_param_semantics_probe.py."
        ),
    )
    parser.add_argument(
        "--subprocess-output-dir",
        help=(
            "Optional directory for child-process JSON outputs before the parent "
            "copies them into their final artifact paths."
        ),
    )
    parser.add_argument(
        "--artifact-output-dir",
        help=(
            "Optional final artifact directory for env/matrix/semantics outputs. "
            "Defaults to analysis/."
        ),
    )
    parser.add_argument("--summary-output", help="Optional explicit summary output path.")
    args = parser.parse_args()
    if not args.env_json and not args.desktop_cookie_header and not args.desktop_cookie_file:
        parser.error(
            "provide --env-json or at least one of --desktop-cookie-header / --desktop-cookie-file"
        )
    return args


def run_cmd(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def copy_if_needed(source: Path, target: Path) -> dict[str, object]:
    source = Path(source)
    target = Path(target)
    if source.resolve() == target.resolve():
        return {
            "mode": "direct",
            "source": str(source),
            "target": str(target),
            "copied": False,
            "error": "",
        }
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return {
            "mode": "staged_copy",
            "source": str(source),
            "target": str(target),
            "copied": True,
            "error": "",
        }
    except Exception as exc:  # pragma: no cover - runtime reporting path
        return {
            "mode": "staged_copy",
            "source": str(source),
            "target": str(target),
            "copied": False,
            "error": str(exc),
        }


def build_env_json(
    args: argparse.Namespace,
    env_json_path: Path,
    staged_env_json_path: Path | None,
) -> dict[str, object]:
    if args.env_json:
        return {
            "built": False,
            "path": str(Path(args.env_json)),
            "staged_path": str(Path(args.env_json)),
            "command": None,
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "copy_step": {
                "mode": "direct",
                "source": str(Path(args.env_json)),
                "target": str(Path(args.env_json)),
                "copied": False,
                "error": "",
            },
        }

    staged_output = staged_env_json_path or env_json_path
    cmd = [
        sys.executable,
        str(TOOLS_DIR / "tencent_cookie_env_from_headers.py"),
        "--mode",
        args.mode,
        "--output",
        str(staged_output),
    ]
    if args.desktop_cookie_header:
        cmd.extend(["--desktop-cookie-header", args.desktop_cookie_header])
    if args.desktop_cookie_file:
        cmd.extend(["--desktop-cookie-file", args.desktop_cookie_file])
    if args.mobile_cookie_header:
        cmd.extend(["--mobile-cookie-header", args.mobile_cookie_header])
    if args.mobile_cookie_file:
        cmd.extend(["--mobile-cookie-file", args.mobile_cookie_file])
    result = run_cmd(cmd)
    copy_step = (
        copy_if_needed(staged_output, env_json_path)
        if result.returncode == 0
        else {
            "mode": "not_run",
            "source": str(staged_output),
            "target": str(env_json_path),
            "copied": False,
            "error": "",
        }
    )
    effective_returncode = result.returncode if result.returncode != 0 else (1 if copy_step["error"] else 0)
    return {
        "built": True,
        "path": str(env_json_path),
        "staged_path": str(staged_output),
        "command": cmd,
        "returncode": effective_returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "copy_step": copy_step,
    }


def load_env_names(env_json_path: Path) -> list[str]:
    raw = json.loads(env_json_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{env_json_path} does not contain an env-name object")
    return [key for key in raw.keys() if isinstance(key, str) and key.strip()]


def run_matrix(
    args: argparse.Namespace,
    env_json_path: Path,
    matrix_output: Path,
    staged_matrix_output: Path | None,
) -> dict[str, object]:
    staged_output = staged_matrix_output or matrix_output
    cmd = [
        sys.executable,
        str(TOOLS_DIR / "tencent_environment_matrix_probe.py"),
        "--include-browser-like",
        "--extra-env-json",
        str(env_json_path),
        "--timeout",
        str(args.timeout),
        "--http-retries",
        str(args.http_retries),
        "--retry-sleep",
        str(args.retry_sleep),
        "--output",
        str(staged_output),
    ]
    result = run_cmd(cmd)
    copy_step = (
        copy_if_needed(staged_output, matrix_output)
        if result.returncode == 0
        else {
            "mode": "not_run",
            "source": str(staged_output),
            "target": str(matrix_output),
            "copied": False,
            "error": "",
        }
    )
    effective_returncode = result.returncode if result.returncode != 0 else (1 if copy_step["error"] else 0)
    return {
        "path": str(matrix_output),
        "staged_path": str(staged_output),
        "command": cmd,
        "returncode": effective_returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "copy_step": copy_step,
    }


def run_semantics(
    args: argparse.Namespace,
    env_json_path: Path,
    env_names: list[str],
    date_tag: str,
    artifact_dir: Path,
    staged_output_dir: Path | None,
) -> list[dict[str, object]]:
    outputs: list[dict[str, object]] = []
    if args.skip_semantics:
        return outputs

    for env_name in env_names:
        if not env_name.startswith("pc_web_") and not env_name.startswith("mobile_h5_"):
            continue
        output_path = artifact_dir / f"replay_bundle_{args.mode}_semantics_{env_name}_{date_tag}.json"
        staged_output_path = (
            staged_output_dir / output_path.name if staged_output_dir else output_path
        )
        cmd = [
            sys.executable,
            str(TOOLS_DIR / "tencent_param_semantics_probe.py"),
            "--output",
            str(staged_output_path),
            "--extra-env-json",
            str(env_json_path),
            "--env-name",
            env_name,
            "--case-profile",
            args.semantics_profile,
            "--timeout",
            str(args.timeout),
        ]
        for value in args.probe_extra_callback_value:
            cmd.extend(["--extra-callback-value", value])
        if args.probe_extra_callback_file:
            cmd.extend(["--extra-callback-file", args.probe_extra_callback_file])
        result = run_cmd(cmd)
        copy_step = (
            copy_if_needed(staged_output_path, output_path)
            if result.returncode == 0
            else {
                "mode": "not_run",
                "source": str(staged_output_path),
                "target": str(output_path),
                "copied": False,
                "error": "",
            }
        )
        effective_returncode = result.returncode if result.returncode != 0 else (1 if copy_step["error"] else 0)
        outputs.append(
            {
                "env_name": env_name,
                "path": str(output_path),
                "staged_path": str(staged_output_path),
                "command": cmd,
                "returncode": effective_returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "copy_step": copy_step,
            }
        )
    return outputs


def main() -> int:
    args = parse_args()
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    date_tag = args.date_tag
    artifact_dir = Path(args.artifact_output_dir) if args.artifact_output_dir else ANALYSIS_DIR
    artifact_dir.mkdir(parents=True, exist_ok=True)

    env_json_path = (
        Path(args.env_json)
        if args.env_json
        else artifact_dir / f"replay_bundle_{args.mode}_env_{date_tag}.json"
    )
    matrix_output = artifact_dir / f"replay_bundle_{args.mode}_matrix_{date_tag}.json"
    summary_output = (
        Path(args.summary_output)
        if args.summary_output
        else artifact_dir / f"replay_bundle_{args.mode}_summary_{date_tag}.json"
    )
    with tempfile.TemporaryDirectory(prefix="tencent_replay_bundle_") as temp_dir:
        staged_root = Path(args.subprocess_output_dir) if args.subprocess_output_dir else Path(temp_dir)
        staged_root.mkdir(parents=True, exist_ok=True)
        staged_env_json_path = (
            None
            if args.env_json
            else staged_root / f"replay_bundle_{args.mode}_env_{date_tag}.json"
        )
        staged_matrix_output = staged_root / matrix_output.name

        env_step = build_env_json(args, env_json_path, staged_env_json_path)
        if env_step["returncode"] != 0:
            summary = OrderedDict(
                (
                    ("generated_at", datetime.now().isoformat(timespec="seconds")),
                    ("mode", args.mode),
                    ("status", "failed_env_build"),
                    ("artifact_output_dir", str(artifact_dir)),
                    ("subprocess_output_dir", str(staged_root)),
                    ("env_step", env_step),
                )
            )
            summary_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 1

        env_names = load_env_names(env_json_path)
        matrix_step: dict[str, object]
        if args.skip_matrix:
            matrix_step = {
                "path": str(matrix_output),
                "staged_path": str(staged_matrix_output),
                "command": None,
                "returncode": 0,
                "stdout": "",
                "stderr": "",
                "copy_step": {
                    "mode": "skipped",
                    "source": str(staged_matrix_output),
                    "target": str(matrix_output),
                    "copied": False,
                    "error": "",
                },
                "skipped": True,
            }
        else:
            matrix_step = run_matrix(args, env_json_path, matrix_output, staged_matrix_output)
        semantics_steps = run_semantics(
            args,
            env_json_path,
            env_names,
            date_tag,
            artifact_dir,
            staged_root,
        )

        overall_status = "ok"
        if matrix_step["returncode"] != 0:
            overall_status = "matrix_failed"
        elif any(step["returncode"] != 0 for step in semantics_steps):
            overall_status = "semantics_partial_failure"

        summary = OrderedDict(
            (
                ("generated_at", datetime.now().isoformat(timespec="seconds")),
                ("mode", args.mode),
                ("status", overall_status),
                ("artifact_output_dir", str(artifact_dir)),
                ("subprocess_output_dir", str(staged_root)),
                (
                    "artifact_family",
                    OrderedDict(
                        (
                            ("env_json", str(env_json_path)),
                            ("matrix", str(matrix_output)),
                            ("semantics", [step["path"] for step in semantics_steps]),
                        )
                    ),
                ),
                ("environment_names", env_names),
                (
                    "semantics_config",
                    OrderedDict(
                        (
                            ("profile", args.semantics_profile),
                            ("extra_callback_values", args.probe_extra_callback_value),
                            ("extra_callback_file", args.probe_extra_callback_file or ""),
                        )
                    ),
                ),
                ("env_step", env_step),
                ("matrix_step", matrix_step),
                ("semantics_steps", semantics_steps),
                (
                    "next_reading",
                    [
                        "When status=ok, inspect the matrix and authish semantics outputs for aged/login-specific parameter splits.",
                        "When status=matrix_failed or semantics_partial_failure, use the recorded stderr/stdout to rerun just the failed substep.",
                        "This runner reduces the final environment-closure path to one repeatable command once Cookie headers are available.",
                        "If the full bundle is too slow in one pass, use --skip-semantics or --skip-matrix to split the run into smaller reproducible phases.",
                        "Use --semantics-profile full plus --probe-extra-callback-value/--probe-extra-callback-file when callback wrapper edge-cases should ride along with an environment replay.",
                        "Child-process outputs are now staged under subprocess_output_dir before being copied into final artifact paths.",
                    ],
                ),
            )
        )
        summary_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if overall_status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
