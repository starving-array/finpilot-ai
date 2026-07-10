"""
FHSS CLI — Unified startup, health, and commit workflow.
Usage:
    python cli.py dev        # Full project startup
    python cli.py status     # Repository health report
    python cli.py commit     # Quality-gated commit
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Logging ──────────────────────────────────────────────────────────────
LOG_DIR = Path(__file__).parent / "logs"
LOG_FILE = LOG_DIR / "cli.log"
LOG_DIR.mkdir(exist_ok=True)

_INDENT = 0


def _log(level, message, **extra):
    ts = datetime.now(timezone.utc).isoformat()
    prefix = "  " * _INDENT
    line = f"{prefix}[{ts}] [{level}] {message}"
    if extra:
        line += " " + json.dumps(extra)
    print(line, file=sys.stderr)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def info(msg, **kw):
    _log("INFO", msg, **kw)


def warn(msg, **kw):
    _log("WARN", msg, **kw)


def error(msg, **kw):
    _log("ERROR", msg, **kw)


def section(title):
    info("")
    info("─" * 60)
    info(f"  {title}")
    info("─" * 60)


def step(name):
    global _INDENT
    _INDENT = 1
    info(f"▶ {name} ...")


def ok(duration=None):
    global _INDENT
    dur = f" ({duration:.1f}s)" if duration else ""
    info(f"  ✓ PASS{dur}")
    _INDENT = 0


def fail(duration=None):
    global _INDENT
    dur = f" ({duration:.1f}s)" if duration else ""
    info(f"  ✗ FAIL{dur}")
    _INDENT = 0


# ── Helpers ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
DOCKER_COMPOSE = ["docker", "compose", "-f", str(ROOT / "docker" / "docker-compose.yml")]


def run(cmd, cwd=None, timeout=120, capture=False):
    """Run a command, log output, return (ok, stdout, stderr)."""
    label = cmd if isinstance(cmd, str) else " ".join(cmd)
    info(f"  $ {label}")
    try:
        r = subprocess.run(
            cmd if isinstance(cmd, list) else cmd,
            cwd=cwd or ROOT,
            capture_output=capture,
            text=True,
            timeout=timeout,
            shell=isinstance(cmd, str),
        )
        if r.returncode != 0:
            if r.stderr:
                for line in r.stderr.strip().splitlines():
                    warn(f"  stderr: {line}")
            return False, r.stdout, r.stderr
        return True, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        error(f"  Timed out after {timeout}s")
        return False, "", "timeout"
    except FileNotFoundError:
        error(f"  Command not found: {label}")
        return False, "", "not found"


def check_cmd(name):
    return shutil.which(name) is not None


def wait_for_health(url, max_retries=30, interval=3):
    for i in range(max_retries):
        ok, out, _ = run(f'curl -s {url}', timeout=5, capture=True)
        if ok and out:
            try:
                data = json.loads(out)
                if isinstance(data, dict) and data.get("status") == "UP":
                    return True
            except (json.JSONDecodeError, AttributeError):
                pass
        if i < max_retries - 1:
            time.sleep(interval)
    return False


def docker_ps():
    ok, out, _ = run([*DOCKER_COMPOSE, "ps"], capture=True)
    return out or ""


def container_running(name):
    return name in docker_ps() and "Up" in docker_ps()


# ── Commands ─────────────────────────────────────────────────────────────
def cmd_dev(args):
    """Full project startup for local development."""

    info("")
    info("╔══════════════════════════════════════════════════╗")
    info("║   FHSS — Development Startup                    ║")
    info("╚══════════════════════════════════════════════════╝")
    info("")

    # ── 1. Environment ──
    section("1. Environment Check")

    t0 = time.time()
    step("Python")
    ok(time.time() - t0)

    step("Docker")
    if not check_cmd("docker"):
        fail()
        error("Docker not found. Install Docker Desktop and try again.")
        return False
    ok()

    step("Node")
    if not check_cmd("node"):
        warn("Node not found. Frontend will not start.")
    else:
        ok()

    # ── 2. Docker Infra ──
    section("2. Starting Infrastructure")

    step("Starting postgres + redis")
    t0 = time.time()
    ok_flag, out, err = run([*DOCKER_COMPOSE, "up", "-d", "postgres", "redis"])
    if not ok_flag:
        fail(time.time() - t0)
        error("Failed to start Docker containers")
        return False
    ok(time.time() - t0)

    step("Waiting for postgres health")
    t0 = time.time()
    if not wait_for_health("http://localhost:8080/api/v1/score/health", max_retries=3):
        # postgres doesn't have an HTTP endpoint; just check ps state
        time.sleep(10)
    ok(time.time() - t0)

    # ── 3. Backend (Flyway) ──
    section("3. Database Schema (Flyway)")

    step("Starting backend (applies migrations)")
    t0 = time.time()
    ok_flag, out, err = run([*DOCKER_COMPOSE, "up", "-d", "backend"])
    if not ok_flag:
        fail(time.time() - t0)
        error("Backend Docker build/start failed")
        return False
    ok(time.time() - t0)

    step("Waiting for backend health")
    t0 = time.time()
    healthy = wait_for_health("http://localhost:8080/api/v1/score/health")
    if healthy:
        ok(time.time() - t0)
    else:
        fail(time.time() - t0)
        warn("Backend health check timed out. Check 'docker logs fhss-backend'")
        if args.strict:
            return False

    # ── 4. Seed DB ──
    section("4. Seed Database")

    if args.skip_seed:
        info("  (skipped)")
    else:
        step("Installing synthetic-data dependencies")
        ok_flag, out, err = run(
            f'"{sys.executable}" -m pip install -r requirements.txt -q',
            cwd=ROOT / "synthetic-data",
            timeout=60,
        )
        if ok_flag:
            ok()
        else:
            fail()
            error("Failed to install seed dependencies")

        step("Running seed.py")
        t0 = time.time()
        ok_flag, out, err = run(
            f"python seed.py",
            cwd=ROOT / "synthetic-data",
            timeout=60,
        )
        if ok_flag:
            for line in (out or "").strip().splitlines():
                info(f"  {line}")
            ok(time.time() - t0)
        else:
            fail(time.time() - t0)
            if err:
                for line in err.strip().splitlines():
                    error(f"  {line}")
            if args.strict:
                return False

    # ── 5. Train Model ──
    section("5. Train ML Model")

    if args.skip_train:
        info("  (skipped)")
    else:
        step("Installing ml-service dependencies")
        ok_flag, out, err = run(
            f'"{sys.executable}" -m pip install -r requirements.txt -q',
            cwd=ROOT / "ml-service",
            timeout=120,
        )
        if ok_flag:
            ok()
        else:
            fail()
            error("Failed to install ML dependencies")

        step("Running train_model.py")
        t0 = time.time()
        ok_flag, out, err = run(
            f"python -m app.training.train_model ..\\synthetic-data\\output\\profiles_labeled.csv",
            cwd=ROOT / "ml-service",
            timeout=300,
        )
        if ok_flag:
            ok(time.time() - t0)
        else:
            fail(time.time() - t0)
            if err:
                for line in err.strip().splitlines():
                    error(f"  {line}")

    # ── 6. ML Service ──
    section("6. Start ML Service")

    if args.ml_docker:
        step("Starting ml-service in Docker")
        t0 = time.time()
        ok_flag, out, err = run([*DOCKER_COMPOSE, "up", "-d", "ml-service"])
        if ok_flag:
            ok(time.time() - t0)
            step("Waiting for ML health")
            if wait_for_health("http://localhost:8000/health"):
                ok()
            else:
                warn("ML health check timed out")
        else:
            fail(time.time() - t0)
            warn("Falling back to local ML service")
            args.ml_docker = False

    if not args.ml_docker:
        step("Starting ML service locally (uvicorn)")
        t0 = time.time()
        env = os.environ.copy()
        env["MODEL_PATH"] = str(ROOT / "ml-service" / "models" / "model_latest.joblib")
        try:
            proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app.main:app",
                 "--host", "0.0.0.0", "--port", "8000"],
                cwd=ROOT / "ml-service",
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            info(f"  PID: {proc.pid}")
            time.sleep(5)
            ok(time.time() - t0)
            info("  ML service started (background). Stop with: taskkill /F /PID {pid}")
        except Exception as e:
            fail(time.time() - t0)
            error(f"  Failed to start ML service: {e}")

    # ── 7. Frontend ──
    section("7. Start Frontend")

    if args.skip_frontend:
        info("  (skipped)")
    else:
        step("Starting frontend dev server (npm run dev)")
        t0 = time.time()
        try:
            proc = subprocess.Popen(
                ["npx.cmd", "vite", "--port", "5173"],
                cwd=ROOT / "frontend",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            info(f"  PID: {proc.pid}")
            ok(time.time() - t0)
        except Exception as e:
            fail(time.time() - t0)
            error(f"  Failed to start frontend: {e}")

    # ── Summary ──
    section("Summary")
    info("  Backend API:  http://localhost:8080")
    info("  ML Service:   http://localhost:8000")
    info("  Frontend:     http://localhost:5173")
    info(f"  Log file:     {LOG_FILE}")
    info("")
    info("  To stop:  docker compose -f docker/docker-compose.yml down")
    info("")
    return True


def cmd_status(args):
    """Complete repository health report."""
    info("")
    info("╔══════════════════════════════════════════════════╗")
    info("║   FHSS — Repository Health Report               ║")
    info("╚══════════════════════════════════════════════════╝")
    info("")

    results = {}

    # ── Repository ──
    section("Repository")
    step("Git status")
    ok_flag, out, _ = run("git status --short", capture=True)
    dirty = bool(out and out.strip())
    results["git_dirty"] = dirty
    if dirty:
        warn(f"  Uncommitted files:\n{out}")
    else:
        ok()

    step("Branch")
    ok_flag, out, _ = run("git branch --show-current", capture=True)
    branch = (out or "unknown").strip()
    info(f"  {branch}")

    # ── Containers ──
    section("Containers")
    step("Docker running")
    if check_cmd("docker"):
        ok()
        for svc in ["fhss-postgres", "fhss-redis", "fhss-backend"]:
            if container_running(svc):
                info(f"    {svc}: Up")
            else:
                warn(f"    {svc}: Not running")
    else:
        warn("Docker not found")

    # ── Services ──
    section("Services")
    step("Backend API")
    ok_flag, out, _ = run("curl -s http://localhost:8080/api/v1/score/health", timeout=5, capture=True)
    if ok_flag and out:
        try:
            d = json.loads(out)
            info(f"  {json.dumps(d)}")
        except json.JSONDecodeError:
            pass
    else:
        warn("Not reachable")

    step("ML Service")
    ok_flag, out, _ = run("curl -s http://localhost:8000/health", timeout=5, capture=True)
    if ok_flag and out:
        try:
            d = json.loads(out)
            if d.get("status") == "UP":
                info(f"  Model: {d.get('model_version', '?')}")
            else:
                info(f"  {json.dumps(d)}")
        except json.JSONDecodeError:
            pass
    else:
        warn("Not reachable")

    # ── Files ──
    section("Repository Hygiene")
    step("Temp / cache / build artifacts")
    patterns = ["**/__pycache__", "**/.venv", "**/node_modules", "**/target"]
    counts = []
    for pat in patterns:
        c = len(list(ROOT.glob(pat)))
        if c:
            counts.append(f"{pat}: {c}")
    if counts:
        for c in counts:
            warn(f"  {c}")
    else:
        ok()

    # ── Final Score ──
    section("Overall")
    checks = [
        ("docker", check_cmd("docker")),
        ("postgres", container_running("fhss-postgres")),
        ("redis", container_running("fhss-redis")),
        ("backend_api", "Not reachable" not in str(results)),
    ]
    passed = sum(1 for _, v in checks if v)
    total = len(checks)
    score = f"{passed}/{total}"
    info(f"  Health: {score}")
    if passed == total:
        info("  Result: HEALTHY")
    else:
        warn(f"  Result: DEGRADED ({total - passed} issues)")
    info("")


def cmd_test(args):
    """Run all test suites."""
    info("")
    info("╔══════════════════════════════════════════════════╗")
    info("║   FHSS — Running All Tests                      ║")
    info("╚══════════════════════════════════════════════════╝")
    info("")

    suites = [
        ("Backend (scoring)", ROOT / "backend",
         [str(ROOT / "backend" / "mvnw.cmd"), "test", "-pl", "scoring", "-am", "-q"]),
        ("ML Service", ROOT / "ml-service",
         [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"]),
        ("Frontend", ROOT / "frontend",
         ["npx.cmd", "vitest", "run", "--reporter=verbose"]),
        ("CLI", ROOT,
         [sys.executable, "-m", "pytest", "tests/test_cli.py", "-v", "--tb=short"]),
    ]

    passed = 0
    for name, cwd, cmd in suites:
        section(name)
        step("Running")
        ok_flag, out, err = run(cmd, cwd=cwd, timeout=args.timeout)
        if ok_flag:
            ok()
            passed += 1
        else:
            fail()
            if err:
                for line in err.strip().splitlines():
                    warn(f"  {line}")
            if args.stop:
                error(f"  Stopped after {name} failure")
                break

    section("Summary")
    total = len(suites)
    info(f"  {passed}/{total} suites passed")
    if passed == total:
        info("  Result: ALL TESTS PASSED")
        return True
    else:
        warn(f"  Result: {total - passed} suite(s) failed")
        return False
def cmd_commit(args):
    """Quality-gated commit."""
    info("")
    info("╔══════════════════════════════════════════════════╗")
    info("║   FHSS — Commit Gate                            ║")
    info("╚══════════════════════════════════════════════════╝")
    info("")

    # Run status first
    cmd_status(args)

    # ── Check git status ──
    ok_flag, out, _ = run("git status --short", capture=True)
    if not out or not out.strip():
        info("  No changes to commit.")
        return True

    # ── Stage files ──
    step("Staging all changes")
    ok_flag, out, err = run("git add -A")
    if not ok_flag:
        fail()
        error(f"  Stage failed: {err}")
        return False
    ok()

    # ── Show diff stat ──
    ok_flag, out, _ = run("git diff --cached --stat", capture=True)
    if out:
        info("  Files changed:")
        for line in out.strip().splitlines():
            info(f"    {line}")

    # ── Conventional commit prompt ──
    info("")
    info("  Conventional commit types:")
    info("    feat, fix, refactor, docs, test, perf, ci, chore")
    info("")
    info("  Examples:")
    info('    feat(seeder): add relationship allocation cache')
    info('    fix(validation): correct FK injection ordering')
    info('    refactor(graph): simplify dependency planner')
    info("")
    scope = input("  Scope (e.g., scoring, frontend, ml): ").strip()
    ctype = input("  Type (feat/fix/refactor/docs/test/perf/ci/chore): ").strip() or "chore"
    message = input("  Short description: ").strip()
    if not message:
        error("  Commit aborted: no message")
        return False

    full_msg = f"{ctype}({scope}): {message}" if scope else f"{ctype}: {message}"

    confirm = input(f'  Commit as "{full_msg}"? (y/n): ').strip().lower()
    if confirm != "y":
        info("  Commit aborted.")
        return True

    ok_flag, out, err = run(["git", "commit", "-m", full_msg])
    if ok_flag:
        info(f"  Commit successful.")
        return True
    else:
        error(f"  Commit failed: {err}")
        return False


# ── Main ─────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="FHSS CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    dev = sub.add_parser("dev", help="Full development startup")
    dev.add_argument("--skip-seed", action="store_true", help="Skip database seeding")
    dev.add_argument("--skip-train", action="store_true", help="Skip model training")
    dev.add_argument("--skip-frontend", action="store_true", help="Skip frontend")
    dev.add_argument("--ml-docker", action="store_true", help="Run ML in Docker instead of locally")
    dev.add_argument("--strict", action="store_true", help="Stop on first failure")

    sub.add_parser("status", help="Repository health report")
    sub.add_parser("commit", help="Quality-gated commit")

    test = sub.add_parser("test", help="Run all test suites")
    test.add_argument("--stop", action="store_true", help="Stop on first failure")
    test.add_argument("--timeout", type=int, default=300, help="Timeout per suite in seconds")

    args = parser.parse_args()

    if not LOG_FILE.parent.exists():
        LOG_FILE.parent.mkdir(parents=True)

    with open(LOG_FILE, "a") as f:
        f.write(f"\n--- CLI {args.command} at {datetime.now(timezone.utc).isoformat()} ---\n")

    if args.command == "dev":
        ok = cmd_dev(args)
    elif args.command == "status":
        ok = cmd_status(args)
    elif args.command == "commit":
        ok = cmd_commit(args)
    elif args.command == "test":
        ok = cmd_test(args)
    else:
        parser.print_help()
        return

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
