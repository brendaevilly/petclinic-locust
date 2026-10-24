#!/usr/bin/env python3
"""Executa os 60 experimentos do Trabalho 06 (2 perfis × 3 cenários × 10 repetições).

O aquecimento é o tempo de subida dos usuários. Com --reset-stats o Locust zera
as estatísticas ao terminar o spawn; o --run-time inclui o aquecimento, então
o tempo total de cada execução é warmup + duration.

Exemplo (valores do enunciado):
  python scripts/run_experiments.py

Smoke test:
  python scripts/run_experiments.py --warmup 10 --duration 20 --repeats 1
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCUSTFILE = ROOT / "locustfile.py"
RESULTS = ROOT / "results"
RAW = RESULTS / "raw"

PROFILES = {
    "read": "ReadProfile",
    "write": "WriteProfile",
}

SCENARIOS = {
    "A": 30,
    "B": 80,
    "C": 150,
}

CPU_CONTAINERS = ("api-gateway", "customers-service", "vets-service")
HOST_DEFAULT = "http://localhost:8080"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Runner dos experimentos Locust")
    parser.add_argument("--host", default=HOST_DEFAULT)
    parser.add_argument("--warmup", type=int, default=60, help="Aquecimento em segundos (spawn)")
    parser.add_argument("--duration", type=int, default=360, help="Duração medida em segundos")
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--cooldown", type=int, default=20, help="Pausa entre execuções (s)")
    parser.add_argument("--cpu-interval", type=float, default=5.0)
    parser.add_argument("--profiles", nargs="+", choices=list(PROFILES), default=list(PROFILES))
    parser.add_argument("--scenarios", nargs="+", choices=list(SCENARIOS), default=list(SCENARIOS))
    parser.add_argument("--start-repeat", type=int, default=1)
    parser.add_argument(
        "--restart",
        choices=("always", "config", "never"),
        default="always",
        help="always: a cada repetição; config: só ao mudar perfil/cenário; never: não reinicia",
    )
    parser.add_argument("--skip-restart", action="store_true", help="Equivalente a --restart never")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def wait_http(url: str, timeout: int = 180) -> None:
    deadline = time.time() + timeout
    last_error = "sem resposta"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if 200 <= response.status < 400:
                    return
                last_error = f"HTTP {response.status}"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
        time.sleep(2)
    raise RuntimeError(f"Serviço indisponível em {url}: {last_error}")


def restart_customers() -> None:
    subprocess.run(["docker", "restart", "customers-service"], check=True, cwd=ROOT)
    wait_http("http://localhost:8081/actuator/health", timeout=180)
    wait_http("http://localhost:8080/api/customer/owners", timeout=180)


def docker_cpu_once() -> dict[str, float]:
    fmt = "{{.Name}},{{.CPUPerc}}"
    completed = subprocess.run(
        ["docker", "stats", "--no-stream", "--format", fmt, *CPU_CONTAINERS],
        check=True,
        capture_output=True,
        text=True,
    )
    usage: dict[str, float] = {}
    for line in completed.stdout.splitlines():
        if not line.strip() or "," not in line:
            continue
        name, perc = line.split(",", 1)
        usage[name.strip()] = float(perc.strip().replace("%", "").replace(",", "."))
    return usage


class CpuSampler:
    def __init__(self, interval: float) -> None:
        self.interval = interval
        self.samples: list[dict] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop.clear()
        self.samples = []
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> list[dict]:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.interval + 5)
        return self.samples

    def _run(self) -> None:
        while not self._stop.is_set():
            timestamp = datetime.now(timezone.utc).isoformat()
            try:
                usage = docker_cpu_once()
                row = {"timestamp": timestamp, **usage}
                self.samples.append(row)
            except Exception as exc:  # noqa: BLE001
                self.samples.append({"timestamp": timestamp, "error": str(exc)})
            self._stop.wait(self.interval)


def write_cpu_csv(path: Path, samples: list[dict]) -> dict[str, float]:
    fieldnames = ["timestamp", *CPU_CONTAINERS, "error"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for sample in samples:
            writer.writerow(sample)

    averages: dict[str, float] = {}
    for container in CPU_CONTAINERS:
        values = [float(sample[container]) for sample in samples if container in sample]
        averages[container] = sum(values) / len(values) if values else float("nan")
    return averages


def locust_command(args: argparse.Namespace, profile: str, users: int, out_prefix: Path) -> list[str]:
    spawn_rate = max(users / max(args.warmup, 1), 0.1)
    total_seconds = args.warmup + args.duration
    return [
        sys.executable,
        "-m",
        "locust",
        "-f",
        str(LOCUSTFILE),
        PROFILES[profile],
        "--headless",
        "--host",
        args.host,
        "-u",
        str(users),
        "-r",
        f"{spawn_rate:.4f}",
        "--run-time",
        f"{total_seconds}s",
        "--reset-stats",
        "--skip-log-setup",
        "--csv",
        str(out_prefix),
        "--csv-full-history",
    ]


def run_one(
    args: argparse.Namespace,
    profile: str,
    scenario: str,
    repeat: int,
    do_restart: bool,
) -> None:
    users = SCENARIOS[scenario]
    run_id = f"{profile}_{scenario}_r{repeat:02d}"
    out_dir = RAW / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = out_dir / "locust"
    meta_path = out_dir / "meta.json"

    meta = {
        "profile": profile,
        "user_class": PROFILES[profile],
        "scenario": scenario,
        "users": users,
        "repeat": repeat,
        "warmup_seconds": args.warmup,
        "duration_seconds": args.duration,
        "host": args.host,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    if do_restart:
        print(f"[{run_id}] reiniciando customers-service para isolar a configuração")
        restart_customers()

    command = locust_command(args, profile, users, prefix)
    print(f"[{run_id}] {' '.join(command)}")
    if args.dry_run:
        meta["dry_run"] = True
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return

    sampler = CpuSampler(args.cpu_interval)
    sampler.start()
    try:
        completed = subprocess.run(command, cwd=ROOT, check=False)
        meta["locust_exit_code"] = completed.returncode
    finally:
        samples = sampler.stop()

    # Descarta amostras do aquecimento (spawn).
    cutoff = args.warmup
    measured = []
    if samples:
        started = time.time()  # fallback
        try:
            first_ts = datetime.fromisoformat(samples[0]["timestamp"])
            started = first_ts.timestamp()
        except Exception:  # noqa: BLE001
            pass
        for sample in samples:
            try:
                ts = datetime.fromisoformat(sample["timestamp"]).timestamp()
                if ts - started >= cutoff:
                    measured.append(sample)
            except Exception:  # noqa: BLE001
                measured.append(sample)

    averages = write_cpu_csv(out_dir / "cpu.csv", measured or samples)
    meta["cpu_avg_percent"] = averages
    meta["cpu_samples"] = len(measured or samples)
    meta["finished_at"] = datetime.now(timezone.utc).isoformat()
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[{run_id}] CPU média: {averages}")


def main() -> int:
    args = parse_args()
    RESULTS.mkdir(exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)

    restart_mode = "never" if args.skip_restart else args.restart
    print(
        f"Host={args.host} warmup={args.warmup}s duration={args.duration}s "
        f"repeats={args.repeats} restart={restart_mode}"
    )
    wait_http(f"{args.host}/api/customer/owners")
    wait_http(f"{args.host}/api/vet/vets")

    planned = []
    for profile in args.profiles:
        for scenario in args.scenarios:
            for repeat in range(args.start_repeat, args.repeats + 1):
                planned.append((profile, scenario, repeat))

    print(f"Total de execuções: {len(planned)}")
    previous_key = None
    for index, (profile, scenario, repeat) in enumerate(planned, start=1):
        print(f"\n=== {index}/{len(planned)} {profile} {scenario} rep {repeat} ===")
        key = (profile, scenario)
        if restart_mode == "always":
            do_restart = True
        elif restart_mode == "config":
            do_restart = key != previous_key
        else:
            do_restart = False
        run_one(args, profile, scenario, repeat, do_restart)
        previous_key = key
        if index < len(planned) and args.cooldown > 0 and not args.dry_run:
            time.sleep(args.cooldown)

    print("\nConcluído. Execute: python scripts/analyze_results.py")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
