# Sunkeeper — demo video script (target 2:40, hard limit 2:45)

Record the Lens Studio Interactive Preview (SPECS 27 device, scene "Plane") at full panel size.
Camera poses below are Inspector coordinates, taken from `screenshots/m4-camera-poses.md`;
set them with the preview's camera controls or by typing them into the Inspector. Freeze inputs
(`debugFreezeAt` on the Temple Entrance and Sun Reveal scripts, `debugHoldCaption` on Sun
Alignment) hold a moment for a clean take; set them back before committing.

Two voices: **VO** is Mo's recorded voiceover for the video. **Lens** is the in-Lens caption text,
read on screen, never re-voiced. Lines marked **[SPECS LINE]** are the ones to say to camera.

| # | Time | Shot (pose) | On screen | VO |
|---|---|---|---|---|
| 1 | 0:00–0:05 | **Hook.** Sanctuary close-up, end state: Sun Reveal `debugFreezeAt` 13, lock at (114, −22, −40)→(29.5, −49.6, −85.9), camera (−12, −40, −126)→(−28.5, −61, −141) | Three gold statues with halos and pools, Ptah plain | "Twice a year the sun reaches sixty metres into a mountain and lights three gods. Not the fourth." |
| 2 | 0:05–0:20 | **Idea.** Cut to the opening from the start: reset, pitch −16°, live | Temple rising, sun on the viewer's side, "Abu Simbel, at dawn" | "Sunkeeper is a SPECS Lens for travellers, students and museum visitors. It is a tabletop model of the Great Temple of Ramesses II, built around 1264 BCE. You don't tap anything. You find the sun's spot with your own body." |
| 3 | 0:20–0:35 | **Onboarding and entrance.** Temple Entrance `debugFreezeAt` 1.0 for two seconds, then live | Half-risen temple with the warm glow; caption changes to "Find where the sun must stand" | "The temple rises out of the plinth. One line tells you what to do. The sun always hangs on your side of the model: light comes from where you stand." |
| 4 | 0:35–0:55 | **Walk round, cues building.** Keys D then W from the start; pause at (88.5, −20, −41)→(31.9, −58, −97.6) | Floor ring brightening, faint shaft from the doorway to the sun | "As you walk round, a ring on the floor and a shaft from the doorway tell you how close you are to the axis." **[SPECS LINE]** "In the preview I'm pressing keys. On SPECS you'd do this by walking around the table." |
| 5 | 0:55–1:10 | **Get low and lock.** Key Q to (89, −34, −57)→(31.9, −58, −97.6); hold | Ring and shaft at full strength; after a second the caption "Now walk to the side and look inside." | "Get low and in front of the door, where the dawn sun stands in February and October. One second there and the sun locks." |
| 6 | 1:10–1:25 | **Walk to the viewing spot.** Camera along the floor to (−20.1, 0, −91.2)→(−31, −60, −142) | The softer ring beside the plinth fading as you arrive; beam already entering the doorway | "A second ring marks the best place to watch from. The beam gives you eight seconds to get there." |
| 7 | 1:25–1:45 | **The reveal.** Stay at the viewing spot, live | Warm patch travelling the axis, shaft behind it, statues easing up gold one by one | "The light travels the halls, the vestibule, into the sanctuary. Ra-Horakhty, Ramesses, Amun-Ra light up. Ptah, god of the underworld, stays in shadow. Lit one by one for the camera; in reality they light together." |
| 8 | 1:45–2:00 | **Narration excerpt.** Same pose; let two or three captions play | Lens captions: "For over three thousand years" / "the light has kept this appointment," / "every February and October." | *(no VO; let the Lens captions carry it)* |
| 9 | 2:00–2:12 | **Reset.** Camera to (89, −10, −57)→(48.7, −61, −112.8); click Try again | Button on the plinth corner; statues, beam and halos fade over two seconds; sun follows again | "Try again, or just step away, and it fades back to the start." |
| 10 | 2:12–2:38 | **Design process.** Screen recording: `devpost/design-brief.md` top (the one spatial moment, done criteria), then `devpost/asset-review/findings.md` table and `hybrid_top_beam_path.jpg`, then `colossi_before_after.png` | The brief; the inspection table with MISALIGNED / WRONG COUNT; the rebuilt axis with the line of sight | "I planned it with the Devpost Learn skill pack: an interview that became a design brief, with the facts the build had to respect. The AI-generated temple broke them: the interior sat off the axis, five statues, six columns. So the façade stayed and the interior was rebuilt in Blender on the axis, with eight pillars, four pillars and exactly four statues. CLAD built the Lens from the brief, milestone by milestone." |
| 11 | 2:38–2:42 | **Outro.** Back to shot 1's frame | Title card: Sunkeeper — The Secret of Abu Simbel | "Sunkeeper. Find where the sun must stand." |

Running total 2:42. If a take runs long, trim shot 10 first (it can lose the colossi image), then shot 4.

## Voiceover script (read in one pass, about 2:00 of speech)

Twice a year the sun reaches sixty metres into a mountain and lights three gods. Not the fourth.

Sunkeeper is a SPECS Lens for travellers, students and museum visitors. It is a tabletop model of the Great Temple of Ramesses II, built around 1264 BCE. You don't tap anything. You find the sun's spot with your own body.

The temple rises out of the plinth. One line tells you what to do. The sun always hangs on your side of the model: light comes from where you stand.

As you walk round, a ring on the floor and a shaft from the doorway tell you how close you are to the axis. **In the preview I'm pressing keys. On SPECS you'd do this by walking around the table.**

Get low and in front of the door, where the dawn sun stands in February and October. One second there and the sun locks.

A second ring marks the best place to watch from. The beam gives you eight seconds to get there.

The light travels the halls, the vestibule, into the sanctuary. Ra-Horakhty, Ramesses, Amun-Ra light up. Ptah, god of the underworld, stays in shadow. Lit one by one for the camera; in reality they light together.

*(pause for the Lens captions)*

Try again, or just step away, and it fades back to the start.

I planned it with the Devpost Learn skill pack: an interview that became a design brief, with the facts the build had to respect. The AI-generated temple broke them: the interior sat off the axis, five statues, six columns. So the façade stayed and the interior was rebuilt in Blender on the axis, with eight pillars, four pillars and exactly four statues. CLAD built the Lens from the brief, milestone by milestone.

Sunkeeper. Find where the sun must stand.

## Notes
- The in-Lens narration (Mo's recording `Assets/Audio/Narration.mp3` with 14 cued captions, `Assets/Scripts/SunNarration.ts`) is separate from this voiceover and must not be talked over; shot 8 lets it speak for itself, so record the preview's audio for that shot.
- Keep the preview's grid floor: it reads as the room. Hide the Lens Studio panels around the preview if the recorder allows.
- Dates on screen or in VO: "built c. 1264–1244 BCE" in text; "around 1264 BCE" is fine in speech.
