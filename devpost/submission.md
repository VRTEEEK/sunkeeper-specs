# Sunkeeper — The Secret of Abu Simbel (Devpost draft, under 400 words)

## What it does
Sunkeeper puts a cut-away model of the Great Temple of Ramesses II (built c. 1264–1244 BCE) on a plinth in front of you. A glowing sun hangs on your side of the temple and follows you as you walk. Twice a year the real dawn sun stands low and straight in front of the entrance; find that spot with your own body, get a little lower, and the sun locks. Light enters the doorway, travels the halls to the sanctuary, and three of the four seated gods ease up to gold: Ra-Horakhty, Ramesses, Amun-Ra. Ptah, god of the underworld, stays in shadow. Fourteen short captions tell the story, then "Try again" or a step back resets it.

## Who it is for
Curious travellers, students and museum visitors who want to understand why Abu Simbel is an engineering marvel rather than just look at it. The alignment is learned by finding it.

## How it was built
Planned with the Devpost Learn skill pack: the plan-lens interview became a design brief with the one spatial moment, done criteria and the historical facts to respect. Snap's CLAD agent built the Lens in Lens Studio 5.24 through its MCP tools, in eight signed-off milestones. The façade is a Meshy AI image-to-3D model; its interior was off the axis with five statues and six columns, so Blender scripts rebuilt the interior on the doorway axis with eight Osiride pillars, four pillars and exactly four statues. All behaviour is TypeScript with the Spectacles Interaction Kit.

## Challenges
An additive display cannot show darkness, so "Ptah stays dark" became "the other three glow". The low aligned spot hides the open roof, so the beam waits two seconds and a second floor ring leads you to the side; the walls were lowered to a third of the façade so the payoff is visible standing up. Lens Studio no longer offers text-to-speech, so the narration is a recording generated with ElevenLabs, with each caption cued to the pauses in it.

## What I learned
- **Design for the body, not the screen.** The interaction is where you stand, and the best place to trigger the moment isn't the best place to watch it, so the Lens asks you to move twice.
- **On SPECS, dark is invisible.** The display adds light, so Ptah's "shadow" had to come from contrast: three statues turning gold against plain stone.
- **AI makes things look right, not be right.** The AI temple had five statues and a doorway into solid rock. We kept the façade and rebuilt the interior with exact, scripted geometry.
- **The agent builds, I decide.** The coding agent wrote almost everything; my job was the judgement calls on what to cut, what had to be historically exact, and when to stop and fix.

## What's next
Run it on SPECS: drop the plinth onto a real table, tune the elevation window and the walk timing with real bodies, record the voice, add the lock chime, and try a second temple with its own alignment.
