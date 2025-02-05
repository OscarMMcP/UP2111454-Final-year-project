# Main
import cv2 as cv
import numpy as np
print( cv.__version__ )

canvas = np.zeros((500,500,4), dtype=np.uint8)
canvas[:, :] = [255, 255, 255, 255]  # White background with full opacity


# Function to simulate a 1x1 pixel cursor
def draw_pixel(event, x, y, flags, param):
    if event == cv.EVENT_MOUSEMOVE:  # When mouse moves
        temp_canvas = canvas.copy()
        temp_canvas[y, x] = [0, 0, 0, 255]  # Draw a tiny black pixel
        cv.imshow("Canvas", temp_canvas)

cv.setMouseCallback("Canvas", draw_pixel)



cv.imshow("Canvas", canvas)



# Wait for a key press and close the window
cv.waitKey(0)
cv.destroyAllWindows()