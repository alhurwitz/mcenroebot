# V2 Arm — Bill of Materials

Things you need on top of what you already have (Pi 4, P2S, filament, SG90s, etc.).

## Motors & motion

| Qty | Part | Why | ~Cost |
|---|---|---|---|
| 2 | MG996R metal-gear servo (180°) | J1 yaw + J2 pitch. SG90s won't hold the arm — the metal gears + 11kg-cm torque are the minimum here. | $14 (pair) |
| 1 | A2212 1000KV brushless outrunner | J3 swing motor. Already in the original BOM. | $10 |
| 1 | 30A ESC (e.g. Simonk / BLHeli) | Drives the A2212. Needs OneShot or PWM (Pi can do 50Hz servo PWM, good enough). | $8 |
| 1 | 3S 2200mAh LiPo + balance charger | Powers the BLDC. Don't try running this off the 5V wall wart. | $25 + $20 |
| 1 | XT60 pigtails + power switch | LiPo-to-ESC connection. | $5 |

The 5V/3A supply you have can stay on the Pi + servos circuit. Keep the LiPo
circuit isolated — common ground only.

## Bearings & shafts

| Qty | Part | Where it goes | ~Cost |
|---|---|---|---|
| 2 | 608ZZ skate bearing (8mm bore, 22mm OD) | One in the pitch bracket for swing-axis radial support, one as a yaw-axis thrust support (optional v1) | $4 (pack) |
| 1 | 5mm × 60mm steel rod (or M5 bolt + nuts) | Swing-axis stub shaft on the far side of the swing arm hub | $2 |

## Fasteners

| Qty | Part | Where |
|---|---|---|
| 16+ | M3 × 12mm socket head | General assembly |
| 8 | M3 × 20mm socket head | Paddle clamp through-bolts |
| 8 | M4 × 16mm socket head | Servo ears + base plate to base |
| 1 set | M3 / M4 nylock nuts | Paddle clamp, base plate |
| 4 | M3 × 6mm set screw | Hub-to-shaft on the BLDC (only need 1, the rest are spares) |
| Optional | M3 brass heat-set inserts (10-pack) | If you want stronger threads in PETG. Press in with a soldering iron. | $6 |

## Paddle

| Qty | Part | Notes |
|---|---|---|
| 1 | Cheap recreational ping pong paddle | You'll cut the handle off and clamp the blade. Don't use your nice paddle for this. ~$8 |

## Total new spend (rough)

~$110 if you already have the A2212 from the original BOM, ~$120 with it included. Most of the cost is the LiPo + charger.

## Notes

- **Heat-set inserts are optional but recommended** for the swing arm hub — the
  set-screw will see vibration loads and a bare plastic thread will strip.
- **Don't skip the LiPo balance charger.** Charging a LiPo on a generic wall
  wart is how garage fires start.
- **The 5mm stub shaft on the swing arm far side is a v1.1 upgrade.** First
  prints can run the swing arm cantilevered off the BLDC shaft alone — it's
  marginal but will work for low-rate testing.
