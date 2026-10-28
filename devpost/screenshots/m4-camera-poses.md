# Milestone 4 screenshot camera poses (Lens Studio 5.24 Interactive Preview)

World units are cm; the viewer starts at the origin facing −Z. Poses are the preview
camera's position and the point it looks at (Inspector coordinates), plus the resulting
rotation (pitch x, yaw y) that `MovePreviewCamera getPose` reported. Preview device
SPECS 27, Interactive scene "Plane".

| File | What it shows | Position (x, y, z) | Look at (x, y, z) | Rotation reported (x, y, z) | Script readout |
|---|---|---|---|---|---|
| m4-1-start-not-aligned.png | Start pose, sun on the viewer's line, no cues | (0, 0, 0) | reset, then pitch −27° | (333, 0, 0) | az 73°, el 32°, dist 103 cm, score 0.00 |
| m4-2-partway-cues-building.png | 10° off the axis, 80 cm from the entrance, shaft faint, sun over the façade | (88.5, −20, −41) | (31.9, −58, −97.6) | (334.6, 45, 0) | az 10°, el 29°, dist 80 cm, score 0.47 |
| m4-3-locked-caption.png | Locked on the axis 100 cm out, caption up, shaft full | (114, −22, −40) | (29.5, −49.6, −85.9) | (344.0, 61.5, 0) | az 0.1°, el 22.7°, dist 100 cm, score 1.00, ALIGNED |
| m4-4-floor-ring-locked.png | Bonus: the floor ring at the viewer's feet while locked (view lowered to 34 cm below start) | (89, −34, −57) | (62, −159, −78) | (279.3, 0, 347.8) | az 0.5°, el 23°, dist 70 cm, score 1.00, ALIGNED |

The lock for m4-3 was first triggered at the ring, pose (89, −34, −57) looking at the
doorway (31.9, −58, −97.6); the camera was then moved out to 100 cm for the framing.
The caption was held on screen with the script's `debugHoldCaption` input (off in the commit).

## Milestone 5 screenshot camera poses

The lock was triggered first at the aligned pose (114, −22, −40) looking at (29.5, −49.6, −85.9); the reveal script's `debugFreezeAt` input held the sequence clock at the stated time while the camera was moved (input back to −1 in the commit).

| File | What it shows | Sequence time | Position (x, y, z) | Look at (x, y, z) | Rotation reported |
|---|---|---|---|---|---|
| m5-a-light-halfway-great-hall.png | Standing height behind the sanctuary, looking down the axis: patch halfway down the great hall, shaft back to the doorway, cue shaft up to the sun | +4.6 s | (−49, 0, −154) | (12, −63, −111) | (139.8, 305.2, 180) |
| m5-b-sanctuary-three-lit-ptah-dark.png | Close on the sanctuary from above the vestibule: three statues lit, Ptah (nearest) at base | +13 s (complete) | (−19.7, −31, −133.8) | (−28.7, −62, −140) | (280.9, 0, 343.8) |
| m5-c-full-temple-end-from-aligned-spot.png | Standing at the aligned spot at the end of the sequence | +13 s (complete) | (114, 0, −40) | (0, −58, −120) | (337.4, 54.9, 0) |

Note on (a): from standing height beside the plinth the half-height side walls hide the hall floor, so the shot is taken along the axis from behind the sanctuary, where the sightline clears the walls.
