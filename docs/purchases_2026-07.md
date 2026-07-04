# Purchase list — July 2026

## 1. Second launcher motor — RESOLVED 2026-07-04, DO NOT BUY

AJ already owns two motors: a QWinOut A2212 **1400KV** (w/ X-mount) and an A2212-class **1000KV**.
Plan: mixed-KV pair — **1400KV on TOP** (topspin headroom), 1000KV on bottom. On 3S the
1000KV still gives ~11k rpm no-load ≈ 35 m/s surface speed on a 60mm wheel — far above launch needs.
Software support added: `ThrottleMap.top_rpm_at_full` / `bottom_rpm_at_full` per-wheel overrides
(measure each wheel's rpm at throttle 1.0 during calibration). Set `LaunchGeometry.max_wheel_rpm`
to the **slower** (bottom/1000KV) wheel's measured ceiling.

Possible instead: **one more 30A ESC** — but June notes say four 30A ESCs are owned (two spares).
Check the parts bin first. If actually short: any 20–30A SimonK/BLHeli ESC with standard 50Hz
servo-PWM input works with the PCA9685 + `esc_calibrate.py` teach flow (~$9–12 on Amazon).

<details><summary>Original motor research (kept for reference)</summary>

### Second A2212 1400KV motor (launcher wheel #2)

**Recommended: QWinOut A2212 1400KV 10T single, with X-mount + prop adapter (Amazon, ~$10–13, Prime)**
- Link: https://www.amazon.com/QWinOut-Brushless-Outrunner-KKmulticopter-Quadcopter/dp/B07VR99T5M
- Includes the silver cross X-mount and bullet prop adapter — matches the existing mount pattern (memory: A2212 mount pattern, coupon v3 fits).
- QWinOut's own store lists the same unit at $9.61 (reg. $14.42), so expect low-teens on Amazon; verify price/Prime badge at checkout.
- Rationale: single unit, fast shipping, same generic XXD-style A2212 family as the existing motor, hardware included.

**Alternates**
- eBay singles, $5.99–$9.89 (+ up to ~$7 ship): https://www.ebay.com/sch/i.html?_nkw=a2212+1400kv&_sop=12 — cheapest, but slower and mount hardware varies by listing; 4-packs ~$21.58 (~$5.40/motor) if spares are wanted.
- JSumo A2212 1400KV, $10.91, 41 in stock, cross mount + prop adapter + pre-soldered 3.5mm bullets included: https://www.jsumo.com/a2212-1400kv-outrunner-brushless-motor — good spec page, but ships from Turkey (slow to US).
- Amazon 4-pack option (motors + 4× ESC + props, QWinOut): https://www.amazon.com/QWinOut-Brushless-Outrunner-Firmware-Propeller/dp/B08L7P9ZW8 — redundant ESCs (he owns four 30A already), only worth it if per-unit price beats singles.

**Matching note:** "A2212 1400KV" listings come in 10T and 13T winds — pick 10T to match the typical existing unit (check the wind stamped on the current motor's bell). Small KV variance between clones is normal; trim per-wheel throttle in software if wheel speeds differ.

</details>

## 2. 5V/5A+ servo rail UBEC (replace 5V/3A rail)

**Recommended: Hobbywing UBEC 8A (2-3S input, 5V/6V out, 8A cont / 15A burst) — $20 at Aloft Hobbies**
- Link: https://alofthobbies.com/products/hobbywing-8a-ubec
- Stock note: low stock, 2 left at time of research (2026-07-04) — order promptly or fall back to alternates.
- Rationale: 2-3S input matches the launcher pack exactly; 8A continuous gives real headroom for 3–4 MG996R stall transients (each can spike ~2.5A), where a 5A unit would be at its limit.

**Alternates**
- Hobbywing UBEC 5A Air (2-8S in, 5.0/6.0/7.4V out, 5A cont / 15A peak), $15 at Aloft: https://alofthobbies.com/products/hobbywing-ubec-5a-air-2-8s (10 in stock) — meets the ≥5A spec, lighter/smaller.
- Amazon fast-ship generics (~$10–15, Prime): Readytosky 5V UBEC 5A B0CZ81Z25S (https://www.amazon.com/Readytosky-DC-DC-Voltage-Converter-Module/dp/B0CZ81Z25S) or 2-8S UBEC-8A 5.2/6/7.4/8.4V (https://www.amazon.com/UBEC-8A-Servo-Independent-Supply-Airplane/dp/B0CN3429PF) — if the Hobbywing 8A sells out.

**Wiring notes**
- UBEC 5V out → PCA9685 servo V+ rail only. Do NOT feed the Pi from this rail; Pi keeps its own 5V supply.
- Common ground: UBEC GND, PCA9685 GND, and Pi GND must be tied together (signal reference).
- Keep the old 5V/3A supply as a spare or dedicate it to the Pi.
- Set the UBEC's voltage switch to 5V before connecting (MG996R tolerates 6V, but PCA9685 V+ rail with anything else attached is safest at 5V).
