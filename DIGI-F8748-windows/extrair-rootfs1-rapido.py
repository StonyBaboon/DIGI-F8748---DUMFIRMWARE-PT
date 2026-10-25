import importlib.util
import getpass
import hashlib
import time
from pathlib import Path

spec = importlib.util.spec_from_file_location("digi", "digi-f8748.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

HOST = "192.168.1.1"
USER="ObN13844"
DEVICE = "/dev/mtd9"
TOTAL = 0x04A80000
CHUNK=1*1024*1024

folder = Path.home() / "Desktop" / "F8748-dump"
folder.mkdir(parents=True, exist_ok=True)

dest = folder / "rootfs1.bin"
previous = folder / "rootfs1-primeiros-64KiB.bin"

# Aproveitar a primeira extracao, se ainda nao existir rootfs1.bin
if not dest.exists():
    if previous.exists() and previous.stat().st_size == 65536:
        dest.write_bytes(previous.read_bytes())
        print("[OK] Importados os primeiros 64 KiB.")
    else:
        dest.touch()

current = dest.stat().st_size

if current > TOTAL:
    raise SystemExit("[ERRO] O ficheiro e maior do que a particao.")

# O extrator anterior gravava blocos completos de 8192 bytes.
if current % 8192:
    raise SystemExit(
        "[ERRO] Tamanho nao alinhado a 8192 bytes. "
        "Nao vou continuar automaticamente."
    )

print("[PARTICAO]", DEVICE)
print("[TOTAL]", TOTAL, "bytes")
print("[EXISTENTE]", current, "bytes")
print("[EM FALTA]", TOTAL - current, "bytes")
print("[BLOCO MAXIMO]", CHUNK, "bytes")

if current == TOTAL:
    print("[OK] A extracao ja esta completa.")
    raise SystemExit(0)

password = getpass.getpass("Password SSH temporaria: ")

transport = None
started = time.monotonic()

try:
    transport, channel = mod.open_root_shell(
        HOST,
        USER,
        password,
        attempts=1
    )

    with dest.open("ab") as output:
        offset = current

        while offset < TOTAL:
            size = min(CHUNK, TOTAL - offset)

            print(
                f"\n[LER] Offset {offset:#x} | "
                f"{size / 1048576:.2f} MiB"
            )

            block_start = time.monotonic()

            data = mod.mtd_pull(
                channel,
                DEVICE,
                offset,
                size,
                size,
                "/var/tmp/digi_benchmark.bin"
            )

            if len(data) != size:
                raise RuntimeError(
                    f"Bloco incompleto em {offset:#x}: "
                    f"{len(data)}/{size} bytes"
                )

            output.write(data)
            output.flush()

            offset += size
            elapsed = time.monotonic() - block_start

            print(
                f"[OK] {offset / 1048576:.2f}/"
                f"{TOTAL / 1048576:.2f} MiB "
                f"({100 * offset / TOTAL:.1f}%) "
                f"| bloco em {elapsed:.2f}s"
            )

    print("\n[SUCESSO] Extracao concluida.")
    print("[FICHEIRO]", dest)
    print("[TAMANHO]", dest.stat().st_size, "bytes")
    print("[TEMPO TOTAL]", round(time.monotonic() - started, 2), "segundos")

    h = hashlib.sha256()
    with dest.open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)

    print("[SHA256]", h.hexdigest())

except Exception as e:
    print("\n[INTERROMPIDO]", type(e).__name__, str(e))
    print("[GUARDADO]", dest)
    print("[BYTES]", dest.stat().st_size)
    print("[INFO] Os blocos completos foram preservados.")

finally:
    if transport is not None:
        transport.close()


