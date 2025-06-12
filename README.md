![image](https://github.com/user-attachments/assets/4246c3a4-7e26-4cae-9302-62b492628352)

Field cell culture incubator running Python - built out of a beer cooler with a Raspberry pi.

# Dependencies


# Enabling systemctl service 
Copy the contents of `incubator.service` to the systemd directory:
`sudo nano /etc/systemd/system/incubator.service`

Enable and start the systemctl service:
```
sudo systemctl daemon-reload
sudo systemctl enable incubator.service
sudo systemctl start incubator.service
```

- Start at boot.
- Gracefully handle serial, 1-Wire, and I²C errors.
- Prioritize N₂ displacement on startup.
- Use PID for heater control.
- Auto‐restart on any UI crash.
- Log to a rotating file.

To watch logs: `journalctl -fu incubator.service`


# Hardware 
## Brains
[Raspberry Pi 3b+](https://www.raspberrypi.com/products/raspberry-pi-3-model-b-plus/) ($35) w/ 1GB RAM and a 64GB Sandisk microSD card ($6)

## Heaters

Heating is provided by an array of 6 20W silicone 12V DC [heater panels](https://www.amazon.com/Silicone-Flexible-Industrial-Equipment-50x150mm/dp/B0BKL824TN/ref=sr_1_2?sr=8-2) ($24) each attached to a 24 fin, 60x150x25mm [aluminum heatsinks](https://www.amazon.com/Awxlumv-Aluminum-60x150x25mm-2-36x5-91x0-98-Amplifier/dp/B07VDHQDQT/ref=sr_1_2?sr=8-2) ($9.99 x6).

## Senses
### Temperature
To control the heaters, I use an array of waterproof 1-wire interfaced [DS18B20 temperature sensors](https://www.adafruit.com/product/381) ($9.95 x5). Wires are meshed via 2 layers of 3-1 and 2-1 [Wago flip connectors](https://www.adafruit.com/product/5616) ($1.95 x6) and feed signal to GPIO with a 1kOhm resistor ($0.1) wired on an [Adafruit PermaProto perfboard](https://www.adafruit.com/product/1609?gad_campaignid=21079227318) ($3.33) with jumper cable headers ($.1 x3).

### Gas  
I chose the [ExplorIR®-M 20% CO2 Sensor](https://www.co2meter.com/products/explorir-20-co2-smart-led-sensor?variant=43960991842502) (~$250 at time) and [LOX-O2 UV Flux 25% Oxygen Smart Sensor](https://www.co2meter.com/products/25-percent-oxygen-sensor?variant=43960891277510) ($273.90) as MX board units. UART interface.

Prices have been rapidly increased (due to tariffs?), increasing both the cost of the ExplorIR ($394.90) and LOX-O2 ($273.90). The ExplorIR is listed as unavailable now - uncertain prospects.

To interface both UART gas sensors simultaneously, the single UART pinout of the Raspberry Pi was expanded using a Wonrabai USB-C-UART interface with an FTDI 232 chip ($12.47) via a USB-C 3.1 to USB-A 3.0 4” cable.

## Solenoids
[US Solid 12V DC solenoid with NPT 1/4"](https://ussolid.com/products/u-s-solid-electric-solenoid-valve-1-4-12v-dc-solenoid-valve-brass-body-normally-closed-viton-seal-html) ($16.55 x2), controlled via GPIO to [Electronics Salon 12V 10A SPDT relays](https://www.amazon.com/Electronics-Salon-10Amp-Power-Module-Version/dp/B014F6EEVK/ref=sr_1_9?sr=8-9) ($13.99 x2) powered off Adafruit [USB-C to 5.5mm barrel cables](https://www.adafruit.com/product/5450) ($7.95 x4) with a 65W dual USB-C power adapter.

## Displays
[Adafruit HT16K33 0.56" 4-Digit 7-Segment Display w/ I2C Backpacks](https://www.adafruit.com/product/881) ($11.95 x3).

XX gauge silicone stranded tin coated wire and standard XX gauge jumper pin cables.
Wiring is run through a [Deutsch DT04 12 position](https://www.digikey.com/en/products/detail/te-connectivity-deutsch-ict-connectors/DT04-12PA-LE14/10461760) waterproof electrical connector using cheap knock-off crimps and a knock-off Deutsch-style [crimper](https://www.amazon.com/Knoweasy-KN-16-Crimping-Impression-Contacts/dp/B09Z6Q6K4W/ref=sr_1_8?sr=8-8).
