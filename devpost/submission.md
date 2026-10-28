# Sunkeeper — The Secret of Abu Simbel (Devpost draft, under 400 words)

## What it does
Sunkeeper puts a cut-away model of the Great Temple of Ramesses II (built c. 1264–1244 BCE) on a plinth in front of you. A glowing sun hangs on your side of the temple and follows you as you walk. Twice a year the real dawn sun stands low and straight in front of the entrance; find that spot with your own body, get a little lower, and the sun locks. Light enters the doorway, travels the halls to the sanctuary, and three of the four seated gods ease up to gold: Ra-Horakhty, Ramesses, Amun-Ra. Ptah, god of the underworld, stays in shadow. Fourteen short captions tell the story, then "Try again" or a step back resets it.

## Who it is for
Curious travellers, students and museum visitors who want to understand why Abu Simbel is an engineering marvel rather than just look at it. The alignment is learned by finding it.

## How it was built
Planned with the Devpost Learn skill pack: the plan-lens interview became a design brief with the one spatial moment, done criteria and the historical facts to respect. Snap's CLAD agent built the Lens in Lens Studio 5.24 through its MCP tools, in eight signed-off milestones. The façade is a Meshy AI image-to-3D model; its interior was off the axis with five statues and six columns, so Blender scripts rebuilt the interior on the doorway axis with eight Osiride pillars, four pillars and exactly four statues. All behaviour is TypeScript with the Spectacles Interaction Kit.

## Challenges
An additive display cannot show darkness, so "Ptah stays dark" became "the other three glow". The low aligned spot hides the open roof, so the beam waits two seconds and a second floor ring leads you to the side; the walls were lowered to a third of the façade so the payoff is visible standing up. Lens Studio no longer offers text-to-speech, so the narration is my own recording, with each caption cued to the pauses in it.

## What I learned
`[Mo's words: the additive display, trusting then checking AI models, brief versus build, what you'd test first on real glasses]`

## What's next
Run it on SPECS: drop the plinth onto a real table, tune the elevation window and the walk timing with real bodies, record the voice, add the lock chime, and try a second temple with its own alignment.
