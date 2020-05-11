
import os.path

name_of_game = "Circuits"
version = "1.0.0"


""" Display """
default_window_size = (480*2, 240*2)  # size of window when the game starts.
minimum_window_size = (480, 240)  # if the window is smaller than this, it will begin cropping the picture.

allow_fullscreen = True
allow_window_resize = True

clear_color = (0, 0, 0)


""" Pixel Scaling """
optimal_window_size = (480*2, 240*2)
optimal_pixel_scale = 2  # how many screen pixels each "game pixel" will take up at the optimal window size.

auto_resize_pixel_scale = True  # whether to automatically update the pixel scale as the window grows and shrinks.
minimum_auto_pixel_scale = 2


""" FPS """
target_fps = 60
precise_fps = False


""" Miscellaneous """
do_crash_reporting = True  # whether to produce a crash file when the program exits via an exception.
is_dev = os.path.exists(".gitignore")  # yikes

