/**
 * SunNarration — milestone 6: the story, the Try again button and the reset.
 *
 * On SunReveal's completion the narration plays as short caption phrases on a small warm
 * strip near the sanctuary end of the plinth (yaw-facing the viewer), timed to a reading
 * pace or, when a voice file is assigned, stretched to the audio's length. Lens Studio's
 * built-in text-to-speech is deprecated in 5.24 ("VoiceML capabilities are no longer
 * supported"), so the voice is a recorded file: drop it into Assets/Audio/Narration.mp3 and
 * assign it to the "Narration Audio" input.
 *
 * After the last phrase the closing caption and the Try again button (a UI Kit pinch button
 * on the plinth's front-right corner) appear. Pinching it, or standing more than
 * `stepAwayDistance` from the plinth for `stepAwayHoldSec`, resets: statues, beam, halos and
 * pools fade out over RESET_FADE_SEC, the sun follows the viewer again, the cues re-arm and
 * the captions and button hide. Prints: NARRATION_START, NARRATION_END, RESET (<cause>),
 * RESET_COMPLETE, each with the time since lock.
 */

import { SunAlignment } from './SunAlignment';
import { SunReveal } from './SunReveal';
import { ViewingSpot } from './ViewingSpot';
import { RectangleButton } from 'SpectaclesUIKit.lspkg/Scripts/Components/Button/RectangleButton';

/** Reading pace used to time the captions when there is no voice file. */
const WORDS_PER_SEC = 2.6;
/** Pause added after each phrase (s). */
const PHRASE_GAP_SEC = 0.3;
/** How long the last story phrase stays before the closing caption (s). */
const LAST_PHRASE_HOLD_SEC = 1.0;
/** Fade time of the reset (s). */
const RESET_FADE_SEC = 2.0;

const CLOSING_CAPTION = 'Step away, or pinch Try again, to see it again.';

/** The narration, as short caption phrases. Facts as approved in devpost/design-brief.md. */
const PHRASES: string[] = [
  'Twice a year, at dawn,',
  'the sun reaches deep into this mountain.',
  'It travels about sixty metres',
  'through the halls of Ramesses the Second,',
  'and lights three of the four statues in the sanctuary:',
  'Amun-Ra, Ra-Horakhty, and the deified king himself.',
  'Only Ptah, associated with the underworld, stays in shadow.',
  'For over three thousand years',
  'the light has kept this appointment,',
  'every February and October.',
  'When engineers moved the whole temple in the 1960s',
  'to save it from rising waters,',
  'they kept the alignment.',
  'It now arrives about a day later.',
];

type Phase = 'idle' | 'narrating' | 'closing' | 'resetting';

@component
export class SunNarration extends BaseScriptComponent {
  @input alignment: SunAlignment;
  @input reveal: SunReveal;
  @input
  @allowUndefined
  viewingSpot: ViewingSpot;

  /** The Camera Object: its world position is the viewer's head. */
  @input camera: SceneObject;

  /** The narration caption object (Component.Text on it), near the sanctuary end of the plinth. */
  @input caption: SceneObject;

  /** Plays the voice file. Optional. */
  @input('Component.AudioComponent')
  @allowUndefined
  audio: AudioComponent;

  /** NARRATION AUDIO SLOT: drop your recorded voice into Assets/Audio/Narration.mp3 and assign it here. */
  @input('Asset.AudioTrackAsset')
  @allowUndefined
  narrationAudio: AudioTrackAsset;

  /**
   * Optional: when a voice file is assigned, the second (from the start of the file) at which each
   * phrase begins, comma-separated, one per phrase. Measured from the recording's pauses. Leave
   * empty to spread the phrases over the file's length by word count instead.
   */
  @input
  voiceCueTimes: string = '';

  /** The UI Kit "Try again" button on the plinth's front-right corner. */
  @input tryAgain: RectangleButton;

  /** Reset when the head is further than this from the plinth centre (cm, horizontal)... */
  @input
  stepAwayDistance: number = 150;
  /** ...for this long (s). Only armed after the narration. */
  @input
  stepAwayHoldSec: number = 2.0;

