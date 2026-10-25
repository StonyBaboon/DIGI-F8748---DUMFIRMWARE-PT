import importlib.util
import getpass

spec = importlib.util.spec_from_file_location("digi", "digi-f8748.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

user = input("Utilizador SSH: ").strip()
password = getpass.getpass("Password SSH: ")

transport = None

try:
    transport = mod.ssh_connect("192.168.1.1", user, password)

    channel = transport.open_session()
    channel.get_pty(term="vt100", width=80, height=24)
    channel.invoke_shell()

    import time
    time.sleep(0.8)

    print("\n[TESTE 1] Ler 16 bytes da flash para um ficheiro temporario")
    resposta = mod.shell_read(
        channel,
        "mtd_debug read /dev/mtd9 0 16 /var/tmp/digi_probe.bin",
        5
    )
    print(repr(resposta))

    if "Access Denied" not in resposta and "Copied" in resposta:
        print("\n[TESTE 2] Mostrar os 16 bytes")
        resposta = mod.shell_read(
            channel,
            'hexdump -ve \'1/1 "%02x"\' /var/tmp/digi_probe.bin',
            5
        )
        print(repr(resposta))
    else:
        print("\n[PARADO] A leitura foi recusada; nao executar mais comandos.")

except Exception as e:
    print("[ERRO]", type(e).__name__, str(e))

finally:
    if transport is not None:
        transport.close()
