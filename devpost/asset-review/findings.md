# Meshy temple model: inspection findings (step A.2, 27 Oct 2026)

Source: `assets_src/temple/Meshy_AI_abu_simbel_cutaway_ul_1027081830_image-to-3d-texture.usdz` (not committed).
Script: `tools/blender/01_inspect_temple.py` (Blender 5.2.1, headless). Renders in this folder; raw numbers in `measurements.json`, ASCII maps in `maps.txt`.

## Geometry as imported (Blender Z-up: X length, Y depth, Z height)
- One mesh `mesh1`, 515,793 vertices, 960,470 triangles, one material `mat0`.
- Textures came through: base colour 4096², normal 4096², roughness 2048², metallic 2048² (all packed).
- Bounding box 1.904 m (X) × 0.936 m (Y) × 0.617 m (Z). Façade block at −X (X −0.95 to −0.42, full Y width); interior block from X −0.42 to +0.95, only Y −0.47 to −0.05.

## Checks against the brief
| Check | Brief | Model | Verdict |
|---|---|---|---|
| Colossi on façade | 4, second from left broken | 4, second from left broken, upper body on the terrace | OK |
| Niche figure above entrance | Ra-Horakhty | present | OK |
| Entrance position | on the temple axis | centred on façade, Y ≈ 0 | OK on its own |
| Interior centre line | same axis as entrance | Y ≈ −0.26, i.e. 26 cm (14 % of length) to one side | **MISALIGNED** |
| Line of sight doorway → sanctuary | straight | none: rays through the doorway stop 25–45 cm in, inside solid rock behind the façade; the hall's own entrance is hidden behind the façade block | **BLOCKED** |
| First hall | 8 Osiride pillars, 4 each side | 6 round columns in one row plus 6 engaged Osiride figures on the opposite wall | **WRONG COUNT** |
| Second hall | 4 pillars | a square chamber with a frame and one visible column; no clear set of 4 | **UNCLEAR / WRONG** |
| Sanctuary statues | exactly 4 (Ptah, Amun-Ra, Ramesses II, Ra-Horakhty) | **5** seated statues on the back wall | **WRONG COUNT** |
| Roof cut away | yes | yes, interior walls about half height | OK |

Statue separability: the five sanctuary statues are distinct blobs on a continuous bench; a box cut should separate them but leaves open bottoms and needs the bench/wall patched behind the removed one.

## Nothing has been changed yet. Decisions needed before step A.3
1. Axis: move the interior block +0.26 m in Y to centre it on the doorway, then cut a passage through the rock between the doorway (X ≈ −0.50) and the hall front (X ≈ −0.42). Alternative: re-cut the façade opening at Y −0.26 (moves the door off the façade centre, not faithful).
2. Sanctuary: remove one statue and respace the remaining four, or regenerate the model with a corrected prompt.
3. Pillars: accept the 6-column hall as stylisation (brief says wrong pillar counts are not fine), rebuild the halls' interiors from primitives inside the shell, or regenerate.

## Decision (Mo, 27 Oct 2026): hybrid
Keep the Meshy façade block (colossi, broken second colossus, niche figure); delete the Meshy interior block. Bore a passage through the rock behind the entrance on the doorway axis. Build a new interior with `tools/blender/02_build_hybrid_temple.py` on that axis: open roof, half-height walls, great hall with 8 Osiride pillars (two rows of 4, figure silhouette facing the axis), second hall with 4 square pillars, vestibule, sanctuary with exactly 4 seated statues as separate objects (`Statue_Ptah`, `Statue_AmunRa`, `Statue_Ramesses`, `Statue_RaHorakhty`, left to right from the entrance, each with its own material). Interior depth about 2–2.5× the façade height. Interior colour sampled from the façade base-colour texture with subtle noise, kept light for the additive display. Line of sight from the doorway to the three lit statues verified by ray cast and drawn on a top-down render. Then decimate (60–100k triangles total), textures ≤ 2048, scale to ~55 cm, origin at base centre, export GLB to `Assets/Temple/`.

## Hybrid build results (step A.3-5, `02_build_hybrid_temple.py`)
- Doorway measured by ray scan: 5.2 cm wide, 12.0 cm tall, centre Y -0.002 m, façade wall at X -0.572 m, recess back at X -0.497 m (model units, metres).
- Meshy interior block removed behind X -0.429 m; façade now 459,266 triangles. Passage bored through the rock and lined (faces removed: 821).
- Façade base-colour texture: mean sRGB (0.751, 0.533, 0.286), mean luminance 0.561; interior texture = that mean with ±9 % fractal noise. Metallic map is flat (mean 0.0, std 0.001) and will be dropped at export.
- New interior on the doorway axis: great hall with 8 Osiride pillars (2 × 4, figure silhouettes facing the axis), doorway, second hall with 4 square pillars, doorway, vestibule, doorway, sanctuary with 4 separate seated statues, back wall. Interior depth 1.40 m = 2.3 × façade height; walls 0.30 m above the sill (about half the façade).
- Statues left to right from the entrance (+Y to −Y in Blender): Statue_Ptah, Statue_AmunRa, Statue_Ramesses, Statue_RaHorakhty, each with its own material.
- Line of sight from the doorway centre (ray cast): Statue_Ptah clear, Statue_AmunRa clear, Statue_Ramesses clear, Statue_RaHorakhty clear; axis ray stops at the back wall (X 0.914). Drawn on `hybrid_top_beam_path.jpg`.
- Triangles: Facade 459,266, Interior_Pillars 432, Interior_Shell 180, Statue_AmunRa 60, Statue_Ptah 60, Statue_RaHorakhty 60, Statue_Ramesses 60. Model size 1.93 × 0.94 × 0.62 m before scaling.
- Renders: hybrid_front, hybrid_top, hybrid_three_quarter(_other_side), hybrid_interior_closeup, hybrid_sanctuary_closeup, hybrid_top_beam_path, hybrid_beam_three_quarter.
- Not yet done: decimation, texture resize, scaling to 55 cm, GLB export (step A.6).
