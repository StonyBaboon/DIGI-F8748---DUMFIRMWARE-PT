import importlib.util
import getpass

spec = importlib.util.spec_from_file_location("digi", "digi-f8748.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

user = input("Novo utilizador SSH: ").strip()
password = getpass.getpass("Password SSH: ")

transport = None

try:
    transport, channel = mod.open_root_shell(
        "192.168.1.1", user, password, attempts=1
    )

    print("\n[TESTE] Ler apenas 16 bytes")

    data = mod.mtd_pull(
        channel,
        "/dev/mtd9",
        0,
        16,
        16,
        "/var/tmp/digi_probe.bin"
    )

    print("[OK] Bytes recebidos:", len(data))
    print("[HEX]", data.hex())

except Exception as e:
    print("[FALHOU]", type(e).__name__, str(e))

finally:
    if transport is not None:
        transport.close()
