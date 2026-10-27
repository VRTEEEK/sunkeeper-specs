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
