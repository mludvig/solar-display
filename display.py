import board
import digitalio

from adafruit_rgb_display import ili9341

class Display:
    # Config for display baudrate (default max is 24mhz):
    BAUDRATE = 24000000

    def __init__(self, rotation=0):
        # Configuration for CS and DC pins (these are PiTFT defaults):
        cs_pin = digitalio.DigitalInOut(board.CE0)
        dc_pin = digitalio.DigitalInOut(board.D25)
        reset_pin = digitalio.DigitalInOut(board.D24)
        backlight_pin = digitalio.DigitalInOut(board.D13)

        # Turn on the Backlight
        backlight_pin.switch_to_output()
        backlight_pin.value = True

        # Setup SPI bus using hardware SPI:
        spi = board.SPI()

        # Create the display:
        self.disp = ili9341.ILI9341(
            spi,
            rotation=rotation,
            cs=cs_pin,
            dc=dc_pin,
            rst=reset_pin,
            baudrate=self.BAUDRATE,
        )

        # Create blank image for drawing.
        # Make sure to create image with mode 'RGB' for full color.
        if self.disp.rotation % 180 == 90:
            # landscape mode
            self.d_height = self.disp.width
            self.d_width = self.disp.height
        else:
            # portrait mode
            self.d_height = self.disp.height
            self.d_width = self.disp.width

    def display_image(self, image):
        # Crop oversized image
        if image.height > self.d_height or image.width > self.d_width:
            image = image.crop((0, 0, self.d_width, self.d_height))

        # Display image.
        self.disp.image(image)
