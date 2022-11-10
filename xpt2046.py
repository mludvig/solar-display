"""XPT2046 Touch module."""

# Inspired by:
# https://raw.githubusercontent.com/Luca8991/XPT2046-Python/main/xpt2046.py

import busio
from gpiozero import Button, DigitalOutputDevice

class XPT2046:
    """Serial interface for XPT2046 Touch Screen Controller."""

    # Command constants from XPT2046 datasheet
    GET_X = 0b11010000  # X position
    GET_Y = 0b10010000  # Y position
    GET_Z1 = 0b10110000  # Z1 position
    GET_Z2 = 0b11000000  # Z2 position
    GET_TEMP0 = 0b10000000  # Temperature 0
    GET_TEMP1 = 0b11110000  # Temperature 1
    GET_BATTERY = 0b10100000  # Battery monitor
    GET_AUX = 0b11100000  # Auxiliary input to ADC

    def __init__(self, miso, mosi, clk, cs,
                 irq=None, irq_handler=None, irq_handler_kwargs={},
                 width=240, height=320,
                 x_min=130, x_max=1935, y_min=195, y_max=1935,
                 rotation=0):
        """Initialize touch screen controller.

        Args:
            spi (Class Spi):  SPI interface for OLED
            cs (Class Pin):  Chip select pin
            irq (Class Pin):  Touch controller interrupt pin
            irq_handler (function): Handler for screen interrupt
            width (int): Width of LCD screen
            height (int): Height of LCD screen
            x_min (int): Minimum x coordinate
            x_max (int): Maximum x coordinate
            y_min (int): Minimum Y coordinate
            y_max (int): Maximum Y coordinate
        """
        self.spi = busio.SPI(clk, mosi, miso)
        self.cs = DigitalOutputDevice(cs, active_high=False, initial_value=False)
        self.cs.value = False
        self.rx_buf = bytearray(3)  # Receive buffer
        self.tx_buf = bytearray(3)  # Transmit buffer
        self.width = width
        self.height = height

        # Set calibration
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.x_multiplier = width / (x_max - x_min)
        self.x_add = x_min * -self.x_multiplier
        self.y_multiplier = height / (y_max - y_min)
        self.y_add = y_min * -self.y_multiplier

        assert rotation in [0, 90, 180, 270]
        self.rotation = rotation

        if irq is not None:
            self.irq = Button(irq)
            self.irq_locked = False
            self.irq_handler = irq_handler
            self.irq_handler_kwargs = irq_handler_kwargs
            self.irq.when_pressed = self.irq_press
            self.irq.when_released = self.irq_release

    def irq_press(self):
        """Send X,Y values to passed interrupt handler."""
        if irq_handler is None:
            return
        if not self.irq_locked:
            self.irq_locked = True  # Lock Interrupt
            buff = self.raw_touch()
            if buff is not None:
                raw_x, raw_y = buff
                x, y = self.normalize(raw_x, raw_y)
                self.irq_handler(x, y, raw_x, raw_y, **self.irq_handler_kwargs)

    def irq_release(self):
        self.irq_locked = False  # Unlock interrupt

    def normalize(self, x, y):
        """Normalize mean X,Y values to match LCD screen."""
        x = int(self.x_multiplier * x + self.x_add)
        y = int(self.y_multiplier * y + self.y_add)
        if self.rotation == 0:
            return self.width - x, self.height - y
        elif self.rotation == 90:
            return y, self.width - x
        elif self.rotation == 180:
            return x, y
        elif self.rotation == 270:
            return self.height - y, x
        return x, y

    def raw_touch(self):
        """Read raw X,Y touch values.

        Returns:
            tuple(int, int): X, Y
        """
        x = self.send_command(self.GET_X)
        y = self.send_command(self.GET_Y)
        return (x,y)

    def normalized_touch(self):
        coords = self.raw_touch()
        if coords is None:
            return coords
        return self.normalize(*coords)

    def send_command(self, command):
        """Write command to XT2046 (MicroPython).

        Args:
            command (byte): XT2046 command code.
        Returns:
            int: 12 bit response
        """
        self.tx_buf[0] = command
        self.cs.value = True
        self.spi.write_readinto(self.tx_buf, self.rx_buf)
        self.cs.value = False

        return (self.rx_buf[1] << 4) | (self.rx_buf[2] >> 4)
