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
