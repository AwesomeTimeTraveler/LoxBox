# LoxBox – Source Code Overview

This folder contains the operational code (**Version "1"**) for the LoxBox incubator system.  
It manages temperature, O₂, and CO₂ control, provides both console and hardware display interfaces,  
and handles logging for monitoring and troubleshooting.

---

## 📂 File Structure

### `main.py`
- Entry point of the system.
- Loads configuration from `config.yaml`.
- Initializes GPIO, sensors, displays, and controllers.
- Starts the **curses-based UI** (`ui_curses.py`) and supervises restarts on crash.
- Handles safe shutdown (forcing GPIO low, cleaning up).

### `config.yaml`
- Human-readable configuration file.
- Defines:
  - GPIO pin assignments.
  - Target setpoints (temperature, O₂, CO₂).
  - Thresholds for control bands (continuous vs pulsed).
  - PID tuning parameters.
  - Logging paths and options.

### `controllers.py`
- Implements **control logic**:
  - `HeaterController`: PID-based PWM control for heater relays.
  - `GasController`: Bang-bang logic with pulse/settle cycles for O₂/CO₂ solenoids.  
    Includes special handling for CO₂ overshoot mitigation (short pulses, rise suppression).
- Tracks last state (ON/OFF) for logging.

### `sensors.py`
- Interfaces with physical sensors:
  - `OneWireTemps`: Reads temperature from 1-Wire devices (DS18B20 or similar).
  - `SerialGas`: Reads O₂ and CO₂ sensors via UART/USB serial, parses values, applies scaling.
- Includes error handling to raise exceptions for malformed or missing data.

### `display.py`
- Manages I²C **7-segment LED displays** for live readouts of O₂, CO₂, and temperature.
- `DisplaySupervisor`: Provides safe `print` to displays, with fallback if hardware errors occur.

### `ui_curses.py`
- Provides a **curses-based UI** in the terminal:
  - Displays live sensor values and colored status bars.
  - Maps controller states to colors for quick monitoring.
  - Updates I²C displays in sync with the terminal UI.
  - Logs structured data (`.log` and `.csv`) every cycle.
- Allows user to quit with `q`.

### `force_gpio_off.py`
- Utility script to safely force all control pins LOW.
- Used in shutdown/service stop to ensure heaters and solenoids are turned off.

---

## ⚙️ General Workflow

1. **Startup** (`main.py`):
   - Load `config.yaml`.
   - Initialize GPIO, sensors, and controllers.
   - Start curses UI loop.

2. **Control Loop** (`ui_curses.py`):
   - Every cycle (~1 s):
     - Read temperature, O₂, and CO₂ sensors.
     - Update heater (PID PWM).
     - Update O₂ controller (priority: purge if too high).
     - Update CO₂ controller (pulsed micro-dosing with settle/rise suppression).
     - Refresh terminal UI and I²C displays.
     - Log to `.log` (human-readable) and `.csv` (structured).

3. **Shutdown**:
   - On exit or crash, GPIO is forced LOW (via `force_gpio_off.py` or signal handler).
   - Ensures all relays and solenoids are turned off safely.

---

## 🧪 Usage

```bash
# Run the incubator control loop
python3 main.py

# Test O₂ solenoid/sensor only
python3 manual_o2_test.py

# Force all GPIO outputs LOW (safety)
python3 force_gpio_off.py
```
