# Bug-Hunt Report: shenbi-character-design
**Date**: 2026-06-12
**Skill**: `skills/shenbi-character-design/SKILL.md`
**Test type**: bug-hunt
**Result**: PASS -- all planted defects detected

## Detection Summary
| # | Finding | Severity | Evidence location | Detected |
|---|---------|----------|-------------------|---|
| 1 | 老政委 voice_profile is a clone of protagonist's voice_profile -- modern Chinese internet slang, engineering-student speech patterns impossible for a 55-60 year old illiterate rural blacksmith | error | `characters/major/lao-zhengwei.md` L13-L29 | YES |

## Detection 1: Cloned Voice Profile (Protagonist -> Mentor)
### Defect Location
`tests/rounds/round-003-2026-06-11/novel-output/shenbi-character-design-bughunt/characters/major/lao-zhengwei.md` L13-L29

### Defect Description
The voice_profile section of 老政委 (the mentor) in `lao-zhengwei.md` L13-L29 is a full copy of the protagonist's voice_profile. The speech patterns include characteristics physically impossible for the mentor:

- L15: "习惯用现代中国网络用语和流行文化梗对比异世界现实，产生认知错位的幽默感（'这不就是异世界版网贷吗''这放在地球就是个非法集资'）" -- Requires modern Chinese internet culture knowledge impossible for a native of a fantasy world
- L16: "自言自语时自带理工科吐槽模式，用现代概念解构异世界现象（'所以这个灵能方程本质上是个偏微分方程，他们居然用两百个参数硬拟合'）" -- Requires modern STEM education the illiterate miner never received
- L17: "前期说话带痞气和犬儒，常用反问和调侃消解严肃性；后期语言逐渐沉稳，但始终保留自嘲底色" -- Contradicts personality_tags at L4: "沉稳如山, 洞悉人心, 实事求是, 大智若愚"
- L21: "我他妈就想躺平（前期，逐渐被自己调侃为黑历史）" -- Directly contradicts the mentor's backstory of lifelong dedication to revolutionary cause (L46-L51)
- L23: "路是走出来的（中期开始出现，成为其核心信念的口头表达）" -- This catchphrase belongs to the protagonist's arc of gradual awakening, not to a character who has been organizing underground networks for 40 years
- L26: "不说空洞的大道理和革命口号——这是他从梵光失败中吸取的教训" -- The mentor IS the living embodiment of revolutionary principles; the original character card states "实事求是" is his core value (L5)

### Skill Rule Applied
**铁律三: voice_profile 必填** -- "每个主要角色必须有说话风格指纹（speech_patterns, catchphrases, avoid_patterns）" (SKILL.md L34)

The cloned voice_profile violates this rule at the functional level: a fingerprint copied from another character is not a fingerprint at all. The purpose of 铁律三, as clarified by the Anti-Rationalization table at SKILL.md L85, is to prevent characters from having interchangeable dialogue -- "没有声音指纹的配角说话都一个味" (characters without voice fingerprints all sound the same). A cloned voice_profile produces exactly the failure mode the rule was designed to prevent: two characters who speak identically, making them auditorily interchangeable. The rule requires a "speaking style fingerprint" -- by definition, a fingerprint must be unique to the individual. A copy fails the uniqueness requirement inherent in the concept of a fingerprint.

**Evidence**:
- `lao-zhengwei.md` L13-L29: Complete voice_profile block containing 5 speech_patterns, 4 catchphrases, 4 avoid_patterns -- all identical to protagonist's profile
- `lao-zhengwei.md` L4: `personality_tags: ["沉稳如山", "洞悉人心", "实事求是", "大智若愚", "沧桑而不绝望"]` contradicts speech_patterns at L17 ("带痞气和犬儒") and L21 ("我他妈就想躺平")
- `lao-zhengwei.md` L44-L51: Backstory establishes he grew up illiterate in a mining slum, spent 50 years as an underground revolutionary -- modern internet slang and STEM terminology impossible
- SKILL.md L34: "3. **voice_profile 必填** -- 每个主要角色必须有说话风格指纹（speech_patterns, catchphrases, avoid_patterns）"
- SKILL.md L85: Anti-Rationalization: `"配角不需要 voice_profile"` -> Reality: `"没有声音指纹的配角说话都一个味"` -- establishes that the rule's purpose is preventing interchangeable dialogue, which a cloned profile directly causes

### False Positive Check
Confirmed no clean content incorrectly flagged. Each non-defect field in `lao-zhengwei.md` was individually verified against the character's established background and narrative function:

- `personality_tags` (L4): "沉稳如山, 洞悉人心, 实事求是, 大智若愚, 沧桑而不绝望" -- correctly describes the mentor's grounded, experienced, non-ideological character, consistent with backstory L44-L51
- `core_value` (L5): "脱离实际就是死路一条" -- aligns with the character's three failed uprisings and the lesson he drew from each (L48-L50)
- `goal_surface` (L6): "帮助林烽少走弯路" -- consistent with mentor archetype and narrative function L86-L93
- `goal_deep` (L7): "在有生之年看到人民重新站起来" -- consistent with FLAT arc type (L9) and lifelong dedication shown in backstory
- `fear` (L8): "林烽重蹈梵光的前穿越者覆辙" -- consistent with the character's historical trauma (梵光失败) described in backstory L44-L51
- `arc_type` (L9): FLAT -- correct for a mentor character who serves as a fixed reference point rather than undergoing transformation
- `arc_starting/arc_turning/arc_ending` (L10-L12): All correctly describe the mentor's arc as confirmation/witness/sacrifice, not personal transformation
- Backstory section (L44-L51): Consistent internal logic -- childhood in mining slum, illiterate upbringing, discovery of revolutionary manual, three failed uprisings, 25 years of underground network building
- Personality depth section (L56-L77): Consistent with personality_tags and backstory -- realistic-not-cynical worldview, teacher instinct, suppressed anger, iron-worker surface persona
- Core fear section (L78-L84): Consistent with the character's narrative function as a cautionary witness to revolutionary failure
- Narrative function section (L86-L94): All four functions (thought transmission, arc catalyst, personification of 实事求是, reader emotional anchor) are correctly derived from the character design

Only the `voice_profile` block (L13-L29) is the defect. No other field, section, or content line was incorrectly flagged.
