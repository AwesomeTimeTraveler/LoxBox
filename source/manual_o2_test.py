from sensors import SerialGas
g = SerialGas("/dev/ttyUSB1", "%\r\n", 0.001, baud=9600)
for _ in range(5):
    try:
        print("O₂ →", g.read())
    except Exception:
        import traceback; traceback.print_exc()
    time.sleep(1)
