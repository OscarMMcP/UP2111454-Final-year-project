import tkinter as tk
from tkinter import colorchooser

def paint(event):
    x1, y1 = (event.x - brush_size), (event.y - brush_size)
    x2, y2 = (event.x + brush_size), (event.y + brush_size)
    canvas.create_oval(x1, y1, x2, y2, fill=color, outline=color)

def change_color():
    global color
    color = colorchooser.askcolor(color=color)[1]

def change_brush_size(new_size):
    global brush_size
    brush_size = int(new_size)

def clear_canvas():
    canvas.delete("all")

# Initialize main window
root = tk.Tk()
root.title("Simple Paint Program")

color = "black"
brush_size = 5

# Create canvas
canvas = tk.Canvas(root, bg="white", width=600, height=400)
canvas.pack(fill=tk.BOTH, expand=True)
canvas.bind("<B1-Motion>", paint)

# Create controls
control_frame = tk.Frame(root)
control_frame.pack()

color_button = tk.Button(control_frame, text="Choose Color", command=change_color)
color_button.pack(side=tk.LEFT)

clear_button = tk.Button(control_frame, text="Clear", command=clear_canvas)
clear_button.pack(side=tk.LEFT)

brush_size_slider = tk.Scale(control_frame, from_=1, to=20, orient=tk.HORIZONTAL, label="Brush Size", command=change_brush_size)
brush_size_slider.set(5)
brush_size_slider.pack(side=tk.LEFT)

# Run application
root.mainloop()
