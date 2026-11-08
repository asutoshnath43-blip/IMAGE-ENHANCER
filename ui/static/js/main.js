document.addEventListener("DOMContentLoaded", () => {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const selectedFilename = document.getElementById("selected-filename");
    const presetSelect = document.getElementById("preset-select");
    const scalingSelect = document.getElementById("scaling-select");
    const formatSelect = document.getElementById("format-select");
    const sharpenSlider = document.getElementById("sharpen-slider");
    const sharpenVal = document.getElementById("sharpen-val");
    const enhanceBtn = document.getElementById("enhance-btn");
    const sampleBtn = document.getElementById("sample-btn");
    const statusBox = document.getElementById("status-box");

    const emptyState = document.getElementById("empty-state");
    const previewStage = document.getElementById("preview-stage");
    const origCard = document.getElementById("orig-card");
    const enhCard = document.getElementById("enh-card");
    const origImg = document.getElementById("orig-img");
    const enhImg = document.getElementById("enh-img");
    const origDims = document.getElementById("orig-dims");
    const enhDims = document.getElementById("enh-dims");
    const downloadBtn = document.getElementById("download-btn");
    const metricsBar = document.getElementById("metrics-bar");
    const metricScale = document.getElementById("metric-scale");
    const metricTime = document.getElementById("metric-time");
    const metricSize = document.getElementById("metric-size");
    const tabBtns = document.querySelectorAll(".tab-btn");

    let currentFile = null;

    sharpenSlider.addEventListener("input", () => {
        sharpenVal.textContent = `${ parseFloat(sharpenSlider.value).toFixed(1) }x`;
    });

    dropZone.addEventListener("click", () => fileInput.click());
    dropZone.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            fileInput.click();
        }
    });

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("drag-over");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("drag-over");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("drag-over");
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFileSelection(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files && fileInput.files.length > 0) {
            handleFileSelection(fileInput.files[0]);
        }
    });

    function handleFileSelection(file) {
        currentFile = file;
        selectedFilename.textContent = file.name;
        enhanceBtn.disabled = false;

        const reader = new FileReader();
        reader.onload = (ev) => {
            origImg.src = ev.target.result;
            const probe = new Image();
            probe.onload = () => {
                origDims.textContent = `${probe.width} × ${probe.height} px`;
            };
            probe.src = ev.target.result;
            emptyState.classList.add("hidden");
            previewStage.classList.remove("hidden");
        };
        reader.readAsDataURL(file);
        setStatus("Ready to enhance to 1080p.", false);
    }

    function setStatus(message, isError = false) {
        statusBox.textContent = message;
        statusBox.classList.remove("hidden", "error");
        if (isError) statusBox.classList.add("error");
    }

    enhanceBtn.addEventListener("click", async () => {
        if (!currentFile) return;
        await runEnhancement(false);
    });

    sampleBtn.addEventListener("click", async () => {
        await runEnhancement(true);
    });

    async function runEnhancement(useSample) {
        enhanceBtn.disabled = true;
        sampleBtn.disabled = true;
        setStatus("Upscaling and restoring 1080p details...", false);

        try {
            const formData = new FormData();
            if (!useSample && currentFile) {
                formData.append("image", currentFile);
            } else {
                formData.append("use_sample", "1");
            }
            formData.append("preset", presetSelect.value);
            formData.append("scaling_mode", scalingSelect.value);
            formData.append("output_format", formatSelect.value);
            formData.append("sharpen", sharpenSlider.value);

            const response = await fetch("/api/enhance", {
                method: "POST",
                body: formData,
            });
            const data = await response.json();

            if (!response.ok || data.error) {
                throw new Error(data.error || "Enhancement request failed.");
            }

            if (data.original_url) {
                origImg.src = data.original_url + "?t=" + Date.now();
            }
            enhImg.src = data.download_url + "?t=" + Date.now();
            origDims.textContent = `${data.original_width} × ${data.original_height} px`;
            enhDims.textContent = `${data.enhanced_width} × ${data.enhanced_height} px`;

            downloadBtn.href = `${data.download_url}?download=1`;
            downloadBtn.download = data.output_filename;
            downloadBtn.classList.remove("hidden");

            emptyState.classList.add("hidden");
            previewStage.classList.remove("hidden");

            metricScale.textContent = `Upscale Factor: ${data.scale_factor}x`;
            metricTime.textContent = `Processing Time: ${data.processing_time_ms} ms`;
            metricSize.textContent = `Output Size: ${data.file_size_kb} KB (${data.output_format})`;
            metricsBar.classList.remove("hidden");

            setStatus(`Enhanced to ${data.enhanced_width}×${data.enhanced_height} (1080p HD). Ready to download.`);
        } catch (err) {
            setStatus(err.message, true);
        } finally {
            enhanceBtn.disabled = !currentFile;
            sampleBtn.disabled = false;
        }
    }

    tabBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
            tabBtns.forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            const view = btn.dataset.view;
            if (view === "split") {
                previewStage.classList.remove("single-view");
                origCard.classList.remove("hidden");
                enhCard.classList.remove("hidden");
            } else if (view === "enhanced") {
                previewStage.classList.add("single-view");
                origCard.classList.add("hidden");
                enhCard.classList.remove("hidden");
            } else {
                previewStage.classList.add("single-view");
                origCard.classList.remove("hidden");
                enhCard.classList.add("hidden");
            }
        });
    });
});
