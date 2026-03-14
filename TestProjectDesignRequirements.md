TestProject design input:

* A WiFi-enabled controller for classic Marklin AC model trains. The module
sits inside (or replaces) the locomotive's existing electronics, is powered
directly from the 24 VAC rail voltage, and exposes motor control via
Modbus TCP over WiFi.
* A simple and readily available microcontroller should be used, that is well supported and have good sw and IDE available.
* Software development is not a part of this project, but the sw support for the chosen CPU/MCU must be considered.
* Components shall as far as possible be SMT, passives in 0603 packages.
* AC output signal must be controlled on both positive and negative side of the sine wave.
* In/Out signals from the board shall be solder points, not connectors as that will be too large.
