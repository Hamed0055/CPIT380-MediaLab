"""MediaLab: simple brightness, contrast, and grayscale histograms.

Requires: Pillow and Matplotlib.
All processing functions return a new image and leave the original unchanged.
"""

from PIL import Image
import matplotlib.pyplot as plt


# 01. Brightness: Adds or subtracts a fixed amount from each RGB channel.
def adjust_brightness(image: Image.Image, amount: int = 0) -> Image.Image:
    if not -255 <= amount <= 255:
        raise ValueError("Brightness amount must be between -255 and 255.")

    image = image.convert("RGB")
    return image.point(lambda value: max(0, min(255, round(value + amount))))


# 02. Grayscale Histogram: Counts how many pixels have each intensity (0–255).
def grayscale_histogram(image: Image.Image) -> list[int]:
    gray = image.convert("L")
    pixels = gray.load()
    counts = [0] * 256

    for y in range(gray.height):
        for x in range(gray.width):
            intensity = pixels[x, y]
            counts[intensity] += 1

    return counts


# 03. Contrast: Spreads or compresses RGB values around the image's mean intensity.
def adjust_contrast(image: Image.Image, factor: float = 1.0) -> Image.Image:
    if not 0 <= factor <= 3:
        raise ValueError("Contrast factor must be between 0 and 3.")

    image = image.convert("RGB")
    counts = grayscale_histogram(image)
    total_pixels = image.width * image.height
    mean = (
        sum(intensity * count for intensity, count in enumerate(counts)) / total_pixels
    )

    # factor = 1: unchanged; > 1: stronger contrast; < 1: weaker contrast.
    return image.point(
        lambda value: max(0, min(255, round(factor * (value - mean) + mean)))
    )


# 04. Binned Histogram: Groups the 256 grayscale levels into fewer histogram bars.
def binned_histogram(image: Image.Image, bins: int = 32) -> list[int]:
    if not isinstance(bins, int) or isinstance(bins, bool) or not 1 <= bins <= 256:
        raise ValueError("bins must be an integer between 1 and 256.")

    full = grayscale_histogram(image)
    grouped = [0] * bins

    for intensity, count in enumerate(full):
        index = min(bins - 1, intensity * bins // 256)
        grouped[index] += count

    return grouped


# 05. Plot Histogram: Creates a Matplotlib figure for a selected number of bins.
def plot_histogram(image: Image.Image, bins: int = 32, title: str = "Histogram"):
    counts = binned_histogram(image, bins)
    bin_width = 256 / bins
    centers = [(i + 0.5) * bin_width for i in range(bins)]

    fig, ax = plt.subplots(figsize=(7, 3))
    ax.bar(centers, counts, width=bin_width * 0.9)
    ax.set(
        xlim=(0, 256),
        xlabel="Grayscale intensity (0–255)",
        ylabel="Pixel count",
        title=title,
    )
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    # Standalone demonstration: creates a sample gradient and shows the results.
    image = Image.linear_gradient("L").resize((512, 256)).convert("RGB")
    result = adjust_contrast(adjust_brightness(image, 25), factor=1.5)
    result.save("histogram_demo.png")
    print("Saved histogram_demo.png")

    fig = plot_histogram(result, bins=32, title="Processed image")
    plt.show()
    plt.close(fig)
