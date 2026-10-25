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

# Zona ja extraida, para validar os bytes recebidos
OFFSET = 0x10000
SIZES = [32768, 49152, 65536, 98304, 131072]

REFERENCE = Path.home() / "Desktop" / "F8748-dump" / "rootfs1.bin"

if not REFERENCE.is_file():
    raise SystemExit("[ERRO] Nao encontrei rootfs1.bin")

available = REFERENCE.stat().st_size - OFFSET

if available < max(SIZES):
    raise SystemExit(
        f"[ERRO] Ficheiro de referencia demasiado pequeno: "
        f"{REFERENCE.stat().st_size} bytes"
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
            print(f"\n[TESTE] {size // 1024} KiB")

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
                print(
                    f"[PARADO] Bloco incompleto: "
                    f"{len(data)}/{size} bytes"
                )
                break

            if data != expected:
                print("[PARADO] Os dados diferem do dump existente.")
                print("[RECEBIDO]", hashlib.sha256(data).hexdigest())
                print("[ESPERADO]", hashlib.sha256(expected).hexdigest())
                break

            speed = (size / 1024) / elapsed

            print(f"[OK] {size // 1024} KiB")
            print(f"[TEMPO] {elapsed:.2f} segundos")
            print(f"[VELOCIDADE] {speed:.2f} KiB/s")
            print("[VALIDACAO] Identico ao dump existente")

            results.append((size // 1024, elapsed, speed))

            # Pequena pausa entre testes
            time.sleep(1)

finally:
    if transport is not None:
        transport.close()

print("\n========== RESULTADOS ==========")

for size, elapsed, speed in results:
    print(
        f"{size:>3} KiB | "
        f"{elapsed:>7.2f} s | "
        f"{speed:>7.2f} KiB/s"
    )

if results:
    best = max(results, key=lambda x: x[2])
    print(
        f"\n[MELHOR] {best[0]} KiB "
        f"({best[2]:.2f} KiB/s)"
    )
else:
    print("\nNenhum tamanho adicional validado.")
