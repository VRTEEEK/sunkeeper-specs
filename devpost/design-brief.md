---
status: approved
---

> **Change log.** 27 Oct 2026: temple asset switched from primitive blocks to Mo's Meshy AI model (see "Temple model" under Where things live, and the README Credits).
> 27 Oct 2026, export: hybrid model exported to `Assets/Temple/Temple.glb` (96k triangles, 2048 px textures, normal map kept, no metallic map), 78 cm long with the origin at the base centre and the façade facing +Z (the viewer). Plinth top enlarged to 60 × 100 cm. **Step B checks:** in Lens Studio confirm the interior reads at least as bright as the façade (dark = transparent on SPECS; lift the interior material if needed), and make the beam a visible glowing shaft seen from above through the open roof, not only light passing through the doorway.
> 27 Oct 2026, later: inspection showed the Meshy interior off-axis with 5 sanctuary statues and 6 columns. Decision: **hybrid**. Keep the Meshy façade, replace the interior with a scripted one on the doorway axis (8 Osiride pillars, 4 pillars, vestibule, 4 separate statues). Details in devpost/asset-review/findings.md.
> 27 Oct 2026, Step B done: `Temple.glb` placed on the plinth in Lens Studio (import scale ×100 metres→cm gives 37.9 × 25 × 78 cm, base on the plinth top, façade towards the viewer, centre 120 cm ahead); plinth now 60 × 100 cm top, 95 cm high; the primitive temple is deleted. Interior brightness: the interior read about 10% darker than the façade in the preview, so `Assets/Scripts/InteriorLift.ts` (on the `Temple Materials` object) adds a warm emissive term (0.14, 0.11, 0.07) to the interior shell, pillar and statue materials at Lens start, which brings it to parity (measured on preview screenshots). It is a script rather than a material edit because the materials live inside the packed GLB and editor-side edits are not saved. Lens size 6.17 MB of the 25 MB SPECS limit, so textures stay at 2048 px. Preview runs at roughly 35–45 fps on the M3 Pro. Beam-as-glowing-shaft is still open for milestones 4–5.

# Design brief: SUNKEEPER — The Secret of Abu Simbel

<!-- Filled in by plan-lens from the learner's interview. Use the learner's words. Mark any value they didn't choose as (default). -->

One line: Move through space, align the sun, and reveal a 3,000-year-old secret.

Who it's for: curious travellers, students, and museum visitors who want to understand why Abu Simbel is an engineering marvel, not just look at it.

## The one spatial moment
You walk around a tabletop-scale, cut-away model of the Great Temple of Ramesses II sitting on a plinth in front of you. A glowing sun hangs on your side of the temple: the light always comes from where you are standing. You find the one spot where the real sun stands twice a year, low and directly in front of the entrance, and bend down to look along the axis. The sun locks, a beam of light travels through the entrance, along the halls, and into the sanctuary, and three of the four seated gods light up one by one. Ptah stays unlit.

## Why it belongs on glasses
- Uses: draws in the world; leaves your body free. (It does not need to share your view: nothing real is recognised.)
- Why it's better than the phone or laptop version: your body is the controller. You walk around a miniature temple on a real table, and your position sets the sun's angle. Your hands stay free and your eyes stay on the temple. On a phone you'd be pointing a screen; on glasses you simply move. The "aha" is physical: you have to get low and in front of the door, exactly where the sun is at dawn on the alignment days.

## Product or overlay
- Type: product. The virtual temple and its light are the experience.
- What the real version would sense: the real table surface (to place the temple) and the viewer's head position (to drive the sun). The head position is tracked in the preview by the camera, so it needs no stand-in.
- Stand-in for the preview: the preview has no real table, so the temple appears on a **virtual plinth** placed in front of the viewer at start (see sizes below). On SPECS the same plinth would be dropped onto a real table surface; that placement step is not part of this build. The plinth is drawn as a simple museum display stand so it is obvious in the scene.

