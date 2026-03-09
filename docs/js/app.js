/* ============================================================
   RealSketch — 100% client-side PWA application
   Handles UI, image loading and calls processing.js
   ============================================================ */
(() => {
    "use strict";

    /* ---------- state ---------- */
    let cvReady = false;
    let originalSrc = null;
    let results = {};

    /* ---------- DOM (IDs from index.html) ---------- */
    const fileInput = document.getElementById("fileInput");
    const btnLoad = document.getElementById("btnLoad");
    const processBtn = document.getElementById("btnProcess");
    const downloadBtn = document.getElementById("btnExport");
    const statusBar = document.getElementById("statusBar");
    const progressWrap = document.getElementById("progressWrap");
    const progressBar = document.getElementById("progressBar");
    const comparisonSection = document.getElementById("comparisonSection");
    const originalImg = document.getElementById("originalImg");
    const tabBtns = document.querySelectorAll(".tab");
    const tabPanels = document.querySelectorAll(".tab-panel");
    const imgSketch = document.getElementById("imgSketch");
    const imgShading = document.getElementById("imgShading");
    const imgValues = document.getElementById("imgValues");
    const imgGrid = document.getElementById("imgGrid");
    const imgEdges = document.getElementById("imgEdges");
    const imgNotan = document.getElementById("imgNotan");

    /* ---------- OpenCV ready callback (global) ---------- */
    window.onOpenCvReady = () => {
        cvReady = true;
        setStatus("OpenCV ready — Load an image to get started.");
        processBtn.disabled = !originalSrc;
    };

    /* ---------- helpers ---------- */
    function setStatus(msg) {
        if (statusBar) statusBar.textContent = msg;
    }

    function setProgress(pct) {
        progressWrap.hidden = pct <= 0 || pct >= 100;
        progressBar.style.width = pct + "%";
    }

    /* ---------- init ---------- */
    setStatus("Loading OpenCV.js …");
    processBtn.disabled = true;
    downloadBtn.disabled = true;
    comparisonSection.hidden = true;

    /* ---------- Drag & Drop on entire page ---------- */
    document.body.addEventListener("dragover", (e) => {
        e.preventDefault();
        btnLoad.classList.add("drag-over");
    });
    document.body.addEventListener("dragleave", (e) => {
        if (!document.body.contains(e.relatedTarget))
            btnLoad.classList.remove("drag-over");
    });
    document.body.addEventListener("drop", (e) => {
        e.preventDefault();
        btnLoad.classList.remove("drag-over");
        if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
    });

    /* ---------- File input ---------- */
    fileInput.addEventListener("change", () => {
        if (fileInput.files.length) handleFile(fileInput.files[0]);
    });

    function handleFile(file) {
        if (!file.type.startsWith("image/")) {
            setStatus("Only image files are allowed.");
            return;
        }
        // Free previous resources
        freeAllResults();

        const reader = new FileReader();
        reader.onload = (ev) => {
            const img = new Image();
            img.onload = () => {
                originalImg.src = img.src;
                comparisonSection.hidden = false;
                loadToMat(img);
                setStatus("Image loaded — Press Process.");
                processBtn.disabled = !cvReady;
                downloadBtn.disabled = true;
            };
            img.src = ev.target.result;
        };
        reader.readAsDataURL(file);
    }

    /** Frees all Mat objects from previous results. */
    function freeAllResults() {
        for (const key of Object.keys(results)) {
            try {
                results[key].delete();
            } catch (_) {
                /* ignore */
            }
        }
        results = {};
    }

    /** Loads the image into a cv.Mat RGBA, scaling if > MAX. */
    function loadToMat(img) {
        const canvas = document.createElement("canvas");
        const MAX = 1400;
        let w = img.naturalWidth,
            h = img.naturalHeight;
        if (Math.max(w, h) > MAX) {
            const r = MAX / Math.max(w, h);
            w = Math.round(w * r);
            h = Math.round(h * r);
        }
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(img, 0, 0, w, h);
        if (originalSrc) originalSrc.delete();
        originalSrc = cv.matFromImageData(ctx.getImageData(0, 0, w, h));
    }

    /* ---------- Process ---------- */
    processBtn.addEventListener("click", () => {
        if (!cvReady || !originalSrc) {
            setStatus("Load an image first.");
            return;
        }
        processBtn.disabled = true;
        downloadBtn.disabled = true;
        setProgress(5);
        setStatus("Pre-processing image …");
        requestAnimationFrame(() => setTimeout(runPipeline, 50));
    });

    function runPipeline() {
        try {
            const src = preprocessImage(originalSrc);
            setProgress(15);

            setStatus("Generating sketch …");
            const sketch = RealSketchProcessing.generateSketch(src);
            matToImg(sketch, imgSketch);
            freeOld("sketch");
            results.sketch = sketch;
            setProgress(45);

            setStatus("Generating shading \u2026");
            const shading = RealSketchProcessing.generateShading(src);
            matToImg(shading, imgShading);
            freeOld("shading");
            results.shading = shading;
            setProgress(70);

            setStatus("Generating values \u2026");
            const values = RealSketchProcessing.generateToneMap(src);
            matToImg(values, imgValues);
            freeOld("values");
            results.values = values;
            setProgress(100);

            if (src !== originalSrc) src.delete();

            comparisonSection.hidden = false;
            downloadBtn.disabled = false;
            setStatus("Done! Select a tab to view each step.");
            activateTab("sketch");
        } catch (e) {
            console.error(e);
            setStatus("Error: " + e.message);
        }
        processBtn.disabled = false;
        setTimeout(() => setProgress(0), 600);
    }

    function freeOld(key) {
        if (results[key]) {
            try {
                results[key].delete();
            } catch (_) {
                /* ignore */
            }
        }
    }

    /** Preprocess: normalize low contrast via CLAHE on L (LAB). */
    function preprocessImage(src) {
        const gray = new cv.Mat();
        cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY);
        const data = gray.data;
        let lo = 255,
            hi = 0;
        for (let i = 0; i < data.length; i++) {
            if (data[i] < lo) lo = data[i];
            if (data[i] > hi) hi = data[i];
        }
        gray.delete();

        if (hi - lo < 80) {
            const bgr = new cv.Mat();
            cv.cvtColor(src, bgr, cv.COLOR_RGBA2BGR);
            const lab = new cv.Mat();
            cv.cvtColor(bgr, lab, cv.COLOR_BGR2Lab);
            const channels = new cv.MatVector();
            cv.split(lab, channels);
            const L = channels.get(0);
            const clahe = new cv.CLAHE(3.0, new cv.Size(8, 8));
            clahe.apply(L, L);
            clahe.delete();
            channels.set(0, L);
            cv.merge(channels, lab);
            cv.cvtColor(lab, bgr, cv.COLOR_Lab2BGR);
            const result = new cv.Mat();
            cv.cvtColor(bgr, result, cv.COLOR_BGR2RGBA);
            L.delete();
            channels.delete();
            lab.delete();
            bgr.delete();
            return result;
        }
        return src;
    }

    /** Draws cv.Mat onto an <img> element. */
    function matToImg(mat, imgEl) {
        const canvas = document.createElement("canvas");
        canvas.width = mat.cols;
        canvas.height = mat.rows;
        cv.imshow(canvas, mat);
        imgEl.src = canvas.toDataURL("image/png");
        imgEl.style.display = "block";
    }

    /* ---------- Tabs ---------- */
    tabBtns.forEach((btn) => {
        btn.addEventListener("click", () => activateTab(btn.dataset.tab));
    });

    function activateTab(id) {
        tabBtns.forEach((b) =>
            b.classList.toggle("active", b.dataset.tab === id),
        );
        tabPanels.forEach((p) =>
            p.classList.toggle("active", p.id === "panel-" + id),
        );
    }

    /* ---------- Download All ---------- */
    downloadBtn.addEventListener("click", () => {
        const keys = ["grid", "notan", "edges", "sketch", "shading", "values"];
        for (const key of keys) {
            const mat = results[key];
            if (!mat) continue;
            const canvas = document.createElement("canvas");
            canvas.width = mat.cols;
            canvas.height = mat.rows;
            cv.imshow(canvas, mat);
            const a = document.createElement("a");
            a.download = "realsketch_" + key + ".png";
            a.href = canvas.toDataURL("image/png");
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }
    });

    /* ---------- Service Worker ---------- */
    if ("serviceWorker" in navigator) {
        navigator.serviceWorker
            .register("./sw.js")
            .then(() => console.log("SW registered"))
            .catch((e) => console.warn("SW error:", e));
    }
})();
