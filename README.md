![image](https://github.com/user-attachments/assets/4246c3a4-7e26-4cae-9302-62b492628352)

Field cell culture incubator running Python - built out of a beer cooler with a Raspberry pi

The Python script is wrapped in systemd service to auto-boot on power-up.

## Sensors
### Temperature
Waterproof 1-wire interfaced [DS18B20 temperature sensors](https://www.adafruit.com/product/381) ($9.95 Adafruit) in a 5 sensor array. Wires are meshed via 3 separate [5-1 Wago flip connectors](https://www.adafruit.com/product/5616) ($1.95) and are wired signal to GPIO with a 1kOhm resistor ($0.1).

### Gas  
I chose the [ExplorIR®-M 20% CO2 Sensor](https://www.co2meter.com/products/explorir-20-co2-smart-led-sensor?variant=43960991842502) (~$250 at time) and [LOX-O2 UV Flux 25% Oxygen Smart Sensor](https://www.co2meter.com/products/25-percent-oxygen-sensor?variant=43960891277510) ($273.90) as MX board units. UART interface.

Prices have been rapidly increased (due to tariffs?), increasing both the cost of the ExplorIR ($394.90) and LOX-O2 ($273.90). The ExplorIR is listed as unavailable now - uncertain prospects.

To interface both UART gas sensors simultaneously, the single UART pinout of the Raspberry Pi was expanded using a Wonrabai USB-C-UART interface with an FTDI 232 chip ($12.47) via a USB-C 3.1 to USB-A 3.0 4” cable.

## Solenoids
[US Solid 12V DC solenoid with NPT 1/4"](https://ussolid.com/products/u-s-solid-electric-solenoid-valve-1-4-12v-dc-solenoid-valve-brass-body-normally-closed-viton-seal-html) ($16.55), controlled via GPIO to [Electronics Salon 12V 10A SPDT relays](https://www.amazon.com/Electronics-Salon-10Amp-Power-Module-Version/dp/B014F6EEVK/ref=sr_1_9?sr=8-9) ($13.99) powered off Adafruit USB-C to 5.5mm barrel adapter cables with a 65W dual USB-C power adapter.

## Displays
[Adafruit HT16K33 0.56" 4-Digit 7-Segment Display w/ I2C Backpacks](https://www.adafruit.com/product/881) ($11.95).

XX gauge silicone stranded tin coated wire and standard XX gauge jumper pin cables.
Wiring is run through a [Deutsch DT04 12 position](https://www.digikey.com/en/products/detail/te-connectivity-deutsch-ict-connectors/DT04-12PA-LE14/10461760) waterproof electrical connector using cheap knock-off crimps and a knock-off Deutsch-style [crimper](https://www.amazon.com/Knoweasy-KN-16-Crimping-Impression-Contacts/dp/B09Z6Q6K4W/ref=sr_1_8?sr=8-8).
