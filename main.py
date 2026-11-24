# Methods that can be applied to an uploaded image whole.
# ------------------------------------------------------------
# Imports
# ------------------------------------------------------------
# Path helps us refer to files/folders in a platform-independent way.
from pathlib import Path

# NumPy is used for numerical array operations and comparisons.
import numpy as np

# Matplotlib is used only for displaying images in the notebook.
import matplotlib.pyplot as plt

# Pillow (PIL) provides the main image object and image operations used in this lab.
from PIL import Image, ImageOps

# skimage.data provides built-in demonstration images such as
# astronaut, coffee, rocket, and chelsea.
from skimage import data


def as_rgb_pil(arr, max_side=300):
    """
    Convert a NumPy image array into a Pillow RGB image.

    Parameters
    ----------
    arr : NumPy array
        Image returned by skimage.data.
    max_side : int
        Maximum allowed width or height for the classroom demonstration.

    Why this helper exists
    ----------------------
    skimage.data returns images as NumPy arrays, but the examples in this
    notebook mainly use Pillow. This helper performs that conversion once
    and optionally reduces very large images so the pixel-by-pixel examples
    run quickly in class.
    """

    # Convert the NumPy array into a Pillow image and force three-channel RGB.
    image = Image.fromarray(arr).convert("RGB")

    # Find a scale factor that keeps the image at or below max_side.
    # min(1.0, ...) means we only shrink; we never enlarge here.
    scale = min(1.0, max_side / max(image.size))

    # Resize only when the original image is larger than the desired limit.
    if scale < 1:
        new_size = (
            max(1, int(round(image.width * scale))),
            max(1, int(round(image.height * scale))),
        )

        # BILINEAR interpolation gives a smoother classroom preview than
        # nearest-neighbor resizing.
        image = image.resize(new_size, Image.Resampling.BILINEAR)

    # Return the prepared Pillow image.
    return image


# ------------------------------------------------------------
# Prepare four built-in demonstration images.
# ------------------------------------------------------------
# Each skimage.data function returns a NumPy array.
# as_rgb_pil(...) converts that array into a Pillow image.
astronaut = as_rgb_pil(data.astronaut())
coffee = as_rgb_pil(data.coffee())
rocket = as_rgb_pil(data.rocket())
chelsea = as_rgb_pil(data.chelsea())


def show_images(images, titles=None, figsize=None):
    """
    Display several images side-by-side.

    images  : list of Pillow images
    titles  : optional list of titles, one title per image
    figsize : Matplotlib figure size in inches, e.g. (12, 4)

    This helper avoids repeating the same plotting code in every example.
    """

    # Number of images determines how many subplot columns we need.
    n = len(images)

    # If the caller does not specify a figure size, allocate about
    # four inches of width per displayed image.
    if figsize is None:
        figsize = (4 * n, 4)

    # Create one Matplotlib figure.
    plt.figure(figsize=figsize)

    # Place each image into one subplot.
    for i, img in enumerate(images, start=1):
        plt.subplot(1, n, i)
        plt.imshow(img)

        # Hide x/y axes because they are not useful for ordinary image viewing.
        plt.axis("off")

        # Add a title only if titles were provided.
        if titles:
            plt.title(titles[i - 1])

    # Reduce unnecessary spacing and display the figure.
    plt.tight_layout()
    plt.show()


def clip8(value):
    """
    Convert a numeric value to a valid 8-bit channel value.

    RGB channels must stay between 0 and 255.
    We round first, clip into the legal range, and convert to int.
    """
    return int(np.clip(round(value), 0, 255))
