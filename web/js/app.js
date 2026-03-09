/* ============================================================
   RealSketch PWA — Client logic
   ============================================================ */

(() => {
    "use strict";

    // ---- DOM elements ----
    const fileInput = document.getElementById("fileInput");
    const btnLoad = document.getElementById("btnLoad");
    const btnProcess = document.getElementById("btnProcess");
    const btnExport = document.getElementById("btnExport");
    const statusBar = document.getElementById("statusBar");
    const progressWrap = document.getElementById("progressWrap");
    const progressBar = document.getElementById("progressBar");
    const previewSec = document.getElementById("previewSection");
    const originalImg = document.getElementById("originalImg");
    const resultsSec = document.getElementById("resultsSection");
    const imgSketch = document.getElementById("imgSketch");
    const imgShading = document.getElementById("imgShading");
    const imgValues = document.getElementById("imgValues");
    const tabs = document.querySelectorAll(".tab");
    const panels = document.querySelectorAll(".tab-panel");

    let currentFile = null;
    let resultData = null; // { sketch, shading, values } base64

    // ---- Service Worker ----
    if ("serviceWorker" in navigator) {
        navigator.serviceWorker.register("/sw.js").catch(() => {});
    }

    // ---- Status helpers ----
    function setStatus(msg) {
        statusBar.textContent = msg;
    }
    function showProgress(pct) {
        progressWrap.hidden = false;
        progressBar.style.width = pct + "%";
    }
    function hideProgress() {
        progressWrap.hidden = true;
        progressBar.style.width = "0%";
    }

    // ---- File load ----
    fileInput.addEventListener("change", () => {
        const file = fileInput.files[0];
        if (!file) return;
        currentFile = file;
        resultData = null;

        // Preview
        const url = URL.createObjectURL(file);
        originalImg.src = url;
        previewSec.hidden = false;
        resultsSec.hidden = true;

        btnProcess.disabled = false;
        btnExport.disabled = true;
        setStatus(
            `Image loaded: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`,
        );
    });

    // ---- Process ----
    btnProcess.addEventListener("click", async () => {
        if (!currentFile) return;

        btnProcess.disabled = true;
        btnExport.disabled = true;
        setStatus("Processing image...");
        showProgress(15);

        const form = new FormData();
        form.append("image", currentFile);

        try {
            showProgress(40);

            const resp = await fetch("/api/process", {
                method: "POST",
                body: form,
            });
            showProgress(80);

            const data = await resp.json();
            showProgress(100);

            if (!resp.ok || data.error) {
                throw new Error(data.error || "Unknown error");
            }

            // Save result
            resultData = {
                original: data.original,
                sketch: data.sketch,
                shading: data.shading,
                values: data.values,
            };

            // Show in preview
            originalImg.src = data.original;
            imgSketch.src = data.sketch;
            imgShading.src = data.shading;
            imgValues.src = data.values;

            resultsSec.hidden = false;
            btnExport.disabled = false;

            // Activate Sketch tab
            activateTab("sketch");

            const faceMsg = data.has_face
                ? "Face detected — portrait guides generated."
                : "Generic mode (no face detected).";
            setStatus("✓ Processing complete — " + faceMsg);
        } catch (err) {
            setStatus("Error: " + err.message);
        } finally {
            btnProcess.disabled = false;
            setTimeout(hideProgress, 600);
        }
    });

    // ---- Tabs ----
    function activateTab(name) {
        tabs.forEach((t) =>
            t.classList.toggle("active", t.dataset.tab === name),
        );
        panels.forEach((p) =>
            p.classList.toggle("active", p.id === "panel-" + name),
        );
    }
    tabs.forEach((t) =>
        t.addEventListener("click", () => activateTab(t.dataset.tab)),
    );

    // ---- Export / Download ----
    btnExport.addEventListener("click", () => {
        if (!resultData) return;

        const files = [
            { name: "01_original.png", data: resultData.original },
            { name: "02_sketch.png", data: resultData.sketch },
            { name: "03_shading.png", data: resultData.shading },
            { name: "04_values.png", data: resultData.values },
        ];

        files.forEach(({ name, data }) => {
            const a = document.createElement("a");
            a.href = data;
            a.download = name;
            document.body.appendChild(a);
            a.click();
            a.remove();
        });

        setStatus("✓ 4 files downloaded.");
    });
})();
