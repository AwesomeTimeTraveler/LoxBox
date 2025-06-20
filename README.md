![image](https://github.com/user-attachments/assets/4246c3a4-7e26-4cae-9302-62b492628352)
# Low-Oxygen, Dual-Gas DIY Field Incubator

A low-cost, beer-cooler-turned-CO₂/O₂/temperature-controlled incubator for mammalian cell culture, running on a Raspberry Pi 3B+.

---

## Features

- **Temperature control** via 6 × 12 V 20W heater panels and PID  
- **Gas control**  
  - Nitrogen purge to displace O₂ down to ~2%  
  - CO₂ injection to maintain ~5%  
  - Dual-mode (continuous vs. pulse) logic for coarse/fine tuning  
- **Real-time UI** in terminal (curses) + three 7-segment I²C displays  
- **Resilient**:  
  - Auto-restart on UI crash  
  - Graceful handling of serial, 1-Wire, I²C errors  
  - Rotating file logging  
- **Runs at boot** under `systemd`

---

## Hardware Overview

| Function       | Part                                                                 | Qty | Cost (ea) |
| -------------- | -------------------------------------------------------------------- | --- | --------- |
| Brain          | [Raspberry Pi 3b+](https://www.raspberrypi.com/products/raspberry-pi-3-model-b-plus/) ($35) (1 GB RAM, 64 GB SD)                         | 1   | \$35       |
| Heaters        | [12 V 20 W silicone panels](https://www.amazon.com/Silicone-Flexible-Industrial-Equipment-50x150mm/dp/B0BKL824TN/ref=sr_1_2?sr=8-2) + [aluminum heatsinks](https://www.amazon.com/Awxlumv-Aluminum-60x150x25mm-2-36x5-91x0-98-Amplifier/dp/B07VDHQDQT/ref=sr_1_2?sr=8-2)                       | 6   | \$24       |
| Temp Sensors   | [DS18B20 waterproof 1-Wire](https://www.adafruit.com/product/381)                                            | 6   | \$10       |
| CO₂ Sensor     | [ExplorIR-M 0–20 % CO₂](https://www.co2meter.com/products/explorir-20-co2-smart-led-sensor?variant=43960991842502) via UART                                       | 1   | \$250      |
| O₂ Sensor      | [LOX-O2 LuminOx 0–25 % O₂](https://www.co2meter.com/products/25-percent-oxygen-sensor?variant=43960891277510) via UART                                       | 1   | \$274      |
| UART Interface | [TDI 232 chip](https://www.amazon.com/Communication-Connector-Compatible-Supports-Android/dp/B09F6FGMD7/ref=sr_1_3?sr=8-3)                                                         | 1   | \$13       |
| Relays         | 2 channel 12 V [SPDT modules](https://www.amazon.com/Electronics-Salon-10Amp-Power-Module-Version/dp/B014F6EEVK/ref=sr_1_9?sr=8-9) for heaters + solenoids                  | 2   | \$14       |
| Solenoids      | [US Solid 1/4″ NPT brass, normally-closed, 12 V](https://ussolid.com/products/u-s-solid-electric-solenoid-valve-1-4-12v-dc-solenoid-valve-brass-body-normally-closed-viton-seal-html)                                | 2   | \$17       |
| Power          | 65 W dual USB-C adapter + USB-C→barrel cables                        | —   | \$32       |
| Displays       | Adafruit HT16K33 4-digit 7-segment I²C backpacks                     | 3   | \$12       |
| Misc.          | [Wago connectors](https://www.adafruit.com/product/5616), [perfboard](https://www.adafruit.com/product/1609?gad_campaignid=21079227318), wiring, waterproof [Deutsch connector](https://www.digikey.com/en/products/detail/te-connectivity-deutsch-ict-connectors/DT04-12PA-LE14/10461760),[crimper](https://www.amazon.com/Knoweasy-KN-16-Crimping-Impression-Contacts/dp/B09Z6Q6K4W/ref=sr_1_8?sr=8-8)     | —   | \$70       |

---

## Software Dependencies

- **Python 3.8+**  
- OS: **Raspberry Pi OS** (64-bit)  
- System packages:
```bash
sudo apt update && sudo apt install -y \
  python3-pip python3-serial python3-yaml python3-curses \
  python3-rpi.gpio i2c-tools
```

- Python libraries (in a venv or globally):
```
pip3 install \
  w1thermsensor simple-pid adafruit-circuitpython-ht16k33 \
  pyserial pyyaml
```

Enable 1-Wire & I²C in raspi-config.

# Quick Start
1. Clone Repo
 ```
 git clone https://github.com/AwesomeTimeTraveler/LoxBox
 cd LoxBox
 ```
   
2. Configure
  Edit `config.yaml` with your GPIO pins, setpoints, thresholds, PID gains, etc.

3. Install systemd service

```
sudo cp incubator.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable incubator.service
sudo systemctl start incubator.service
```
Logs ⇒ `journalctl -fu incubator.service`

4. Manual run (for testing)

```
source env/bin/activate         # if using a venv
python3 main.py
```

# Wiring
**Heaters:** 6 panels in parallel → 12 V relay common → GPIO pins (e.g. BCM 13, 19)

**Solenoids:** N₂ on BCM 20, CO₂ on BCM 21 via SPDT relays

**DS18B20:** All in parallel on BCM 4 + 1 kΩ pull-up

**Gas sensors (UART):**

- CO₂ → `/dev/ttyS0` (Pi’s UART)

- O₂ → USB-UART → `/dev/ttyUSB0`

**I²C displays:** SCL/SDA to Pi I²C pins; addresses `0x70`, `0x71`, `0x72`


# System Logic
## 1. Startup:
- Heat ramp to 37 °C (PID)
- Nitrogen purge (continuous) until O₂ < 2.5%
- Then switch to normal control

## 2. Operational:
- Heaters under PID throttling (slow relay cycles + hysteresis)
- N₂ valve:
  - Continuous when O₂ > 125% × setpt
  - Pulsed at 50% duty for 10% band
- CO₂ valve:
  - Continuous when CO₂ < 75% × setpt
  - Pulsed for 10% band
- UI: curses bars + three 7-segment displays
- ~*Safety*~: All relays off on crash, on shutdown signals

# Troubleshooting
- No I²C devices ⇒ `i2cdetect -y 1`
- 1-Wire not found ⇒ enable in raspi-config, reboot
- Serial errors ⇒ check `/dev/serial0` & `/dev/ttyUSB0` permissions
- Logs ⇒ `tail -n50 incubator.log` or `journalctl -u incubator.service`
