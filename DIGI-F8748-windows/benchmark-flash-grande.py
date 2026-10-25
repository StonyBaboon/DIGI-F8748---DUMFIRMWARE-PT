import importlib.util
import getpass
import hashlib
import time
from pathlib import Path

spec = importlib.util.spec_from_file_location("digi", "digi-f8748.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

HOST = "192.168.1.1"
USER = "zDt9dhn9"
DEVICE = "/dev/mtd9"
OFFSET = 0x10000

SIZES = [
    256 * 1024,
    512 * 1024,
    1024 * 1024,
]

REFERENCE = Path.home() / "Desktop" / "F8748-dump" / "rootfs1.bin"

if not REFERENCE.is_file():
    raise SystemExit("[ERRO] rootfs1.bin nao encontrado.")

file_size = REFERENCE.stat().st_size

if file_size < OFFSET + max(SIZES):
    raise SystemExit(
        f"[ERRO] Dump existente demasiado pequeno: {file_size} bytes."
    )

password = getpass.getpass("Password SSH temporaria: ")

transport = None
results = []

try:
    transport, channel = mod.open_root_shell(
        HOST, USER, password, attempts=1
    )

    with REFERENCE.open("rb") as reference:
        for size in SIZES:
            kib = size // 1024

            print(f"\n[TESTE] {kib} KiB")
            start = time.monotonic()

            try:
                data = mod.mtd_pull(
                    channel,
                    DEVICE,
                    OFFSET,
                    size,
                    size,
                    "/var/tmp/digi_benchmark.bin"
                )
            except Exception as e:
                print("[PARADO]", type(e).__name__, str(e))
                break

            elapsed = time.monotonic() - start

            reference.seek(OFFSET)
            expected = reference.read(size)

            if len(data) != size:
                print(f"[PARADO] Tamanho incorreto: {len(data)}/{size}")
                break

            if data != expected:
                print("[PARADO] Dados diferentes do dump existente.")
                print("[RECEBIDO]", hashlib.sha256(data).hexdigest())
                print("[ESPERADO]", hashlib.sha256(expected).hexdigest())
                break

            speed = size / 1024 / elapsed

            print("[OK] Dados identicos")
            print(f"[TEMPO] {elapsed:.2f} segundos")
            print(f"[VELOCIDADE] {speed:.2f} KiB/s")

            results.append((kib, elapsed, speed))
            time.sleep(1)

finally:
    if transport is not None:
        transport.close()

print("\n========== RESULTADOS ==========")

for kib, elapsed, speed in results:
    print(
        f"{kib:>5} KiB | "
        f"{elapsed:>7.2f} s | "
        f"{speed:>8.2f} KiB/s"
    )

if results:
    best = max(results, key=lambda x: x[2])
    print(f"\n[MELHOR] {best[0]} KiB ({best[2]:.2f} KiB/s)")
