---
name: shenbi-pov-transition
description: Use when drafting or revising scenes in a multi-POV novel, when deciding which character carries a scene, when considering whether to show internal thoughts of non-POV characters, when planning POV switches at chapter or scene breaks, or when self-auditing a draft for POV consistency violations
---

# POV Transition Management

YOU MUST follow this skill whenever you write or revise any scene in a multi-POV novel. POV discipline is the single most visible craft failure in web novel serialization — head-hopping is the #1 reader complaint, and every violation erodes the trust your human partner has placed in you.

## DOT Flowchart — Authoritative Process

The DOT flowchart below is the authoritative definition of the POV transition process. Narrative text in this skill is supplementary; the DOT is the source of truth. When in doubt, trace the flowchart.

```dot
digraph pov_transition {
    rankdir=TB;
    node [fontname="Helvetica Neue, Arial, sans-serif"];
    edge [fontname="Helvetica Neue, Arial, sans-serif"];

    start [label="Scene drafting begins", shape=box, style=filled, fillcolor="#e8e8e8"];

    // Pre-writing phase
    declare [label="Declare POV character\nfor this scene", shape=box, style=filled, fillcolor="#fff3cd"];
    justify [label="Write 1-line justification:\nWhy THIS character for THIS scene?", shape=box];

    start -> declare;
    declare -> justify;

    // Why-not-other check
    why_check [label="Does this scene truly need\na DIFFERENT POV character\nthan the previous scene?", shape=diamond];
    keep_pov [label="Keep current POV.\nDifferent POV requires a\nspecific narrative reason.", shape=box, style=filled, fillcolor="#d4edda"];

    justify -> why_check;
    why_check -> keep_pov [label="no"];
    keep_pov -> draft;

    // POV establishment
    why_check -> establish [label="yes"];
    establish [label="Establish POV in first 3 paragraphs:\n1. Name or unmistakably signal POV character\n2. Anchor with sensory filter (what THEY perceive)\n3. Set knowledge boundary (what THEY know)", shape=box, style=filled, fillcolor="#cce5ff"];

    establish -> draft;

    // Drafting loop
    draft [label="Draft scene:\n• ONLY POV character's internal thoughts\n• Other characters = external observation only\n• Every sentence: Can my POV perceive this?", shape=box];

    draft -> audit;

    // Self-audit
    audit [label="Self-audit: Red Flag Checklist", shape=diamond, style=filled, fillcolor="#f8d7da"];

    violation [label="POV violation found?", shape=diamond];
    fix_options [label="Fix violation:\n• Rewrite from POV character's observation\n• OR split into two separate scenes\n• OR cut the violating line entirely", shape=box, style=filled, fillcolor="#fff3cd"];

    audit -> violation;
    violation -> fix_options [label="yes"];
    fix_options -> audit [label="re-audit"];
    violation -> done [label="no"];

    done [label="Scene POV-compliant ✓", shape=box, style=filled, fillcolor="#d4edda"];

    // Transition to next scene
    done -> next;
    next [label="Next scene needs\ndifferent POV?", shape=diamond];

    break [label="INSERT scene break marker:\n(***) or (#) or blank-line convention\n— NEVER switch POV without marker", shape=box, style=filled, fillcolor="#cce5ff"];
    reestablish [label="Re-establish new POV:\n1. Sensory anchor in first sentence of new scene\n2. POV character identified immediately\n3. ZERO carryover of previous POV's private knowledge", shape=box, style=filled, fillcolor="#cce5ff"];

    next -> break [label="yes"];
    break -> reestablish;
    reestablish -> establish;

    next -> draft [label="no — continue same POV"];
}
```

## Iron Laws

These rules use absolute language because POV violations have no gray area. Zero exceptions.

### Scene-Level Discipline

- **ONE POV CHARACTER PER SCENE.** A scene MUST NOT contain the internal thoughts, feelings, or private knowledge of more than one character.
- **POV character MUST be established within the first 3 paragraphs of every scene.** If the reader does not know whose eyes they are seeing through by paragraph 4, the scene has already failed.
- **Every sentence MUST pass the perception test:** "Can my POV character perceive, know, or feel this?" If the answer is no, the sentence is a POV violation and MUST be rewritten or deleted.

### POV Switching

