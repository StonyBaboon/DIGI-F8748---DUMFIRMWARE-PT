import importlib.util
import getpass
import time

spec = importlib.util.spec_from_file_location("digi", "digi-f8748.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

password = getpass.getpass("Password SSH temporaria: ")
transport = None

try:
    transport = mod.ssh_connect("192.168.1.1", "TBqiUa1t", password)
    channel = transport.open_session()
    channel.get_pty(term="vt100", width=80, height=24)
    channel.invoke_shell()

    time.sleep(1)

    print("\n[RESPOSTA INICIAL]")
    while channel.recv_ready():
        print(repr(channel.recv(65536).decode("latin1", "replace")))

    print("\n[TESTE] cat /proc/self/status")
    result = mod.shell_read(channel, "cat /proc/self/status", 5)
    print(repr(result))

finally:
    if transport is not None:
        transport.close()
