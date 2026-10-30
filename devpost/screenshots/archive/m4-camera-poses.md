# Milestone 4 screenshot camera poses (Lens Studio 5.24 Interactive Preview)

> **28 Oct 2026, after the demo look pass:** the whole scene was raised 15 cm so the plinth stands on the Evening Room floor. Add **+15 to every y** (positions and look-at points) in the tables below; x and z are unchanged. The preview scene is now "Evening Room", not "Plane".

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

## Milestone 5 revision screenshot camera poses (sightlines + lit contrast)

Interior walls were lowered (great hall side/back walls and the first partition to 1/3 of the
façade height, the vestibule and sanctuary partitions to 1/4) and the lit statues got a gold
tint, a halo card and a floor pool. Lock triggered at (114, −22, −40) looking at
(29.5, −49.6, −85.9) with `debugFreezeAt` 13; standing height = eye at y 0, 65 cm above the plinth top.

| File | What it shows | Position (x, y, z) | Look at (x, y, z) | Rotation reported |
|---|---|---|---|---|
| m5r-a-aligned-spot-standing.png | Standing on the floor ring (aligned spot, 70 cm from the entrance): the lit sanctuary seen over the façade top | (89, 0, −57) | (−10, −62, −128) | (333.0, 54.4, 0) |
| m5r-a-aligned-spot-standing-sanctuary-crop.png | 300 × 400 px crop of the above around the sanctuary, enlarged 3× | same | same | same |
| m5r-b-beside-plinth-sanctuary-side.png | Standing beside the plinth at the sanctuary end, 35 cm out from the axis, three-quarter view: three gold statues, Ptah (nearest) plain | (−20.1, 0, −91.2) | (−28.7, −61, −140) | (309.1, 10.0, 0) |
| m5r-c-sanctuary-closeup-lit.png | Close on the sanctuary from above the vestibule: halos behind, pools in front, Ptah left | (−12, −40, −126) | (−28.5, −61, −141) | (316.7, 47.7, 0) |

## Milestone 6 screenshot camera poses (viewing spot, narration, Try again)

Lock triggered at (114, −22, −40) looking at (29.5, −49.6, −85.9); the sequence ran in real time (no freeze).

| File | What it shows | When | Position (x, y, z) | Look at (x, y, z) | Rotation reported |
|---|---|---|---|---|---|
| m6-a-viewing-spot-marker-after-lock.png | The softer viewing-spot ring beside the plinth at the sanctuary end, a few seconds after lock | lock + ~5 s | (45, −10, −25) | (−20, −150, −90) | (303.3, 45, 0) |
| m6-b-caption-mid-narration.png | Narration caption strip near the sanctuary end, seen from the viewing spot, lit statues behind | lock + ~25 s | (−20.1, 0, −91.2) | (−31, −60, −142) | (310.9, 12.1, 0) |
| m6-c-try-again-button.png | "Try again" pinch button on the plinth's front-right corner, from the aligned side | lock + ~54 s | (89, −10, −57) | (48.7, −61, −112.8) | (323.5, 35.8, 0) |

The pinch test used Lens Studio's preview input injection: with the camera aimed at the button (so it sits at render-space 0.5, 0.5), a touch start → move → end at that point, 250 ms apart, drives SIK's mouse interactor and fires the button's trigger-up.

## Milestone 7 screenshot camera poses (polish pass)

Preview device SPECS 27 (per-eye 26.8° × 36.6°, about 45° diagonal, from the device descriptor); the scene camera inherits the device FOV.

| File | What it shows | Position (x, y, z) | Look at / rotation | Notes |
|---|---|---|---|---|
| m7-a-opening-onboarding-caption.png | The opening from the start position: temple risen, sun on the viewer's line, "Abu Simbel, at dawn" just above the plinth's near edge | (0, 0, 0) | reset, pitch −16° | about 2 s after start |
| m7-b-entrance-mid-rise.png | The temple half-way out of the plinth with the warm entrance glow | (0, 0, 0) | reset, pitch −16° | `debugFreezeAt` 1.0 on the Temple Entrance script (back to −1 in the commit) |
| m7-c1-start-left.png | Start position 60 cm to the left: temple, sun and caption all in the frame | (−60, 0, 0) | (0, −50, −120) | pass 1 of the scripted loop |
| m7-c2-aligned-spot-locked.png | The aligned spot during the reveal (before the narration caption was moved to the viewing-spot side) | (89, −34, −57) | (31.9, −58, −97.6) | the narration caption used to sit behind the sun from here |
| m7-d-grazing-beam-check.png | Grazing angle along the axis from behind the sanctuary at wall height: beam, pools, halos; two consecutive captures differ in 0 pixels outside the caption | (−62, −49, −162) | (12, −63, −111) | flicker / z-fight check |
| m7-c3-start-centre.png | Start position, centre: temple, sun and caption in frame | (0, 0, 0) | (0, −50, −120) | pass 2 |
| m7-c4-viewing-spot-beam.png | Viewing spot during the reveal (narration caption still on the near side, since moved) | (−20.1, 0, −91.2) | (−31, −60, −142) | pass 2 |
| m7-c5-start-right.png | Start position 60 cm to the right | (60, 0, 0) | (0, −50, −120) | pass 3 |
| m7-c6-viewing-spot-narration.png | Viewing spot mid-narration with the caption on the far side of the sanctuary, scale 1.5 | (−20.1, 0, −91.2) | (−31, −60, −142) | final check run |

## Demo look pass (Evening Room, scene raised 15 cm)

| File | What it shows | Position (x, y, z) | Look at / rotation |
|---|---|---|---|
| look-after-start.png | Start position in the Evening Room: stone plinth, temple risen, onboarding caption | (0, 0, 0) | reset, pitch −16° |
| look-after-aligned-spot.png | Ring spot, locked, reveal frozen at its end | (89, −19, −57) | (31.9, −43, −97.6) |
| look-after-viewing-spot.png | Viewing spot, lit sanctuary, closing caption | (−20.1, 15, −91.2) | (−31, −45, −142) |