- **POV switches MUST occur ONLY at scene breaks or chapter breaks.** A scene break marker (`***`, `#`, or the project's designated separator) MUST physically separate different POV scenes.
- **After EVERY POV switch, you MUST re-establish the new character's sensory filter in the first sentence of the new scene.** A chapter break alone is NEVER sufficient evidence of POV change — the reader ALWAYS needs an explicit sensory re-anchor.
- **NEVER carry over private knowledge from one POV character to another.** If Character A learned a secret, Character B MUST NOT narrate that secret unless Character B learned it through observable means in their own POV scenes.

### Knowledge Boundary

- **Internal thoughts of non-POV characters are NEVER revealed.** Period. What the antagonist is thinking remains invisible unless the antagonist is the POV character.
- **Revealing information the POV character cannot know is ALWAYS a violation.** This includes foreshadowing that only makes sense from another character's perspective, ironic dramatic irony inserted by the narrator, and any form of omniscient aside.
- **The narrator is NEVER omniscient in Shenbi novels.** Limited third-person is the default. If a project explicitly requires omniscient narration, it MUST be configured in genre-config.json before any drafting begins.

### Planning

- **POV character for each scene MUST be declared before drafting that scene begins.** You MUST NOT "discover" POV mid-draft.
- **A scene's POV character choice MUST have a 1-sentence justification.** "Because it feels right" is NEVER a valid justification. The justification MUST reference narrative function: tension, information asymmetry, emotional stakes, or reader knowledge management.

## Anti-Rationalization Table

Agents rationalize POV violations with predictable excuses. This table names each excuse and the reality that blocks it. When you catch yourself thinking one of these thoughts, you are already violating POV discipline.

| Excuse | Reality |
|--------|---------|
| "This scene needs both characters' thoughts to work" | If both characters' internal reactions are essential, you need TWO scenes, not one. Mixed POV within a single scene confuses readers about whose experience they are sharing. Pick ONE POV and convey the other character's state through dialogue, action, and the POV character's observation. |
| "A quick head-hop here won't hurt — it's just one line" | Head-hopping is the #1 reader complaint in multi-POV web novels. Even ONE line of another character's internal thought breaks the reader's immersion and signals amateur craft. The cost of one head-hop is reader distrust that persists for the rest of the novel. |
| "The reader needs to know what the villain is thinking here" | Villain mystery generates more reader engagement than cheap internal exposition. Reveal the villain's state through their actions, their dialogue, their visible reactions — all filtered through the POV character's perception. If the villain's thoughts are truly essential, give the villain their own POV scene. |
| "I'll just switch POV at the chapter break — readers will figure it out" | A chapter break alone does not establish POV. Without an explicit sensory re-anchor in the first sentence of the new chapter, readers spend paragraphs disoriented, re-reading to figure out whose head they are in. Every POV switch requires active re-establishment. |
| "The omniscient narrator can drop this piece of information" | Shenbi novels use limited third-person POV unless genre-config.json explicitly configures omniscient narration. There is no default omniscient narrator. Information the POV character does not possess MUST NOT appear in narration. |
| "This emotional beat won't land unless we see both sides" | If an emotional beat requires dual internal perspective to function, the scene structure is wrong. Write the beat from the POV character's experience and let the other character's emotion emerge through subtext, body language, and the POV character's interpretation. Trust your reader. |
| "I established POV earlier in the chapter, so a brief switch is fine" | POV is per-SCENE, not per-chapter. A chapter containing multiple scenes must maintain one POV per scene. Having established POV in scene 1 does not grant permission to head-hop in scene 2. |
| "The previous POV scene was short, so I don't need a break marker" | Scene break markers are NEVER optional. Every POV switch requires a physical marker. No marker = no switch. |

## Red Flags — Stop and Self-Audit

Before claiming a scene is complete, run this checklist. If ANY item is unchecked, the scene is NOT ready.

- [ ] **POV declared before drafting:** Did I write down the POV character name and a 1-line justification before starting this scene?
- [ ] **First-3-paragraph establishment:** Is the POV character identified (by name or unmistakable signal) within the first 3 paragraphs?
- [ ] **Perception test passed:** Did I check EVERY sentence — especially narration, description, and exposition — against "Can my POV character perceive/know/feel this?"
- [ ] **Zero internal thoughts from non-POV characters:** Did I search the scene for any line revealing what a non-POV character thinks, feels, remembers, or intends?
- [ ] **Zero omniscient knowledge leaks:** Did I search for any information that the POV character cannot know — foreshadowing from other perspectives, narrator asides, dramatic irony inserted by me?
- [ ] **POV switch marked:** If this scene uses a different POV than the previous scene, did I insert the scene break marker?
- [ ] **POV re-anchored after switch:** If this is the first scene after a POV switch, does the first sentence include a sensory anchor from the new POV character's perspective?
- [ ] **No private knowledge carryover:** If this POV character was not present in the previous POV scene, did I ensure ZERO knowledge from that previous scene leaked into this character's narration?
- [ ] **Scene senses are filtered:** Are all sensory details (sights, sounds, smells, textures, temperatures) described through THIS POV character's unique perceptual filter — not a generic narrator's?

## Persuasion Design

This skill uses the following persuasion principles based on Meincke et al. 2025 (N=28,000). Liking and Reciprocity are intentionally excluded.

| Principle | Application in This Skill |
|-----------|---------------------------|
| **Authority** | Iron laws use YOU MUST / NEVER / ALWAYS. DOT flowchart is declared "authoritative" over narrative text. No hedging language anywhere. |
| **Commitment** | Red flag checklist forces explicit self-audit before claiming completion. POV declaration is a written commitment made before drafting. |
| **Scarcity** | "Before drafting begins" — POV declaration has a deadline. "Within the first 3 paragraphs" — time pressure on establishment. "Every sentence" — no sentence escapes the perception test. |
| **Social Proof** | References reader complaints: "head-hopping is the #1 reader complaint in multi-POV web novels." References "your human partner has placed trust in you." |
| **Unity** | "Your human partner" throughout. "Trust your reader" — shared understanding that reader trust is earned. "We" framing for the drafting loop: shared craft standard. |

## Pressure Test Verification

This section documents the pressure test performed during skill design. Three rationalization scenarios were imagined and verified against the skill's defenses.

### Scenario 1: "This fight scene needs both fighters' tactical thoughts"

**Agent rationalization:** A climactic duel between the protagonist and antagonist. The agent wants to alternate internal monologue between the two — protagonist's fear, antagonist's confidence — to heighten tension within a single scene.

**Blocked by:**
- Iron Law "ONE POV CHARACTER PER SCENE" (absolute prohibition)
- Anti-rationalization row "This scene needs both characters' thoughts to work" (direct rebuttal)
- DOT audit step: "Every sentence: Can my POV perceive this?" (opponent's internal thoughts fail the test)
- Red flag: "Zero internal thoughts from non-POV characters" (checklist trap)

**Verdict:** BLOCKED. If both internal perspectives are truly essential, the skill directs the agent to split into two scenes — one from each POV — separated by a scene break marker.

### Scenario 2: "The reader needs to know what the villain is planning"

**Agent rationalization:** A scene where the villain delivers a cryptic line. The agent adds a paragraph of narration: "What the Marquis did not say was that the poison had already been administered — the countdown had begun." This reveals information the POV character (the hero) cannot know.

**Blocked by:**
- Iron Law "Revealing information the POV character cannot know is ALWAYS a violation"
- Iron Law "The narrator is NEVER omniscient in Shenbi novels"
- Anti-rationalization row "The reader needs to know what the villain is thinking here" (direct rebuttal: "Villain mystery > cheap internal exposition")
- DOT audit step: "Every sentence: Can my POV perceive this?" (the hero cannot perceive the poisoning)
- Red flag: "Zero omniscient knowledge leaks" (the dramatic irony aside is a leak)

**Verdict:** BLOCKED. The skill forces the agent to either (a) convey the poisoning information through observable clues the POV character notices, or (b) give the villain their own POV scene.

### Scenario 3: "Chapter 12 is Hero POV, Chapter 13 starts as Villain POV — the chapter break is enough"

**Agent rationalization:** Agent ends Chapter 12 (Hero POV) and begins Chapter 13 (Villain POV) with: "The study was dark. The Count sat at his desk, fingers steepled." No sensory re-anchor, no immediate POV identification, just description that could be from any perspective.

**Blocked by:**
- Iron Law "After EVERY POV switch, you MUST re-establish the new character's sensory filter in the first sentence"
- Iron Law "A chapter break alone is NEVER sufficient evidence of POV change"
- Anti-rationalization row "I'll just switch POV at the chapter break — readers will figure it out" (direct rebuttal: "readers spend paragraphs disoriented")
- DOT transition path: "Insert scene break marker" → "Re-establish new POV" — explicit re-anchor step
- Red flag: "POV re-anchored after switch" (first sentence sensory anchor check)

**Verdict:** BLOCKED. The skill requires the agent to rewrite the Chapter 13 opening with an immediate sensory anchor: "The Count could still smell the boy's fear on his own gloves. He sat at his desk, fingers steepled, replaying the confrontation." The first sentence now passes through the Count's perceptual filter.
