import importlib.util
import getpass
import hashlib
from pathlib import Path

spec = importlib.util.spec_from_file_location("digi", "digi-f8748.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

HOST = "192.168.1.1"
CHUNK = 1024 * 1024

PARTITIONS = [
    ("kernel1", "/dev/mtd7",  0x05000000),
    ("kernel2", "/dev/mtd8",  0x05000000),
    ("rootfs2", "/dev/mtd10", 0x04FE0000),
    ("u-boot",  "/dev/mtd1",  0x00300000),
]

DEST = Path.home() / "Desktop" / "F8748-dump"
DEST.mkdir(parents=True, exist_ok=True)

user = input("Utilizador SSH temporario: ").strip()
password = getpass.getpass("Password SSH temporaria: ")

transport = None

try:
    transport, channel = mod.open_root_shell(
        HOST, user, password, attempts=1
    )

    for name, device, total in PARTITIONS:
        output = DEST / (name + ".bin")
        existing = output.stat().st_size if output.exists() else 0

        if existing > total or existing % 8192:
            raise RuntimeError(
                f"Tamanho inesperado em {output}: {existing} bytes"
            )

        print(f"\n[PARTICAO] {name} ({device})")
        print(f"[TOTAL] {total} bytes")
        print(f"[EXISTENTE] {existing} bytes")

        with output.open("ab") as f:
            offset = existing

            while offset < total:
                size = min(CHUNK, total - offset)

                print(
                    f"[LER] {name} @ {offset:#x} | "
                    f"{size / 1048576:.2f} MiB",
                    flush=True
                )

                data = mod.mtd_pull(
                    channel,
                    device,
                    offset,
                    size,
                    size,
                    "/var/tmp/digi_benchmark.bin"
                )

                if len(data) != size:
                    raise RuntimeError(
                        f"Bloco incompleto: {len(data)}/{size}"
                    )

                f.write(data)
                f.flush()
                offset += size

                print(
                    f"[OK] {name}: "
                    f"{offset / 1048576:.2f}/"
                    f"{total / 1048576:.2f} MiB",
                    flush=True
                )

        sha = hashlib.sha256()

        with output.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                sha.update(block)

        print(f"[CONCLUIDO] {output}")
        print(f"[SHA256] {sha.hexdigest()}")

except Exception as e:
    print(f"\n[INTERROMPIDO] {type(e).__name__}: {e}")
    print("[INFO] Os blocos completos foram preservados.")

finally:
    if transport is not None:
        transport.close()