  @input
  debugLog: boolean = false;

  private phase: Phase = 'idle';
  private captionText: Text | null = null;
  private buttonLabel: Text | null = null;
  private buttonRoot: SceneObject | null = null;
  private lockTime = 0;
  private t = 0;
  private phraseIndex = -1;
  private phraseEnds: number[] = [];
  private awayTimer = 0;
  private fadeTimer = 0;
  private buttonPending = false;

  onAwake() {
    this.createEvent('OnStartEvent').bind(() => this.start());
    this.createEvent('UpdateEvent').bind(() => this.update());
  }

  private start() {
    if (!this.alignment || !this.reveal || !this.camera || !this.caption) {
      print('SunNarration: alignment, reveal, camera and caption must be assigned');
      return;
    }
    this.captionText = this.caption.getComponent('Component.Text') as Text | null;
    this.caption.enabled = false;
    if (this.tryAgain) {
      this.buttonRoot = this.tryAgain.getSceneObject();
      this.buttonLabel = this.findText(this.buttonRoot);
      if (this.buttonLabel) this.buttonLabel.text = 'Try again';
      // Stay enabled for the first frame so the UI Kit button runs its own start (it builds its
      // Interactable and collider there); hidden in update(). Disabled before that, it would only
      // initialise when first shown and ignore pinches for its first few seconds.
      this.buttonPending = true;
      this.tryAgain.onTriggerUp.add(() => this.onTryAgain());
    } else {
      print('SunNarration: no Try again button assigned');
    }
    if (this.audio && this.narrationAudio) this.audio.audioTrack = this.narrationAudio;
    this.alignment.onAligned(() => {
      this.lockTime = getTime();
    });
    this.reveal.onRevealComplete(() => this.beginNarration());
  }

  // --- narration ---

  private beginNarration() {
    if (this.phase !== 'idle') return;
    this.phase = 'narrating';
    this.t = 0;
    this.phraseIndex = -1;
    // Timeline: measured voice cues, else reading pace stretched to the voice file's length, else reading pace.
    const voice = this.audio && this.narrationAudio ? this.audio.duration : 0;
    const cues = this.parseCues();
    let mode = 'reading pace';
    this.phraseEnds = [];
    if (voice > 1 && cues.length === PHRASES.length) {
      // Each phrase ends where the next begins; the last one ends with the file.
      for (let i = 0; i < PHRASES.length; i++) this.phraseEnds.push(i + 1 < cues.length ? cues[i + 1] : voice);
      mode = 'timed to the voice cues';
    } else {
      const durations = PHRASES.map((p) => p.split(' ').length / WORDS_PER_SEC + PHRASE_GAP_SEC);
      const base = durations.reduce((a, b) => a + b, 0);
      const scale = voice > 1 ? voice / base : 1;
      let acc = 0;
      for (const d of durations) {
        acc += d * scale;
        this.phraseEnds.push(acc);
      }
      if (voice > 1) mode = 'stretched to the voice file';
    }
    const total = this.phraseEnds[this.phraseEnds.length - 1];
    this.playVoice();
    this.caption.enabled = true;
    print('NARRATION_START +' + this.sinceLock() + ' s after lock, ' + PHRASES.length + ' phrases over ' + total.toFixed(1) + ' s (' + mode + (voice > 1 ? ', voice file ' + voice.toFixed(1) + ' s' : '') + ')');
  }

