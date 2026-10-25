import importlib.util
import getpass
import hashlib
from pathlib import Path

spec = importlib.util.spec_from_file_location("digi", "digi-f8748.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

DEVICE = "/dev/mtd9"
TOTAL = 0x04A80000
CHUNK = 8192

folder = Path.home() / "Desktop" / "F8748-dump"
folder.mkdir(parents=True, exist_ok=True)

dest = folder / "rootfs1.bin"
previous = folder / "rootfs1-primeiros-64KiB.bin"

if not dest.exists() and previous.exists():
    initial = previous.read_bytes()
    if len(initial) != 65536:
        raise RuntimeError("O ficheiro inicial nao tem 65536 bytes.")
    dest.write_bytes(initial)
    print("[OK] Importados os primeiros 64 KiB.")

current = dest.stat().st_size if dest.exists() else 0

if current > TOTAL or current % CHUNK:
    raise RuntimeError(
        f"Tamanho inesperado do ficheiro: {current}. "
        "Nao e seguro continuar automaticamente."
    )

print(f"[INFO] Particao: {DEVICE}")
print(f"[INFO] Total: {TOTAL} bytes")
print(f"[INFO] Ja guardados: {current} bytes")
print(f"[INFO] Em falta: {TOTAL - current} bytes")

if current == TOTAL:
    print("[OK] A particao ja esta completa.")
    raise SystemExit(0)

password = getpass.getpass("Password SSH temporaria: ")
transport = None

try:
    transport, channel = mod.open_root_shell(
        "192.168.1.1",
        "zDt9dhn9",
        password,
        attempts=1
    )

    with dest.open("ab") as f:
        for offset in range(current, TOTAL, CHUNK):
            size = min(CHUNK, TOTAL - offset)

            data = mod.mtd_pull(
                channel,
                DEVICE,
                offset,
                size,
                size,
                "/var/tmp/digi_probe.bin"
            )

            if len(data) != size:
                raise RuntimeError(
                    f"Bloco incompleto em {offset:#x}: "
                    f"{len(data)}/{size} bytes"
                )

            f.write(data)
            f.flush()

            completed = offset + size

            if completed % (1024 * 1024) == 0 or completed == TOTAL:
                print(
                    f"[OK] {completed}/{TOTAL} bytes "
                    f"({100 * completed / TOTAL:.1f}%)"
                )

    print("\n[SUCESSO] Particao extraida:", dest)

    h = hashlib.sha256()
    with dest.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)

    print("[SHA256]", h.hexdigest())

except Exception as e:
    print("\n[INTERROMPIDO]", type(e).__name__, str(e))
    print("[INFO] Os blocos completos continuam guardados em:", dest)
    print("[INFO] Podes repetir este script para retomar.")

finally:
    if transport is not None:
        transport.close()