## Where things live
- Where the user is looking during the main task: down and slightly ahead at the temple, from arm's length to about two metres away. During the alignment they look along the temple's axis from the front, bending to get low. During the revelation they stand back up and look down into the open roof.
- Plinth: a simple block, top surface 95 cm above the floor (default: museum display-case height, so the "low" alignment needs a slight bend, not a crouch), anchored in the room 120 cm in front of the viewer's start position (default), front edge facing the viewer. Top was 70 cm × 50 cm; **changed 27 Oct 2026 to 60 cm wide × 100 cm deep** so the 78 cm temple fits with a margin front and back (the captions and the Try again button keep their front-corner spots).
- Temple model: on the plinth, **78 cm long** from terrace to sanctuary back wall (changed 27 Oct 2026 from about 50 cm so the 2 cm doorway stays readable), 38 cm wide, with the colossi façade 25 cm tall. The façade faces the viewer's start position (this stands for east: the real façade faces the sunrise over the Nile). Model: Mo's own Meshy AI image-to-3D model (`assets_src/temple/…usdz`, generated 27 Oct 2026), cleaned up, axis-checked, optimised (about 60k–100k triangles, 2048 px textures) and exported from Blender via scripts in `tools/blender/`. Warm sandstone look kept; textures must stay light for the additive display. (Changed 27 Oct 2026: this replaces the earlier "stylised low-poly blocks" plan; the primitive build from milestone 3 is superseded.)
- Cut-away: the **roof** is removed along the whole axis and the side walls are lowered to about half height (default), so a standing viewer looking down sees the full interior path: entrance → great hall with eight Osiride pillars (four each side) → smaller second hall with four pillars → vestibule → sanctuary. The façade itself stays intact so the low front view reads as the real temple front. (Learner offered "roof or one side wall"; the roof is chosen because the viewer looks down at a table.)
- Sanctuary: exactly four seated statues on the back wall, each a separate object about 3 cm tall, left to right as seen from the entrance: Ptah, Amun-Ra, Ramesses II (deified), Ra-Horakhty. Each can be lit independently.
- Façade: four seated colossi of Ramesses II; the second from the left is broken, its upper body lying on the ground in front, as it is today. Above the entrance, a niche figure of Ra-Horakhty.
- The sun: a glowing disc about 6 cm across (default) that sits 60 cm from the temple centre, always on the line from the temple towards the viewer's head, at the viewer's elevation angle. The scene's key light comes from the sun's position, so shadows inside the model move as the viewer moves.
- Alignment cues: a faint ring on the **floor** at the spot where the viewer should stand (on the temple's axis, about 100 cm in front of the entrance, radius 25 cm; default) that brightens as the viewer approaches; and a faint light shaft from the entrance towards the sun that grows as the viewer gets lower and closer to the axis.
- Captions: one short strip of light-coloured text, two lines at most, about 30 cm wide, floating 5 cm above the plinth top at the front-left corner of the plinth, turning (yaw only) to face the viewer. Never attached to the viewer's face, never a panel.
- Beam: a visible shaft of warm light about the width of the entrance that travels along the axis from the entrance to the sanctuary. Dust motes inside the shaft if cheap enough (polish, optional).

## Hands and input
- Move the sun: walk and move your head. No hand input. (In the preview: WASD to walk, Q/E to lower and raise the view, mouse to look.)
- Lock the sun: stand inside the alignment tolerance for 1 second (default). Tolerance: within ±7° of the temple axis in azimuth, head elevation between 0° and 25° above the temple's floor plane, 50–150 cm from the entrance (default values, chosen so the spot is achievable in the preview and needs only a slight bend on SPECS).
- Try again: after the narration, one big pinch button, "Try again", about 10 cm × 4 cm (default), appears on the front-right corner of the plinth top, facing the viewer, and resets the experience. Stepping out of the alignment zone for 2 seconds after the sequence ends resets it as well. (The button is plan-lens's addition so the reset can be clicked and tested in the preview; the learner approved it.)
- Targets are big and highlight when aimed at.
- Voice (if any) and the button that does the same job: none.

## When things show
- Temple, plinth and sun: show from the start, always.
- Floor ring: faint from the start; brightens smoothly as the viewer nears the spot; full brightness and a soft chime when locked; fades out while the beam plays; returns on reset.
- Light shaft cue: invisible far from the axis; grows with closeness and lowness; becomes the real beam on lock.
- Captions: hidden until lock. On lock: "Sun locked. Stand up and watch the light travel." Then the narration captions, one sentence at a time, timed to the beam and the statues. After the last line: "Step away, or pinch Try again, to see it again." Hidden on reset.
- Narration audio: starts on lock, together with the captions.
- Beam and statue lights: beam starts 2 seconds after lock (gives the viewer time to stand up), travels the axis over about 8 seconds (default), then lights Amun-Ra, Ramesses II and Ra-Horakhty one by one, about 2 seconds apart (default). Ptah is never lit. Everything fades over about 2 seconds on reset; nothing flashes or snaps.
- If something needs attention out of view: the soft chime on lock, since the viewer is looking at the façade at that moment and the beam plays inside the roof. Nothing else is ever out of view.

## Done criteria
Each one can be checked in Lens Studio's preview.
1. At start, the temple sits on a plinth about 1.2 m in front of the viewer with its roof open. From a standing position you can see the façade with four colossi (the second from the left broken) and, looking down, the whole axis: eight-pillar hall, four-pillar hall, vestibule, and four separate sanctuary statues.
2. Walking around the plinth moves the sun disc to your side of the temple and the shadows inside the model follow it.
3. Standing on the axis in front of the entrance and lowering the view (Q key) brightens the floor ring and the light shaft; after about a second a chime sounds, the sun stops following you, and the caption "Sun locked…" appears.
4. After the lock, a beam travels from the entrance through both halls and the vestibule into the sanctuary, then Amun-Ra, Ramesses II and Ra-Horakhty light up one after another. Ptah stays unlit.
5. Captions tell the story in under 45 seconds, with narration audio if the text-to-speech or a dropped-in voice file is available. Afterwards, stepping away from the spot or pinching "Try again" resets the temple so the alignment can be done again.

## Historical facts the build must respect
- The Great Temple was built by Ramesses II, c. 1264–1244 BCE. Everywhere a date appears (captions, README) use the wording "built c. 1264–1244 BCE". The façade faces east, towards the sunrise over the Nile.
- Façade: four colossal seated statues of Ramesses II; the second from the left is broken, its upper body fallen to the ground. Above the entrance, a niche figure of Ra-Horakhty.
- Interior, on one straight axis from the entrance: great hall with eight Osiride pillars (four each side), smaller second hall with four pillars, vestibule, sanctuary.
- Sanctuary: exactly four seated statues; from the entrance, left to right: Ptah, Amun-Ra, Ramesses II (deified), Ra-Horakhty. Ptah, linked to the underworld, is the one the sun does not reach.
- The alignment happens twice a year, around 22 February and 22 October. Before the temple was relocated (1964–1968) to save it from Lake Nasser, the dates were about a day earlier.

## Narration (captions; under 45 seconds)
> Twice a year, at dawn, the sun reaches deep into this mountain.
> It travels about sixty metres through the halls of Ramesses the Second and lights three of the four gods in the sanctuary: Amun-Ra, Ra-Horakhty, and the deified king himself.
> Only Ptah, god of the underworld, stays in shadow.
> For more than three thousand years the light has kept this appointment, every February and October.
> When engineers moved the whole temple in the 1960s to save it from the rising waters, they kept the alignment. It now arrives just one day later.

Audio: use Lens Studio's text-to-speech if it works in the preview for a SPECS project. If not, captions carry the story, and the project keeps a clearly named audio slot (`Assets/Audio/Narration.mp3`, default name) where the learner drops a recorded voice file.

## Out of scope
- Placing the temple on a real, scanned table surface (SPECS-only; the plinth is fixed in the preview).
- Any menu, floating panel or HUD. The only UI is the caption strip and the "Try again" button.
- Any other interaction: no grabbing or moving the temple, no scrubbing the sun by hand.
- The Small Temple (Nefertari), the surrounding site, the relocation story beyond one sentence.
- Photoreal detail, reliefs, hieroglyphs.

## Risks and open questions
- **Dark is transparent on SPECS.** The learner wants "deep shadow in the sanctuary" and "Ptah stays in darkness". On an additive display, dark areas simply disappear, so the contrast must come from the three lit statues glowing warm and bright while Ptah stays at the plain sandstone level, not from making Ptah or the sanctuary black. The preview simulates this. The brief is written that way and the learner approved this reading of "darkness".
- **Comfort of the low spot.** Finding the alignment needs the viewer's head to get low in front of the entrance. The plinth height (95 cm) and the elevation window (up to 25°) are set so it is a slight bend rather than a crouch, and the sun locks after 1 second so nobody holds the pose. Feel unproven: only real glasses would show whether it is comfortable.
- **The aligned view hides the interior.** From the low front spot the viewer sees the façade, not the open roof, so the beam starts 2 seconds after the lock and a caption tells them to stand up. Logic proven in the preview; the timing (2 s, 8 s travel) may need tuning after a walkthrough.
- **Text-to-speech in the preview.** May not work for a SPECS project or may need internet. Captions are the source of truth; the audio slot is the fallback. The demo must never depend on the audio.
- **Narrow field of view.** A 50 cm model at about 1 m fills most of the SPECS view. The viewer will naturally step back to see all of it; captions sit at the plinth corner so they are in view whenever the temple is.
- **Completion date (resolved).** The learner chose the wording "built c. 1264–1244 BCE" for every place a date appears.
- **Sixty metres (resolved).** The narration says "about sixty metres", the entrance-to-sanctuary depth.

## README notes (for the repo milestone)
The learner asked for a short "Design decisions" section in README.md covering:
- the additive-display lighting (contrast from lit statues, not from darkness);
- the sun lock plus the stand-up pause before the beam;
- the 25° elevation tolerance as a usability trade-off against the real dawn angle;
- the preview-only virtual plinth standing in for a real table.
Dates in the README use "built c. 1264–1244 BCE".

## Build notes for CLAD
- Build for SPECS so it runs and can be demonstrated in Lens Studio's preview. No SPECS device is available.
- Use Spectacles Interaction Kit (SIK) and UI Kit for all interactions, so they work with the mouse in Interactive Preview and with LEAF.
- Build any stand-in exactly as described above, and keep it obvious in the scene.
- Use real-world scale in centimeters. Keep content inside the user's view during the main task.
- The display is additive: black renders as transparent. Don't rely on black or very dark content to be seen; keep text light and readable from where the user stands.
- Get the basic flow working first, then add detail.
- Write LEAF scenarios for each done criterion, run them in preview, and report which pass. Say which criteria have no test.
- Don't record, identify, or follow people.

## After the build: judge it
This part is for you, after CLAD finishes.

1. **Does it work?** Ask your agent which LEAF tests passed and which done criteria have no test.
2. **Walk around it.** Open the preview in Interactive Preview. Use WASD to move, Q and E to go down and up, and right-drag (or hold Shift) to look around. Clicking acts as a pinch. Stand where a user would and look at the task.
3. **Ask the three questions.**
   - Does it use what I'm looking at?
   - Does it put something in my space, where it belongs?
   - Does it free my hands or let me keep my eyes up?
   - Would it be just as good on a phone? If so, what would make it need the glasses?
4. **Check comfort.**
   - Everything I need is in view while I do the task. Nothing sits at the edges, behind me, or stuck to my face.
   - Every control is within reach of someone standing there.
   - Text reads easily from where I stand. No dark UI disappearing.
   - Things show when needed and get out of the way.
5. **Label what you know.** Write "logic proven" next to anything the tests and preview show working, and "feel unproven" next to anything only real glasses could tell you (comfort over time, real hand tracking, real recognition).
6. **Fix with design notes, not code.** Tell your agent what to change in design terms, for example: "Move the step card 15 cm lower and next to the pan. Make the Next button twice as big. Re-run the tests." If a fix takes under a minute, like nudging a panel, do it yourself in the scene.
7. **Submit.** Record a video under 3 minutes of your Lens in the preview, public on YouTube. Make your repo public with your Lens Studio project and this `devpost/` folder. Details are on the hackathon site: https://learn-specs.devpost.com/resources
