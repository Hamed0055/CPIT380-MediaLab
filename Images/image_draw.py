"""MediaLab: a small Pillow drawing tool with a Tkinter window."""

import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from PIL import Image, ImageDraw, ImageOps, ImageTk


WIDTH = 800
HEIGHT = 500


# 01. Draw Shape: Adds a line, rectangle, or ellipse to a Pillow image.
def draw_shape(image, tool, start, end, color, thickness):
    draw = ImageDraw.Draw(image)
    x0, y0 = start
    x1, y1 = end

    if tool == "Line":
        draw.line((x0, y0, x1, y1), fill=color, width=thickness)
    else:
        box = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        if tool == "Rectangle":
            draw.rectangle(box, outline=color, width=thickness)
        elif tool == "Ellipse":
            draw.ellipse(box, outline=color, width=thickness)


# 02. Pencil Stroke: Connects two mouse positions with a colored line.
def pencil_stroke(image, start, end, color, thickness):
    ImageDraw.Draw(image).line((start, end), fill=color, width=thickness)


# 03. Eyedropper: Reads the RGB color of one image pixel.
def pick_color(image, x, y):
    return image.getpixel((x, y))


class ImageDrawApp:
    # 04. Initialize: Creates a blank drawing area and a simple toolbar.
    def __init__(self, root):
        root.title("MediaLab - Image Drawing")
        self.image = Image.new("RGB", (WIDTH, HEIGHT), "white")
        self.color = "#000000"
        self.tool = tk.StringVar(value="Pencil")
        self.size = tk.IntVar(value=4)
        self.start = None
        self.last = None

        bar = ttk.Frame(root, padding=8)
        bar.pack(fill="x")

        ttk.Button(bar, text="New", command=self.new_image).pack(side="left")
        ttk.Button(bar, text="Open", command=self.open_image).pack(side="left", padx=3)
        ttk.Button(bar, text="Save", command=self.save_image).pack(side="left")

        ttk.Combobox(
            bar, textvariable=self.tool, state="readonly", width=12,
            values=("Pencil", "Line", "Rectangle", "Ellipse", "Eyedropper"),
        ).pack(side="left", padx=12)

        self.color_button = tk.Button(bar, text="Color", bg=self.color,
                                      fg="white", command=self.choose_color)
        self.color_button.pack(side="left")

        ttk.Label(bar, text="Size:").pack(side="left", padx=(12, 0))
        ttk.Scale(bar, from_=1, to=25, variable=self.size).pack(side="left")

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT,
                                bg="white", cursor="crosshair", highlightthickness=0)
        self.canvas.pack(padx=8, pady=(0, 8))
        self.photo = ImageTk.PhotoImage(self.image)
        self.image_item = self.canvas.create_image(0, 0, anchor="nw", image=self.photo)

        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    # 05. Refresh: Displays the latest Pillow image in the drawing window.
    def refresh(self):
        self.canvas.delete("preview")
        self.photo = ImageTk.PhotoImage(self.image)
        self.canvas.itemconfigure(self.image_item, image=self.photo)

    # 06. Mouse Position: Keeps coordinates inside the image boundaries.
    def position(self, event):
        return (max(0, min(event.x, WIDTH - 1)),
                max(0, min(event.y, HEIGHT - 1)))

    # 07. Mouse Press: Starts a stroke or samples a color with the eyedropper.
    def on_press(self, event):
        self.start = self.last = self.position(event)
        if self.tool.get() == "Eyedropper":
            r, g, b = pick_color(self.image, *self.start)
            self.set_color(f"#{r:02x}{g:02x}{b:02x}")
        elif self.tool.get() == "Pencil":
            x, y = self.start
            radius = max(1, self.size.get()) / 2
            ImageDraw.Draw(self.image).ellipse(
                (x - radius, y - radius, x + radius, y + radius), fill=self.color
            )
            self.refresh()

    # 08. Mouse Drag: Draws with the pencil or previews a shape.
    def on_drag(self, event):
        if self.start is None or self.tool.get() == "Eyedropper":
            return
        point = self.position(event)
        tool = self.tool.get()
        if tool == "Pencil":
            pencil_stroke(self.image, self.last, point, self.color, self.size.get())
            self.refresh()
            self.last = point
        else:
            self.canvas.delete("preview")
            x0, y0 = self.start
            x1, y1 = point
            options = {"outline": self.color, "width": self.size.get(), "tags": "preview"}
            if tool == "Line":
                self.canvas.create_line(x0, y0, x1, y1, fill=self.color,
                                        width=self.size.get(), tags="preview")
            elif tool == "Rectangle":
                self.canvas.create_rectangle(x0, y0, x1, y1, **options)
            elif tool == "Ellipse":
                self.canvas.create_oval(x0, y0, x1, y1, **options)

    # 09. Mouse Release: Applies the finished shape to the Pillow image.
    def on_release(self, event):
        if self.start is None:
            return
        if self.tool.get() in ("Line", "Rectangle", "Ellipse"):
            draw_shape(self.image, self.tool.get(), self.start,
                       self.position(event), self.color, self.size.get())
        self.start = self.last = None
        self.refresh()

    # 10. Set Color: Updates the current drawing color and button preview.
    def set_color(self, color):
        self.color = color
        self.color_button.config(bg=color)

    # 11. Choose Color: Opens the system color picker.
    def choose_color(self):
        _, selected = colorchooser.askcolor(color=self.color)
        if selected:
            self.set_color(selected)

    # 12. New Image: Clears the canvas to a blank white image.
    def new_image(self):
        self.image = Image.new("RGB", (WIDTH, HEIGHT), "white")
        self.refresh()

    # 13. Open Image: Loads a picture and fits it into the drawing area.
    def open_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp")]
        )
        if not path:
            return
        try:
            with Image.open(path) as loaded:
                picture = ImageOps.exif_transpose(loaded).convert("RGBA")
            picture.thumbnail((WIDTH, HEIGHT))
            self.image = Image.new("RGB", (WIDTH, HEIGHT), "white")
            offset = ((WIDTH - picture.width) // 2, (HEIGHT - picture.height) // 2)
            self.image.paste(picture, offset, picture)
            self.refresh()
        except (OSError, ValueError) as exc:
            messagebox.showerror("Cannot open image", str(exc))

    # 14. Save Image: Exports the edited canvas as PNG or JPEG.
    def save_image(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("JPEG image", "*.jpg")],
        )
        if path:
            try:
                self.image.save(path)
            except (OSError, ValueError) as exc:
                messagebox.showerror("Cannot save image", str(exc))


# 15. Main: Starts the standalone drawing window.
def main():
    root = tk.Tk()
    ImageDrawApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
