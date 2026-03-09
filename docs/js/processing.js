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
            const clahe = new cv.CLAHE(3.0, new cv.Size(8, 8));
            clahe.apply(gray, gray);
            clahe.delete();
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
        const clahe = new cv.CLAHE(clip, new cv.Size(8, 8));
        clahe.apply(gray, gray);
        clahe.delete();

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

        cv.arrowedLine(
            result,
            new cv.Point(sx, sy),
            new cv.Point(ex, ey),
            new cv.Scalar(ARROW_COLOR[0], ARROW_COLOR[1], ARROW_COLOR[2], 255),
            thick,
            cv.LINE_AA,
            0,
            0.3,
        );

        const fs = Math.max(0.5, Math.min(h, w) / 900);
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
        const clahe = new cv.CLAHE(2.5, new cv.Size(8, 8));
        clahe.apply(gray, gray);
        clahe.delete();

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
        const fs = Math.max(0.55, Math.min(h, w) / 900);
        const thick = Math.max(1, Math.round(fs * 1.5));
        const bw = Math.round((28 * fs) / 0.55);
        const bh = Math.round((20 * fs) / 0.55);
        const gap = Math.round((5 * fs) / 0.55);
        const pad = Math.round((10 * fs) / 0.55);

        // Measure text
        let maxTw = 0;
        for (const it of items) {
            const sz = cv.getTextSize(
                it.label,
                cv.FONT_HERSHEY_SIMPLEX,
                fs,
                thick,
            );
            maxTw = Math.max(maxTw, sz.size.width);
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

            const ty = y + bh - Math.round((3 * fs) / 0.55);
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
    return { generateSketch, generateShading, generateToneMap };
})();
