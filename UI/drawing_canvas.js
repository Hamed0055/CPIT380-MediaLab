// Mount a pointer-sized preview. The saved pixels are always drawn by Pillow.
export default function ({ parentElement, data, setTriggerValue }) {
    const canvas = parentElement.querySelector("canvas");
    const image = parentElement.querySelector("img");
    canvas.width = image.width = data.width;
    canvas.height = image.height = data.height;
    image.src = data.image;
    image.parentElement.style.maxWidth = data.width + "px";
    const ctx = canvas.getContext("2d");
    ctx.strokeStyle = data.color;
    ctx.fillStyle = data.color;
    ctx.lineWidth = data.thickness;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    let points = [];
    let pointer = null;
    let submitted = false;

    // Pointer position: Translate from CSS coordinates to Pillow's pixel grid.
    function position(event) {
        const rect = canvas.getBoundingClientRect();
        const x = Math.floor((event.clientX - rect.left) * canvas.width / rect.width);
        const y = Math.floor((event.clientY - rect.top) * canvas.height / rect.height);
        return [Math.max(0, Math.min(canvas.width - 1, x)),
                Math.max(0, Math.min(canvas.height - 1, y))];
    }

    // Sketch preview: Draw the current gesture on the clear overlay.
    function preview(point) {
        const [x, y] = points[0];
        const [endX, endY] = point;
        if (data.tool !== "Pencil") ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.beginPath();
        if (data.tool === "Pencil" || data.tool === "Line") {
            const start = data.tool === "Pencil" ? points.at(-1) : points[0];
            ctx.moveTo(...start);
            ctx.lineTo(endX, endY);
        } else if (data.tool === "Rectangle") {
            ctx.rect(x, y, endX - x, endY - y);
        } else if (data.tool === "Ellipse") {
            const width = Math.abs(endX - x) / 2;
            const height = Math.abs(endY - y) / 2;
            if (width && height) ctx.ellipse((x + endX) / 2, (y + endY) / 2, width, height, 0, 0, 2 * Math.PI);
        }
        if (data.filled) ctx.fill();
        else ctx.stroke();
    }

    canvas.onpointerdown = (event) => {
        if (submitted || event.button !== 0 || pointer !== null) return;
        pointer = event.pointerId;
        canvas.setPointerCapture(pointer);
        points = [position(event)];
    };
    canvas.onpointermove = (event) => {
        if (event.pointerId !== pointer || data.tool === "Eyedropper") return;
        const point = position(event);
        preview(point);
        if (data.tool === "Pencil" && points.length < 4095) {
            const last = points.at(-1);
            if (point[0] !== last[0] || point[1] !== last[1]) points.push(point);
        }
    };
    canvas.onpointerup = (event) => {
        if (event.pointerId !== pointer) return;
        pointer = null;
        const point = position(event);
        if (data.tool !== "Eyedropper") {
            preview(point);
            points.push(point);
        }
        submitted = true;
        setTriggerValue("action", { points, tool: data.tool, version: data.version });
    };
    canvas.onpointercancel = () => {
        pointer = null;
        points = [];
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    };
    canvas.dataset.tool = data.tool;
    canvas.dataset.version = String(data.version);
}
