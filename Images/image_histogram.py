"""MediaLab: simple brightness, contrast, and grayscale histograms.

Requires: Pillow and Matplotlib.
All processing functions return a new image and leave the original unchanged.
"""

from PIL import Image
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator, StrMethodFormatter

if __package__:
    from .Image_filters import _check_number, _map_colours, _visible_histogram, _working_image, adjust_contrast as adjust_contrast
else:
    from Image_filters import _check_number, _map_colours, _visible_histogram, _working_image, adjust_contrast as adjust_contrast


# 01. Brightness: Adds or subtracts a fixed amount from each RGB channel.
def adjust_brightness(image: Image.Image, amount: int = 0) -> Image.Image:
    amount = _check_number("Brightness amount", amount, -255, 255)
    return _map_colours(image, lambda value: max(0, min(255, round(value + amount))))


# 02. Grayscale Histogram: Counts each visible pixel in its intensity bin (0–255).
def grayscale_histogram(image: Image.Image) -> list[int]:
    # Pillow performs the same one-increment-per-pixel loop in compiled code.
    return _visible_histogram(_working_image(image))


# 03. Contrast: Re-exported from Image_filters so both tools use the same formula.


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
def plot_histogram(
    image: Image.Image, bins: int = 32, title: str = "Histogram", *, figure: Figure | None = None, counts: list[int] | None = None
):
    counts = binned_histogram(image, bins) if counts is None else counts
    bin_width = 256 / bins
    centers = [(i + 0.5) * bin_width for i in range(bins)]

    fig = figure if figure is not None else Figure(figsize=(6.0, 2.65), layout="constrained")
    ax = fig.subplots()
    ax.bar(centers, counts, width=bin_width * 0.88, color="#2354D6")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#E6EBF4", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
    ax.set(
        xlim=(0, 256),
        xlabel="Brightness (dark to light)",
        ylabel="Pixels",
        title=title,
    )
    return fig


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    # Standalone demonstration: creates a sample gradient and shows the results.
    image = Image.linear_gradient("L").resize((512, 256)).convert("RGB")
    result = adjust_contrast(adjust_brightness(image, 25), factor=1.5)
    result.save("histogram_demo.png")
    print("Saved histogram_demo.png")

    fig = plt.figure(figsize=(6.0, 2.65), layout="constrained")
    plot_histogram(result, bins=32, title="Processed image", figure=fig)
    plt.show()
    plt.close(fig)
