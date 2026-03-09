/* ============================================================
   RealSketch — 100% client-side image processing
   Uses OpenCV.js (loaded from CDN in index.html).
   Replicates the Python pipeline with auto-adaptation for any image.
   ============================================================ */

// eslint-disable-next-line no-unused-vars
const RealSketchProcessing = (() => {
    "use strict";

    /* ---------- helpers ---------- */

    /** Percentile over a single-channel cv.Mat (uint8). */
    function percentile(gray, pct) {
        const data = gray.data;
        const len = data.length;
        const sorted = new Uint8Array(len);
        sorted.set(data);
        sorted.sort();
        const idx = Math.min(Math.floor((pct / 100) * len), len - 1);
        return sorted[idx];
    }

    /** Ensure blockSize is odd and >= 3. */
    function oddBlock(v) {
        let b = Math.max(3, Math.round(v));
        if (b % 2 === 0) b += 1;
        return b;
    }

    /* ================================================================
     1. SKETCH — pencil-style lines (bilateral + adaptive threshold)
     ================================================================ */
    function generateSketch(src) {
        const gray = new cv.Mat();
        cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY);

        const h = gray.rows;
        const w = gray.cols;
        const shortSide = Math.min(h, w);

        // -- Normalize contrast if needed --
        const lo = percentile(gray, 2);
        const hi = percentile(gray, 98);
        if (hi - lo < 100) {
            try {
                const clahe = new cv.CLAHE(3.0, new cv.Size(8, 8));
                clahe.apply(gray, gray);
                clahe.delete();
            } catch (_) {
                cv.equalizeHist(gray, gray);
            }
        }

        // -- Median (adapted to resolution) --
        const medK = shortSide < 600 ? 5 : 7;
        cv.medianBlur(gray, gray, medK);

        // -- Bilateral x2 (smooth while preserving edges) --
        const sigma = Math.max(50, Math.min(200, Math.floor(shortSide / 4)));
        const tmp = new cv.Mat();
        cv.bilateralFilter(gray, tmp, 9, sigma, sigma);
        cv.bilateralFilter(tmp, gray, 7, sigma, sigma);
        tmp.delete();

        // -- Adaptive threshold --
        const block = oddBlock(
            Math.max(9, Math.min(17, Math.floor(shortSide / 80))),
        );
        const C_val = hi - lo > 120 ? 3 : 2;
        const edges = new cv.Mat();
        cv.adaptiveThreshold(
            gray,
            edges,
            255,
            cv.ADAPTIVE_THRESH_MEAN_C,
            cv.THRESH_BINARY,
            block,
            C_val,
        );
        gray.delete();

        // -- Morphological opening --
        const kernel = cv.getStructuringElement(
            cv.MORPH_ELLIPSE,
            new cv.Size(2, 2),
        );
        cv.morphologyEx(edges, edges, cv.MORPH_OPEN, kernel);
        kernel.delete();

        // -- Paper background --
        const result = new cv.Mat(h, w, cv.CV_8UC4);
        const ed = edges.data;
        const rd = result.data;
        for (let i = 0, j = 0; i < ed.length; i++, j += 4) {
            const v = Math.min(248, Math.round(ed[i] * (220 / 255) + 28));
            rd[j] = v;
            rd[j + 1] = v;
            rd[j + 2] = v;
            rd[j + 3] = 255;
        }
        edges.delete();
        return result;
    }

    /* ================================================================
     2. SHADING — 4 zones + light arrow
     ================================================================ */
    const ZONE_RGBA = {
        light: [230, 235, 240, 255],
        mid: [155, 155, 155, 255],
        shadow: [75, 70, 65, 255],
        deep: [30, 28, 25, 255],
    };
    const ARROW_COLOR = [100, 180, 255, 255];

    function generateShading(src) {
        const gray = new cv.Mat();
        cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY);
        cv.GaussianBlur(gray, gray, new cv.Size(9, 9), 0);

        // Adaptive CLAHE
        const lo = percentile(gray, 2);
        const hi = percentile(gray, 98);
        const clip = hi - lo < 100 ? 3.0 : 2.0;
        try {
            const clahe = new cv.CLAHE(clip, new cv.Size(8, 8));
            clahe.apply(gray, gray);
            clahe.delete();
        } catch (_) {
            cv.equalizeHist(gray, gray);
        }

        const h = gray.rows,
            w = gray.cols;
        const gd = gray.data;

        // Percentiles for zones
        const p25 = percentile(gray, 25);
        const p50 = percentile(gray, 50);
        const p75 = percentile(gray, 75);

        // Create canvas with zones
        const result = new cv.Mat(h, w, cv.CV_8UC4);
        const rd = result.data;
        for (let i = 0; i < gd.length; i++) {
            const v = gd[i];
            let c;
            if (v >= p75) c = ZONE_RGBA.light;
            else if (v >= p50) c = ZONE_RGBA.mid;
            else if (v >= p25) c = ZONE_RGBA.shadow;
            else c = ZONE_RGBA.deep;
            const j = i * 4;
            rd[j] = c[0];
            rd[j + 1] = c[1];
            rd[j + 2] = c[2];
            rd[j + 3] = c[3];
        }

        // Smooth edges between zones
        cv.GaussianBlur(result, result, new cv.Size(5, 5), 0);

        // -- Light detection 3×3 sectors --
        const th = Math.floor(h / 3),
            tw = Math.floor(w / 3);
        let maxBright = -1,
            sx = 0,
            sy = 0;
        for (let ri = 0; ri < 3; ri++) {
            for (let ci = 0; ci < 3; ci++) {
                const r0 = ri * th,
                    c0 = ci * tw;
                const r1 = Math.min(r0 + th, h),
                    c1 = Math.min(c0 + tw, w);
                let sum = 0,
                    count = 0;
                for (let r = r0; r < r1; r++) {
                    for (let c = c0; c < c1; c++) {
                        sum += gd[r * w + c];
                        count++;
                    }
                }
                const avg = sum / Math.max(count, 1);
                if (avg > maxBright) {
                    maxBright = avg;
                    sx = c0 + Math.floor(tw / 2);
                    sy = r0 + Math.floor(th / 2);
                }
            }
        }
        gray.delete();

        // Arrow from brightest sector towards center
        const cx = Math.floor(w / 2),
            cy = Math.floor(h / 2);
        const dx = cx - sx,
            dy = cy - sy;
        const len = Math.max(1, Math.sqrt(dx * dx + dy * dy));
        const aLen = Math.floor(Math.min(h, w) / 6);
        const ex = sx + Math.round((dx / len) * aLen);
        const ey = sy + Math.round((dy / len) * aLen);
        const thick = Math.max(2, Math.floor(Math.min(h, w) / 300));

        // Draw arrow manually (cv.arrowedLine not available in OpenCV.js)
        const arrowColor = new cv.Scalar(
            ARROW_COLOR[0],
            ARROW_COLOR[1],
            ARROW_COLOR[2],
            255,
        );
        cv.line(
            result,
            new cv.Point(sx, sy),
            new cv.Point(ex, ey),
            arrowColor,
            thick,
            cv.LINE_AA,
        );
        // Arrowhead
        const tipLen = aLen * 0.3;
        const adx = ex - sx,
            ady = ey - sy;
        const alen2 = Math.max(1, Math.sqrt(adx * adx + ady * ady));
        const ux = adx / alen2,
            uy = ady / alen2;
        const px = -uy,
            py = ux; // perpendicular
        const lx = Math.round(ex - ux * tipLen + px * tipLen * 0.5);
        const ly = Math.round(ey - uy * tipLen + py * tipLen * 0.5);
        const rx = Math.round(ex - ux * tipLen - px * tipLen * 0.5);
        const ry = Math.round(ey - uy * tipLen - py * tipLen * 0.5);
        cv.line(
            result,
            new cv.Point(ex, ey),
            new cv.Point(lx, ly),
            arrowColor,
            thick,
            cv.LINE_AA,
        );
        cv.line(
            result,
            new cv.Point(ex, ey),
            new cv.Point(rx, ry),
            arrowColor,
            thick,
            cv.LINE_AA,
        );

        const fs = Math.max(0.35, Math.min(h, w) / 1500);
        cv.putText(
            result,
            "Light",
            new cv.Point(sx - Math.round(12 * fs), sy - Math.round(12 * fs)),
            cv.FONT_HERSHEY_SIMPLEX,
            fs,
            new cv.Scalar(ARROW_COLOR[0], ARROW_COLOR[1], ARROW_COLOR[2], 255),
            Math.max(1, thick - 1),
            cv.LINE_AA,
        );

        // Legend
        _drawLegend(result, [
            { label: "Light (leave)", color: ZONE_RGBA.light },
            { label: "Mid (soft)", color: ZONE_RGBA.mid },
            { label: "Shadow (strong)", color: ZONE_RGBA.shadow },
            { label: "Deep (dense)", color: ZONE_RGBA.deep },
        ]);

        return result;
    }

    /* ================================================================
     3. VALUES — tonal map quantized to 5 levels
     ================================================================ */
    const TONE_VALUES = [230, 180, 130, 75, 25];
    const TONE_LABELS = ["Light", "Mid-light", "Midtone", "Shadow", "Deep"];

    function generateToneMap(src) {
        const gray = new cv.Mat();
        cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY);

        // CLAHE
        try {
            const clahe = new cv.CLAHE(2.5, new cv.Size(8, 8));
            clahe.apply(gray, gray);
            clahe.delete();
        } catch (_) {
            cv.equalizeHist(gray, gray);
        }

        cv.GaussianBlur(gray, gray, new cv.Size(5, 5), 0);

        const h = gray.rows,
            w = gray.cols;
        const gd = gray.data;

        // Adaptive percentiles
        const levels = 5;
        const pcts = [];
        for (let i = 0; i <= levels; i++) pcts.push(i * (100 / levels));
        const thresholds = pcts.map((p) => percentile(gray, p));

        // Quantize
        const result = new cv.Mat(h, w, cv.CV_8UC4);
        const rd = result.data;
        for (let i = 0; i < gd.length; i++) {
            const v = gd[i];
            let toneIdx = levels - 1;
            for (let t = 0; t < levels; t++) {
                const lo = thresholds[t];
                const hi = t < levels - 1 ? thresholds[t + 1] : 256;
                if (v >= lo && v < hi) {
                    toneIdx = t;
                    break;
                }
            }
            const tv = TONE_VALUES[levels - 1 - toneIdx];
            const j = i * 4;
            rd[j] = tv;
            rd[j + 1] = tv;
            rd[j + 2] = tv;
            rd[j + 3] = 255;
        }
        gray.delete();

        // Legend
        _drawLegend(
            result,
            TONE_LABELS.map((lbl, i) => ({
                label: lbl,
                color: [TONE_VALUES[i], TONE_VALUES[i], TONE_VALUES[i], 255],
            })),
        );

        return result;
    }

    /* ================================================================
     Shared legend (bottom-right corner)
     ================================================================ */
    function _drawLegend(mat, items) {
        const h = mat.rows,
            w = mat.cols;
        const n = items.length;
        // Smaller legend — 60% of previous size
        const base = Math.min(h, w);
        const fs = Math.max(0.35, base / 1500);
        const thick = Math.max(1, Math.round(fs * 1.2));
        const bw = Math.round(12 * (fs / 0.35));
        const bh = Math.round(9 * (fs / 0.35));
        const gap = Math.round(3 * (fs / 0.35));
        const pad = Math.round(5 * (fs / 0.35));

        // Estimate text width (cv.getTextSize not available in OpenCV.js)
        let maxTw = 0;
        for (const it of items) {
            const estW = Math.round(it.label.length * 8 * (fs / 0.35));
            maxTw = Math.max(maxTw, estW);
        }

        const lw = bw + maxTw + pad * 3 + 6;
        const lh = n * (bh + gap) - gap + pad * 2;
        const margin = Math.round((10 * fs) / 0.55);
        const x0 = w - lw - margin;
        const y0 = h - lh - margin;

        // Semi-transparent background (draw a dark rectangle with manual alpha blend)
        const bgColor = new cv.Scalar(30, 28, 25, 220);
        cv.rectangle(
            mat,
            new cv.Point(x0, y0),
            new cv.Point(x0 + lw, y0 + lh),
            bgColor,
            cv.FILLED,
        );
        const brd = new cv.Scalar(100, 100, 100, 255);
        cv.rectangle(
            mat,
            new cv.Point(x0, y0),
            new cv.Point(x0 + lw, y0 + lh),
            brd,
            1,
        );

        for (let i = 0; i < n; i++) {
            const y = y0 + pad + i * (bh + gap);
            const x = x0 + pad;
            const c = items[i].color;
            cv.rectangle(
                mat,
                new cv.Point(x, y),
                new cv.Point(x + bw, y + bh),
                new cv.Scalar(c[0], c[1], c[2], 255),
                cv.FILLED,
            );
            cv.rectangle(
                mat,
                new cv.Point(x, y),
                new cv.Point(x + bw, y + bh),
                new cv.Scalar(120, 120, 120, 255),
                1,
            );

            const ty = y + bh - Math.round(2 * (fs / 0.35));
            cv.putText(
                mat,
                items[i].label,
                new cv.Point(x + bw + pad, ty),
                cv.FONT_HERSHEY_SIMPLEX,
                fs,
                new cv.Scalar(220, 220, 220, 255),
                thick,
                cv.LINE_AA,
            );
        }
    }

    /* ---------- Public API ---------- */
    return {
        generateSketch,
        generateShading,
        generateToneMap,
        generateGrid,
        generateEdgeMap,
        generateNotan,
    };

    /* ================================================================
     4. GRID — proportional grid overlay on the original
     ================================================================ */
    function generateGrid(src) {
        // Copy original to RGBA result
        const result = src.clone();
        const h = result.rows,
            w = result.cols;
        const shortSide = Math.min(h, w);

        // Grid density: 4×4 main + 2 diagonals
        const cols = 4,
            rows = 4;
        const thick = Math.max(1, Math.round(shortSide / 500));
        const thinT = Math.max(1, thick - 1);
        const gridColor = new cv.Scalar(0, 200, 255, 200); // cyan
        const diagColor = new cv.Scalar(255, 100, 200, 140); // pink
        const numColor = new cv.Scalar(0, 200, 255, 255);

        // Vertical lines
        for (let c = 1; c < cols; c++) {
            const x = Math.round((c / cols) * w);
            cv.line(
                result,
                new cv.Point(x, 0),
                new cv.Point(x, h - 1),
                gridColor,
                thick,
                cv.LINE_AA,
            );
        }
        // Horizontal lines
        for (let r = 1; r < rows; r++) {
            const y = Math.round((r / rows) * h);
            cv.line(
                result,
                new cv.Point(0, y),
                new cv.Point(w - 1, y),
                gridColor,
                thick,
                cv.LINE_AA,
            );
        }
        // Diagonals (helps find center + angles)
        cv.line(
            result,
            new cv.Point(0, 0),
            new cv.Point(w - 1, h - 1),
            diagColor,
            thinT,
            cv.LINE_AA,
        );
        cv.line(
            result,
            new cv.Point(w - 1, 0),
            new cv.Point(0, h - 1),
            diagColor,
            thinT,
            cv.LINE_AA,
        );

        // Cross at center
        const cx = Math.floor(w / 2),
            cy = Math.floor(h / 2);
        const crSize = Math.round(shortSide / 30);
        cv.line(
            result,
            new cv.Point(cx - crSize, cy),
            new cv.Point(cx + crSize, cy),
            gridColor,
            thick + 1,
            cv.LINE_AA,
        );
        cv.line(
            result,
            new cv.Point(cx, cy - crSize),
            new cv.Point(cx, cy + crSize),
            gridColor,
            thick + 1,
            cv.LINE_AA,
        );

        // Cell labels (A1, A2, ... D4)
        const fs = Math.max(0.4, shortSide / 1200);
        const labels = "ABCD";
        for (let r = 0; r < rows; r++) {
            for (let c = 0; c < cols; c++) {
                const lbl = labels[r] + (c + 1);
                const tx =
                    Math.round((c / cols) * w) + Math.round(5 * (fs / 0.4));
                const ty =
                    Math.round((r / rows) * h) + Math.round(16 * (fs / 0.4));
                cv.putText(
                    result,
                    lbl,
                    new cv.Point(tx, ty),
                    cv.FONT_HERSHEY_SIMPLEX,
                    fs,
                    numColor,
                    Math.max(1, Math.round(fs * 1.5)),
                    cv.LINE_AA,
                );
            }
        }

        return result;
    }

    /* ================================================================
     5. EDGE MAP — hard / medium / soft edges with varying line weight
     Key for graphite realism: shows WHERE to press hard vs blend
     ================================================================ */
    function generateEdgeMap(src) {
        const gray = new cv.Mat();
        cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY);
        const h = gray.rows,
            w = gray.cols;
        const shortSide = Math.min(h, w);

        // Smooth
        cv.GaussianBlur(gray, gray, new cv.Size(3, 3), 0);

        // --- Three edge scales via Difference of Gaussians ---

        // Hard edges (fine detail: eyes, nostrils, lip line)
        const blur1 = new cv.Mat(),
            blur2 = new cv.Mat();
        cv.GaussianBlur(gray, blur1, new cv.Size(1, 1), 0.5);
        cv.GaussianBlur(gray, blur2, new cv.Size(3, 3), 1.0);
        const dog1 = new cv.Mat();
        cv.subtract(blur1, blur2, dog1);
        blur1.delete();
        blur2.delete();

        // Medium edges (cheekbones, jaw, brows)
        const blur3 = new cv.Mat(),
            blur4 = new cv.Mat();
        cv.GaussianBlur(gray, blur3, new cv.Size(3, 3), 1.5);
        cv.GaussianBlur(gray, blur4, new cv.Size(7, 7), 3.0);
        const dog2 = new cv.Mat();
        cv.subtract(blur3, blur4, dog2);
        blur3.delete();
        blur4.delete();

        // Soft edges (forehead to background, hair mass)
        const blur5 = new cv.Mat(),
            blur6 = new cv.Mat();
        cv.GaussianBlur(gray, blur5, new cv.Size(7, 7), 3.0);
        cv.GaussianBlur(gray, blur6, new cv.Size(15, 15), 6.0);
        const dog3 = new cv.Mat();
        cv.subtract(blur5, blur6, dog3);
        blur5.delete();
        blur6.delete();
        gray.delete();

        // Threshold each scale
        const hardEdge = new cv.Mat(),
            medEdge = new cv.Mat(),
            softEdge = new cv.Mat();
        cv.threshold(dog1, hardEdge, 8, 255, cv.THRESH_BINARY);
        cv.threshold(dog2, medEdge, 5, 255, cv.THRESH_BINARY);
        cv.threshold(dog3, softEdge, 3, 255, cv.THRESH_BINARY);
        dog1.delete();
        dog2.delete();
        dog3.delete();

        // Compose: paper background + colored edges
        // Hard = dark black (B=2), Medium = dark gray (B=80), Soft = light gray (B=170)
        const result = new cv.Mat(h, w, cv.CV_8UC4);
        const rd = result.data;
        const hd = hardEdge.data,
            md = medEdge.data,
            sd = softEdge.data;

        for (let i = 0; i < hd.length; i++) {
            const j = i * 4;
            const isHard = hd[i] > 0;
            const isMed = md[i] > 0;
            const isSoft = sd[i] > 0;

            if (isHard) {
                // Hard edge: dark, thick look — near black
                rd[j] = 15;
                rd[j + 1] = 15;
                rd[j + 2] = 15;
                rd[j + 3] = 255;
            } else if (isMed) {
                // Medium edge: mid-gray
                rd[j] = 100;
                rd[j + 1] = 100;
                rd[j + 2] = 100;
                rd[j + 3] = 255;
            } else if (isSoft) {
                // Soft/lost edge: light gray, barely visible
                rd[j] = 190;
                rd[j + 1] = 190;
                rd[j + 2] = 190;
                rd[j + 3] = 255;
            } else {
                // Paper
                rd[j] = 245;
                rd[j + 1] = 243;
                rd[j + 2] = 240;
                rd[j + 3] = 255;
            }
        }
        hardEdge.delete();
        medEdge.delete();
        softEdge.delete();

        // Small legend
        _drawLegend(result, [
            { label: "Hard (press)", color: [15, 15, 15, 255] },
            { label: "Medium", color: [100, 100, 100, 255] },
            { label: "Soft (blend)", color: [190, 190, 190, 255] },
        ]);

        return result;
    }

    /* ================================================================
     6. NOTAN — 2-value study (light vs shadow masses)
     The first planning step in any realist drawing
     ================================================================ */
    function generateNotan(src) {
        const gray = new cv.Mat();
        cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY);
        const h = gray.rows,
            w = gray.cols;

        // Normalize
        try {
            const clahe = new cv.CLAHE(2.0, new cv.Size(8, 8));
            clahe.apply(gray, gray);
            clahe.delete();
        } catch (_) {
            cv.equalizeHist(gray, gray);
        }

        // Strong blur so we see BIG shapes, not detail
        const kSize = oddBlock(Math.max(9, Math.floor(Math.min(h, w) / 40)));
        cv.GaussianBlur(gray, gray, new cv.Size(kSize, kSize), 0);

        // Simple threshold at median → 2 values
        const median = percentile(gray, 50);
        const result = new cv.Mat(h, w, cv.CV_8UC4);
        const gd = gray.data;
        const rd = result.data;
        for (let i = 0; i < gd.length; i++) {
            const j = i * 4;
            if (gd[i] >= median) {
                // Light mass: warm white paper
                rd[j] = 245;
                rd[j + 1] = 242;
                rd[j + 2] = 235;
                rd[j + 3] = 255;
            } else {
                // Shadow mass: rich dark
                rd[j] = 25;
                rd[j + 1] = 22;
                rd[j + 2] = 20;
                rd[j + 3] = 255;
            }
        }
        gray.delete();

        // Legend
        _drawLegend(result, [
            { label: "Light mass", color: [245, 242, 235, 255] },
            { label: "Shadow mass", color: [25, 22, 20, 255] },
        ]);

        return result;
    }
})();
