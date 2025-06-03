# LoxBox
Field cell culture incubator running Python - built out of a beer cooler with a Raspberry pi

The Python script is wrapped in systemd service to auto-boot on power-up.

## Sensors
### Temperature
Waterproof 1-wire interfaced DS18B20 temperature sensors ($9.95 Adafruit) in a 5 sensor array. Wires are meshed via a 3 separate 5-1 flip connector and connected via 1kOhm resistor to GPIO

### Gas  
I chose the ExplorIR®-M 20% CO2 Sensor and LOX-O2 UV Flux 25% Oxygen Smart Sensor as MX board units. UART interface.

Prices have been rapidly increased (due to tariffs?), increasing both the cost of the ExplorIR ($394.90) and LOX-O2 ($273.90).

To interface both UART gas sensors simultaneously, the single UART pinout of the Raspberry Pi was expanded using a Wonrabai USB-C-UART interface with an FTDI 232 chip ($12.47) via a USB-C 3.1 to USB-A 3.0 4” cable.

## Solenoids
(US Solid 12V DC solenoid 1/4" )[https://ussolid.com/products/u-s-solid-electric-solenoid-valve-1-4-12v-dc-solenoid-valve-brass-body-normally-closed-viton-seal-html], controlled via GPIO to (Electronics Salon 12V 10A SPDT relays)[Electronics-Salon 2 SPDT 10Amp Power Relay Module, DC 12V Version.] powered off Adafruit USB-C to 5.5mm barrel adapter cables with a 65W dual USB-C power adapter.
