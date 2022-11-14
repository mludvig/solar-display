# Solar PV dashboard display

## PIN wiring

+----------+--------------------------------+----------+
| Display  |         Raspberry Pi           | Display  |
+----------+--------------------------------+----------+
|          |           | 1 | 2  |           |          |
|  Buzz +  |   GPIO2   | 3 | 4  |   5V      |  5V PIN  |
|          |           | 5 | 6  |   GND     |  GND PIN |
|          |           | 7 | 8  |           |          |
|  Buzz -  |   GND     | 9 | 10 |           |          |
|          |           | 11| 12 |           |          |
|          |           | 13| 14 |   GND     |  GND     |
|          |           | 15| 16 |           |          |
|  VCC     |   3.3V    | 17| 18 |   GPIO24  |  RESET   |
|  SDI     |   MOSI 0  | 19| 20 |           |          |
|  SDO     |   MISO 0  | 21| 22 |   GPIO25  |  DC      |
|  SCK     |   CLK 0   | 23| 24 |   GPIO8   |  CS      |
|          |           | 25| 26 |           |          |
|          |           | 27| 28 |           |          |
|          |           | 29| 30 |           |          |
|          |           | 31| 32 |           |          |
|  LED     |   PWM 1   | 33| 34 |           |          |
|  T_DO    |   MISO 1  | 35| 36 |   GPIO16  |  T_CS    |
|  T_IRQ   |   GPIO26  | 37| 38 |   MOSI 1  |  T_DIN   |
|          |           | 39| 40 |   CLK 1   |  T_CLK   |
+----------+--------------------------------+----------+


## Enable SPI0, SPI1 and PWM

Edit `/boot/config.txt` and change the following...

Make sure that `dtparams=spi=on` is commented out!

```
# Disable the default 2-CS SPI0, we need 1-CS, see below
#dtparam=spi=on
```

```
[all]

# Enable SPI 0 (single-CS to free up pin 12 for PWM)
dtoverlay=spi0-1cs

# Enable SPI 1 (single-CS to free up pin 13 for PWM)
dtoverlay=spi1-1cs

# Enable hardware PWM on alternative pins 12 and 13
dtoverlay=pwm-2chan,pin=12,func=4,pin2=13,func2=4

```


## Install packages

sudo apt install python3-pip

pip3 install -r requirements.txt


## Clone repo and create dashboards

1. `git clone git@github.com:mludvig/solar-display.git`

2. Edit `config.yaml`

3. Install systemd unit file - follow instructions in `systemd.solar-display.service`

