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
SIZES_MIB = [2, 4, 6, 8, 10]

REFERENCE = Path.home() / "Desktop" / "F8748-dump" / "rootfs1.bin"

if not REFERENCE.is_file():
    raise SystemExit("[ERRO] rootfs1.bin nao encontrado.")

available = REFERENCE.stat().st_size - OFFSET
print(f"[INFO] Dados de referencia disponiveis: {max(0, available) / 1048576:.2f} MiB")
print("[INFO] Blocos sem referencia completa serao testados apenas por tamanho.")

password = getpass.getpass("Password SSH temporaria: ")

transport = None
results = []

try:
    transport, channel = mod.open_root_shell(
        HOST, USER, password, attempts=1
    )

    for mib in SIZES_MIB:
        size = mib * 1048576
        print(f"\n[TESTE] {mib} MiB")

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

        if len(data) != size:
            print(f"[PARADO] Bloco incompleto: {len(data)}/{size}")
            break

        if available >= size:
            with REFERENCE.open("rb") as f:
                f.seek(OFFSET)
                expected = f.read(size)

            if data != expected:
                print("[PARADO] Dados diferentes do dump existente.")
                print("[RECEBIDO]", hashlib.sha256(data).hexdigest())
                print("[ESPERADO]", hashlib.sha256(expected).hexdigest())
                break

            validation = "Identico ao dump existente"
        else:
            validation = "Tamanho correto; conteudo sem referencia independente"

        speed = mib / elapsed

        print(f"[OK] {mib} MiB recuperados")
        print(f"[TEMPO] {elapsed:.2f} segundos")
        print(f"[VELOCIDADE] {speed:.3f} MiB/s")
        print(f"[VALIDACAO] {validation}")

        results.append((mib, elapsed, speed, validation))

        time.sleep(1)

finally:
    if transport is not None:
        transport.close()

print("\n========== RESULTADOS ==========")

for mib, elapsed, speed, validation in results:
    print(
        f"{mib:>2} MiB | "
        f"{elapsed:>7.2f} s | "
        f"{speed:>7.3f} MiB/s | {validation}"
    )

if results:
    best = max(results, key=lambda x: x[2])
    print(f"\n[MELHOR] {best[0]} MiB ({best[2]:.3f} MiB/s)")
else:
    print("\nNenhum bloco adicional validado.")
