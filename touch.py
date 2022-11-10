import time
import board
from gpiozero import TonalBuzzer
from gpiozero.tones import Tone
from xpt2046 import XPT2046

class TouchScreen:
    """
    Wrapper around XPT2024 low-level touch screen driver.

    Sends the sensed coordinates to 'touch_queue' as (x, y, raw_x, raw_y)
    """
    def __init__(self, touch_queue, buzzer_pin, rotation):
        self.touch_queue = touch_queue
        self.buzzer = TonalBuzzer(buzzer_pin)
        self.xpt = XPT2046(
                miso = board.MISO_1,
                mosi = board.MOSI_1,
                clk = board.SCLK_1,
                cs = 16,
                irq = 26,
                irq_handler=self.touchscreen_callback,
                #irq_handler_kwargs=callback_kwargs,
                rotation=rotation,
        )

    def beep(self, length=0.05, tone="A5"):
        self.buzzer.play(Tone(tone))
        time.sleep(length)
        self.buzzer.stop()

    def touchscreen_callback(self, x, y, raw_x, raw_y):
        self.touch_queue.put((x,y,raw_x,raw_y))
        self.beep()
