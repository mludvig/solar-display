import queue
from PIL import Image, ImageDraw, ImageFont
from main import Display
from touch import TouchScreen

BUZZER_PIN=2

def calibrate_touchscreen(disp, touch_queue):
    def _cross_x(x,y):
        return [(max(0,x-10),y),
                (min(disp.d_width,x+10),y)]
    def _cross_y(x,y):
        return [(x, max(0,y-10)),
                (x, min(disp.d_height,y+10))]
    def draw_cross(x, y, fill):
        draw.line(_cross_x(x,y), fill=fill)
        draw.line(_cross_y(x,y), fill=fill)
        disp.display_image(image)

    image = Image.new("RGB", (disp.d_width, disp.d_height), "#000")
    font = ImageFont.truetype("fonts/Roboto-Regular.ttf", 16)
    draw = ImageDraw.Draw(image)
    draw.text((45, 45), "Touch the crosses", font=font, fill="#FF0")

    points = [
            # Top line
            (0, 0),
            (0, disp.d_height//2),
            (0, disp.d_height-1),

            # Middle line
            (disp.d_width//2, 0),
            (disp.d_width//2, disp.d_height//2),
            (disp.d_width//2, disp.d_height-1),

            # Bottom line
            (disp.d_width-1, 0),
            (disp.d_width-1, disp.d_height//2),
            (disp.d_width-1, disp.d_height-1),
    ]
    for point in points:
        draw_cross(*point, "#00FF00")
        while True: # Flush the queue
            try:
                touch_queue.get_nowait()
            except queue.Empty:
                break
        x,y,raw_x,raw_y = touch_queue.get()
        draw_cross(x, y, "#FF0000")
        print(f"{point} {x=},{y=} / {raw_x=},{raw_y=}")

if __name__ == "__main__":
    touch_queue = queue.Queue()

    rotation = 180
    disp = Display(rotation = rotation)

    touch_screen = TouchScreen(touch_queue, BUZZER_PIN, rotation)

    calibrate_touchscreen(disp, touch_queue)

    print("Press any key to exit...")
    input()