  private update() {
    if (this.buttonPending && this.buttonRoot) {
      this.buttonPending = false;
      if (this.phase !== 'closing') this.buttonRoot.enabled = false;
    }
    if (this.phase === 'idle') return;
    const dt = getDeltaTime();
    const head = this.camera.getTransform().getWorldPosition();

    if (this.phase === 'narrating') {
      this.t += dt;
      let i = 0;
      while (i < this.phraseEnds.length && this.t >= this.phraseEnds[i]) i++;
      if (i >= PHRASES.length) {
        if (this.t >= this.phraseEnds[PHRASES.length - 1] + LAST_PHRASE_HOLD_SEC) this.closeNarration();
      } else if (i !== this.phraseIndex) {
        this.phraseIndex = i;
        if (this.captionText) this.captionText.text = PHRASES[i];
        if (this.debugLog) print('SunNarration: phrase ' + (i + 1) + ' at +' + this.sinceLock() + ' s: ' + PHRASES[i]);
      }
    }

    if (this.phase === 'closing') {
      // Armed: stepping well away from the plinth resets.
      const plinth = this.alignment.temple.getTransform().getWorldPosition();
      const dx = head.x - plinth.x;
      const dz = head.z - plinth.z;
      const away = Math.sqrt(dx * dx + dz * dz) > this.stepAwayDistance;
      this.awayTimer = away ? this.awayTimer + dt : 0;
      if (this.awayTimer >= this.stepAwayHoldSec) this.resetAll('stepped away');
    }

    if (this.phase === 'resetting') {
      this.fadeTimer -= dt;
      if (this.fadeTimer <= 0) {
        this.phase = 'idle';
        print('RESET_COMPLETE +' + this.sinceLock() + ' s after lock');
      }
    }

    if (this.caption.enabled) this.faceViewer(this.caption, head);
    if (this.buttonRoot && this.buttonRoot.enabled) this.faceViewer(this.buttonRoot, head);
  }

  private closeNarration() {
    this.phase = 'closing';
    this.awayTimer = 0;
    if (this.captionText) this.captionText.text = CLOSING_CAPTION;
    if (this.buttonRoot) this.buttonRoot.enabled = true;
    print('NARRATION_END +' + this.sinceLock() + ' s after lock; Try again shown');
  }

  // --- reset ---

  private onTryAgain() {
    if (this.phase === 'closing') this.resetAll('Try again pinched');
  }

  /** Back to the start state with a fade (also callable from other scripts). */
  resetAll(cause: string) {
    if (this.phase === 'resetting') return;
    print('RESET (' + cause + ') +' + this.sinceLock() + ' s after lock');
    this.phase = 'resetting';
    this.fadeTimer = RESET_FADE_SEC;
    this.caption.enabled = false;
    if (this.buttonRoot) this.buttonRoot.enabled = false;
    this.stopVoice();
    this.reveal.fadeOut(RESET_FADE_SEC);
    this.alignment.reset();
    if (this.viewingSpot) this.viewingSpot.reset();
  }

  // --- helpers ---

  private parseCues(): number[] {
    const out: number[] = [];
    for (const part of this.voiceCueTimes.split(',')) {
      const v = parseFloat(part.trim());
      if (!isNaN(v)) out.push(v);
    }
    return out;
  }

  /** The voice file is optional: without one the AudioComponent has no player and throws. */
  private playVoice() {
    if (!this.audio || !this.narrationAudio) return;
    try {
      this.audio.play(1);
    } catch (e) {
      print('SunNarration: could not play the voice file: ' + e);
    }
  }

  private stopVoice() {
    if (!this.audio || !this.narrationAudio) return;
    try {
      if (this.audio.isPlaying()) this.audio.stop(false);
    } catch (e) {
      print('SunNarration: could not stop the voice file: ' + e);
    }
  }

  private sinceLock(): string {
    return (getTime() - this.lockTime).toFixed(2);
  }

  private faceViewer(obj: SceneObject, head: vec3) {
    const t = obj.getTransform();
    const d = head.sub(t.getWorldPosition());
    const yaw = Math.atan2(d.x, d.z);
    t.setWorldRotation(quat.angleAxis(yaw, vec3.up()));
  }

  private findText(obj: SceneObject | null): Text | null {
    if (!obj) return null;
    const t = obj.getComponent('Component.Text') as Text | null;
    if (t) return t;
    const n = obj.getChildrenCount();
    for (let i = 0; i < n; i++) {
      const c = this.findText(obj.getChild(i));
      if (c) return c;
    }
    return null;
  }
}
