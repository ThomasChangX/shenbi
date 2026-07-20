#!/usr/bin/env python3
"""Comprehensive redundancy and duplication audit for xinghuo-ranqiong novel output."""

import difflib
import json
import os
import re
from collections import defaultdict

BASE = "/Users/xiaotiac/Documents/GitHub/shenbi/novel-output/xinghuo-ranqiong"
CHAPTERS_DIR = os.path.join(BASE, "chapters")
AUDITS_DIR = os.path.join(BASE, "audits")
PLANS_DIR = os.path.join(BASE, "plans")
STAGING_PLANS_DIR = os.path.join(BASE, "staging/plans")
STAGING_TRUTH_DIR = os.path.join(BASE, "staging/truth")
TRUTH_DIR = os.path.join(BASE, "truth")
SNAPSHOTS_DIR = os.path.join(BASE, "snapshots")


def extract_prose(filepath):
    """Extract prose content after META-END from chapter files."""
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        # Find the last META-END marker and take everything after
        idx = content.rfind("<!--META-END-->")
        if idx == -1:
            idx = content.rfind("META-END")
        if idx != -1:
            # Find end of the marker
            end_marker = content.find("\n", idx)
            if end_marker != -1:
                return content[end_marker:].strip()
        return content.strip()
    except Exception:
        return ""


def similarity_ratio(text1, text2):
    """Compute similarity using difflib SequenceMatcher."""
    if not text1 or not text2:
        return 0.0
    return difflib.SequenceMatcher(None, text1, text2).ratio()


def extract_opening(text, chars=200):
    """Extract first 'chars' characters from prose."""
    return text[:chars] if text else ""


def extract_ending(text, chars=200):
    """Extract last 'chars' characters from prose."""
    return text[-chars:] if text else ""


# ============================================================
# SECTION 1: DUPLICATE CHAPTER CONTENT
# ============================================================
print("=" * 80)
print("SECTION 1: DUPLICATE CHAPTER CONTENT ANALYSIS")
print("=" * 80)

chapter_files = sorted(
    [f for f in os.listdir(CHAPTERS_DIR) if re.match(r"chapter-\d+\.md$", f)],
    key=lambda x: int(re.search(r"chapter-(\d+)\.md", x).group(1)),
)

chapter_prose = {}
chapter_openings = {}
chapter_endings = {}

for cf in chapter_files:
    ch_num = int(re.search(r"chapter-(\d+)\.md", cf).group(1))
    fpath = os.path.join(CHAPTERS_DIR, cf)
    prose = extract_prose(fpath)
    chapter_prose[ch_num] = prose
    chapter_openings[ch_num] = extract_opening(prose)
    chapter_endings[ch_num] = extract_ending(prose)

# 1a. Adjacent chapter pairs
print("\n--- 1a. Adjacent Chapter Pairs (>30% similarity) ---")
adj_high = []
for i in range(1, max(chapter_prose.keys())):
    if i in chapter_prose and (i + 1) in chapter_prose:
        sim = similarity_ratio(chapter_prose[i], chapter_prose[i + 1])
        if sim > 0.30:
            adj_high.append((i, i + 1, sim))
            print(f"  Chapters {i}-{i + 1}: {sim:.1%} similarity -- HIGH")
if not adj_high:
    print("  No adjacent pairs exceed 30% similarity.")

# Top 10 most similar adjacent pairs
print("\n--- Top 10 Most Similar Adjacent Pairs ---")
adj_all = []
for i in range(1, max(chapter_prose.keys())):
    if i in chapter_prose and (i + 1) in chapter_prose:
        sim = similarity_ratio(chapter_prose[i], chapter_prose[i + 1])
        adj_all.append((i, i + 1, sim))
adj_all.sort(key=lambda x: -x[2])
for pair in adj_all[:10]:
    print(f"  Chapters {pair[0]}-{pair[1]}: {pair[2]:.1%} similarity")

# 1b. Non-adjacent pairs (>40% similarity) - sample approach
print("\n--- 1b. Non-adjacent Near-Duplicates (>40% similarity, non-adjacent) ---")
non_adj_high = []
ch_nums = sorted(chapter_prose.keys())
# Check all pairs to be thorough
for i in range(len(ch_nums)):
    for j in range(i + 2, len(ch_nums)):  # Non-adjacent only
        sim = similarity_ratio(chapter_prose[ch_nums[i]], chapter_prose[ch_nums[j]])
        if sim > 0.40:
            non_adj_high.append((ch_nums[i], ch_nums[j], sim))
            print(f"  Chapters {ch_nums[i]}-{ch_nums[j]}: {sim:.1%} similarity -- HIGH")

if not non_adj_high:
    print("  No non-adjacent pairs exceed 40% similarity.")

# 1c. Opening repetition
print("\n--- 1c. Chapter Opening Overlap (>50% similarity) ---")
opening_pairs = []
for i in range(1, max(chapter_openings.keys()) + 1):
    for j in range(i + 1, max(chapter_openings.keys()) + 1):
        if i in chapter_openings and j in chapter_openings:
            sim = similarity_ratio(chapter_openings[i], chapter_openings[j])
            if sim > 0.50:
                opening_pairs.append((i, j, sim))
                print(f"  Chapters {i}-{j}: opening {sim:.1%} similar")
if not opening_pairs:
    print("  No chapters have >50% similar openings.")

# 1d. Ending repetition
print("\n--- 1d. Chapter Ending Overlap (>50% similarity) ---")
ending_pairs = []
for i in range(1, max(chapter_endings.keys()) + 1):
    for j in range(i + 1, max(chapter_endings.keys()) + 1):
        if i in chapter_endings and j in chapter_endings:
            sim = similarity_ratio(chapter_endings[i], chapter_endings[j])
            if sim > 0.50:
                ending_pairs.append((i, j, sim))
                print(f"  Chapters {i}-{j}: ending {sim:.1%} similar")
if not ending_pairs:
    print("  No chapters have >50% similar endings.")

# ============================================================
# SECTION 2: AUDIT FILE REDUNDANCY
# ============================================================
print("\n" + "=" * 80)
print("SECTION 2: AUDIT FILE REDUNDANCY")
print("=" * 80)

audit_files = sorted(os.listdir(AUDITS_DIR))
audit_types = set()
audit_by_type = defaultdict(list)

for af in audit_files:
    m = re.match(r"chapter-(\d+)-(.+)\.md", af)
    if m:
        ch = int(m.group(1))
        atype = m.group(2)
        audit_types.add(atype)
        audit_by_type[atype].append((ch, os.path.join(AUDITS_DIR, af)))

print(f"Total audit files: {len(audit_files)}")
print(f"Audit types: {sorted(audit_types)}")

# 2a. Within each audit type, find near-identical files
print("\n--- 2a. Near-identical Audits Within Same Type (>90% similarity) ---")
for atype in sorted(audit_types):
    files = audit_by_type[atype]
    if len(files) < 2:
        continue

    pairwise = []
    for i in range(len(files)):
        for j in range(i + 1, len(files)):
            try:
                with open(files[i][1]) as f:
                    t1 = f.read()
                with open(files[j][1]) as f:
                    t2 = f.read()
                sim = similarity_ratio(t1, t2)
                if sim > 0.90:
                    pairwise.append((files[i][0], files[j][0], sim))
            except:
                pass

    if pairwise:
        # Report number of highly similar pairs
        print(f"  [{atype}]: {len(pairwise)} near-identical pairs found (>{90}%)")
        for p in pairwise[:5]:
            print(f"    Chapters {p[0]}-{p[1]}: {p[2]:.1%}")
        if len(pairwise) > 5:
            print(f"    ... and {len(pairwise) - 5} more")
    else:
        print(f"  [{atype}]: No near-identical pairs")

# 2b. Count unique vs templated content
print("\n--- 2b. Unique vs Templated Audit Content ---")
for atype in sorted(audit_types):
    files = audit_by_type[atype]
    if len(files) < 2:
        continue

    # Compare each audit to the first one as a baseline
    first_content = None
    try:
        with open(files[0][1]) as f:
            first_content = f.read()
    except:
        continue

    similarities = []
    for i in range(1, len(files)):
        try:
            with open(files[i][1]) as f:
                c = f.read()
            sim = similarity_ratio(first_content, c)
            similarities.append(sim)
        except:
            pass

    if similarities:
        avg_sim = sum(similarities) / len(similarities)
        if avg_sim > 0.70:
            print(
                f"  [{atype}]: HIGHLY TEMPLATED - avg similarity to first: {avg_sim:.1%} ({len(files)} files)"
            )
        elif avg_sim > 0.40:
            print(
                f"  [{atype}]: Somewhat templated - avg similarity to first: {avg_sim:.1%} ({len(files)} files)"
            )
        else:
            print(
                f"  [{atype}]: Mostly unique - avg similarity to first: {avg_sim:.1%} ({len(files)} files)"
            )

# 2c. Empty/placeholder audit files
print("\n--- 2c. Empty/Placeholder Audit Files (<100 meaningful chars) ---")
empty_audits = []
for af in audit_files:
    fpath = os.path.join(AUDITS_DIR, af)
    try:
        with open(fpath) as f:
            content = f.read()
        # Strip whitespace, markdown headers, boilerplate
        stripped = re.sub(r"^#.*$", "", content, flags=re.MULTILINE)
        stripped = re.sub(r"^##.*$", "", stripped, flags=re.MULTILINE)
        stripped = re.sub(r"^---.*$", "", stripped, flags=re.MULTILINE)
        stripped = re.sub(r"\*{1,3}", "", stripped)
        stripped = re.sub(r"\|.*\|", "", stripped)
        stripped = re.sub(r"[-\s]", "", stripped)
        if len(stripped) < 100:
            empty_audits.append(af)
    except:
        pass

if empty_audits:
    print(f"  Found {len(empty_audits)} effectively empty/placeholder audit files:")
    for ea in sorted(empty_audits):
        print(f"    {ea}")
else:
    print("  No effectively empty audit files found.")

# ============================================================
# SECTION 3: PLAN REDUNDANCY
# ============================================================
print("\n" + "=" * 80)
print("SECTION 3: PLAN REDUNDANCY")
print("=" * 80)

plan_files = sorted(
    [f for f in os.listdir(PLANS_DIR) if re.match(r"chapter-\d+-plan\.md$", f)],
    key=lambda x: int(re.search(r"chapter-(\d+)-plan\.md", x).group(1)),
)

plan_contents = {}
for pf in plan_files:
    ch_num = int(re.search(r"chapter-(\d+)-plan\.md", pf).group(1))
    fpath = os.path.join(PLANS_DIR, pf)
    try:
        with open(fpath) as f:
            plan_contents[ch_num] = f.read()
    except:
        pass

# 3a. Consecutive plan similarity
print("\n--- 3a. Consecutive Chapter Plan Similarity ---")
consec_high = []
for i in range(1, max(plan_contents.keys())):
    if i in plan_contents and (i + 1) in plan_contents:
        sim = similarity_ratio(plan_contents[i], plan_contents[i + 1])
        if sim > 0.50:
            consec_high.append((i, i + 1, sim))
            print(f"  Plans {i}-{i + 1}: {sim:.1%} similarity -- HIGH")
if not consec_high:
    print("  No consecutive plans exceed 50% similarity.")

# Top 10 most similar consecutive plans
print("\n--- Top 10 Most Similar Consecutive Plans ---")
consec_all = []
for i in range(1, max(plan_contents.keys())):
    if i in plan_contents and (i + 1) in plan_contents:
        sim = similarity_ratio(plan_contents[i], plan_contents[i + 1])
        consec_all.append((i, i + 1, sim))
consec_all.sort(key=lambda x: -x[2])
for pair in consec_all[:10]:
    print(f"  Plans {pair[0]}-{pair[1]}: {pair[2]:.1%} similarity")

# 3b. Core task repetition across plans
print("\n--- 3b. Core Task Repetition Across Plans ---")
# Extract "核心任务" or similar task lines
task_pattern = re.compile(r"(?:核心任务|本章任务|core.?task)[：:]\s*(.+)", re.IGNORECASE)
chapter_tasks = {}
for ch_num, content in plan_contents.items():
    tasks = task_pattern.findall(content)
    if tasks:
        chapter_tasks[ch_num] = tasks

# Check for exact duplicate tasks across chapters
task_to_chapters = defaultdict(list)
for ch_num, tasks in chapter_tasks.items():
    for t in tasks:
        # Normalize a bit
        normalized = re.sub(r"\s+", "", t)
        task_to_chapters[normalized].append(ch_num)

repeated = {k: v for k, v in task_to_chapters.items() if len(v) > 1}
if repeated:
    print(f"  Found {len(repeated)} tasks repeated across multiple chapters:")
    for task, chs in list(repeated.items())[:10]:
        print(f"    Task: '{task[:80]}...' in chapters {chs}")
else:
    print("  No exact task repetitions found.")

# Also do fuzzy matching
print("\n--- 3c. Plans with Minimal Changes from Previous ---")
for i in range(1, max(plan_contents.keys())):
    if i in plan_contents and (i + 1) in plan_contents:
        sim = similarity_ratio(plan_contents[i], plan_contents[i + 1])
        if sim > 0.70:
            print(
                f"  Plan {i + 1} is essentially a copy of Plan {i} ({sim:.1%} similar) -- POTENTIAL COPY-PASTE"
            )

# ============================================================
# SECTION 4: STAGING VS FINAL FILE COMPARISON
# ============================================================
print("\n" + "=" * 80)
print("SECTION 4: STAGING VS FINAL FILE COMPARISON")
print("=" * 80)

# 4a. Staging plans vs final plans (random 10)
print("\n--- 4a. Staging Plans vs Final Plans (10 random chapters) ---")
import random

random.seed(42)

# Get chapters that have both staging and final plans
staging_plan_files = {}
for f in os.listdir(STAGING_PLANS_DIR):
    m = re.match(r"chapter-(\d+)-plan\.md$", f)
    if m:
        staging_plan_files[int(m.group(1))] = os.path.join(STAGING_PLANS_DIR, f)

# Remove chapter 35 and 54 which don't appear in plans dir but do in staging
common_plan_chapters = sorted(set(staging_plan_files.keys()) & set(plan_contents.keys()))
sample_chapters = random.sample(common_plan_chapters, min(10, len(common_plan_chapters)))

for ch in sorted(sample_chapters):
    try:
        with open(staging_plan_files[ch]) as f:
            staging_content = f.read()
        final_content = plan_contents[ch]
        sim = similarity_ratio(staging_content, final_content)
        flag = " *** MATCH" if sim > 0.95 else (" *** VERY SIMILAR" if sim > 0.85 else "")
        print(f"  Chapter {ch}: staging vs final plan similarity: {sim:.1%}{flag}")
    except Exception as e:
        print(f"  Chapter {ch}: ERROR - {e}")

# 4b. Staging truth vs final truth
print("\n--- 4b. Staging Truth vs Final Truth File Comparison ---")
staging_truth_files = {}
for f in os.listdir(STAGING_TRUTH_DIR):
    fpath = os.path.join(STAGING_TRUTH_DIR, f)
    staging_truth_files[f] = fpath

truth_files = {}
for f in os.listdir(TRUTH_DIR):
    fpath = os.path.join(TRUTH_DIR, f)
    truth_files[f] = fpath

for fname in sorted(staging_truth_files.keys()):
    if fname in truth_files:
        try:
            with open(staging_truth_files[fname]) as f:
                staging_c = f.read()
            with open(truth_files[fname]) as f:
                final_c = f.read()
            sim = similarity_ratio(staging_c, final_c)
            flag = (
                " *** MATCH"
                if sim > 0.95
                else (" *** VERY SIMILAR" if sim > 0.85 else " *** DIFFERENT" if sim < 0.70 else "")
            )
            staging_len = len(staging_c)
            final_len = len(final_c)
            size_diff = ""
            if staging_len > final_len * 1.2:
                size_diff = f" [STAGING IS BIGGER: {staging_len} vs {final_len} chars]"
            elif final_len > staging_len * 1.2:
                size_diff = f" [FINAL IS BIGGER: {final_len} vs {staging_len} chars]"
            print(f"  {fname}: {sim:.1%} similar{flag}{size_diff}")
        except:
            print(f"  {fname}: ERROR reading files")
    else:
        print(f"  {fname}: exists in staging but NOT in final truth")

# Check for staging-only truth files
for fname in sorted(staging_truth_files.keys()):
    if fname not in truth_files:
        print(f"  {fname}: STAGING-ONLY (no final truth counterpart)")

# Check for final-only truth files
for fname in sorted(truth_files.keys()):
    if fname not in staging_truth_files:
        print(f"  {fname}: FINAL-ONLY (no staging counterpart)")

# ============================================================
# SECTION 5: DECISION JSON CONTENT OVERLAP
# ============================================================
print("\n" + "=" * 80)
print("SECTION 5: DECISION JSON CONTENT OVERLAP")
print("=" * 80)

decision_files = sorted(
    [f for f in os.listdir(CHAPTERS_DIR) if re.match(r"chapter-\d+-decisions\.json$", f)],
    key=lambda x: int(re.search(r"chapter-(\d+)-decisions\.json", x).group(1)),
)

decision_contents = {}
for df in decision_files:
    ch_num = int(re.search(r"chapter-(\d+)-decisions\.json", df).group(1))
    fpath = os.path.join(CHAPTERS_DIR, df)
    try:
        with open(fpath) as f:
            decision_contents[ch_num] = f.read()
    except:
        pass

print(f"Total decision files: {len(decision_contents)}")

# 5a. Adjacent chapter decision similarity
print("\n--- 5a. Adjacent Chapter Decision Similarity ---")
adj_dec_high = []
for i in range(1, max(decision_contents.keys())):
    if i in decision_contents and (i + 1) in decision_contents:
        sim = similarity_ratio(decision_contents[i], decision_contents[i + 1])
        if sim > 0.50:
            adj_dec_high.append((i, i + 1, sim))
            print(f"  Decisions {i}-{i + 1}: {sim:.1%} similarity -- POTENTIAL COPY")
if not adj_dec_high:
    print("  No adjacent decision files exceed 50% similarity.")

# Top 10 most similar adjacent decision pairs
print("\n--- Top 10 Most Similar Adjacent Decision Pairs ---")
adj_dec_all = []
for i in range(1, max(decision_contents.keys())):
    if i in decision_contents and (i + 1) in decision_contents:
        sim = similarity_ratio(decision_contents[i], decision_contents[i + 1])
        adj_dec_all.append((i, i + 1, sim))
adj_dec_all.sort(key=lambda x: -x[2])
for pair in adj_dec_all[:10]:
    print(f"  Decisions {pair[0]}-{pair[1]}: {pair[2]:.1%} similarity")

# 5b. Check for copy-paste of selections/adjustments
print("\n--- 5b. Decision Structure Analysis ---")
# Parse first decision file to understand structure
if decision_contents:
    first_key = min(decision_contents.keys())
    try:
        first_json = json.loads(decision_contents[first_key])
        print(f"  Decision JSON keys for chapter {first_key}: {list(first_json.keys())}")
    except:
        print(f"  Could not parse decision JSON for chapter {first_key}")

# Check for identical decision values
print("\n--- 5c. Identical Decision Values Across Adjacent Chapters ---")
for i in range(1, max(decision_contents.keys())):
    if i in decision_contents and (i + 1) in decision_contents:
        try:
            d1 = json.loads(decision_contents[i])
            d2 = json.loads(decision_contents[i + 1])

            # Compare top-level string values
            for key in set(d1.keys()) & set(d2.keys()):
                if isinstance(d1[key], str) and isinstance(d2[key], str):
                    if d1[key] == d2[key] and len(d1[key]) > 50:
                        print(
                            f"  Chapters {i}-{i + 1}: IDENTICAL '{key}' value ({len(d1[key])} chars)"
                        )
        except:
            pass

# ============================================================
# SECTION 6: SNAPSHOT CONTENT ANALYSIS
# ============================================================
print("\n" + "=" * 80)
print("SECTION 6: SNAPSHOT CONTENT ANALYSIS")
print("=" * 80)

snapshot_files = sorted(
    [f for f in os.listdir(SNAPSHOTS_DIR) if re.match(r"chapter-\d+-\d+T\d+\.md$", f)],
    key=lambda x: int(re.search(r"chapter-(\d+)-\d+T", x).group(1)),
)

# Create mapping: chapter number -> list of snapshot files
snapshot_by_ch = defaultdict(list)
for sf in snapshot_files:
    ch_num = int(re.search(r"chapter-(\d+)-\d+T", sf).group(1))
    snapshot_by_ch[ch_num].append(sf)

print(f"Total snapshots: {len(snapshot_files)} across {len(snapshot_by_ch)} chapters")

# 6a. Compare snapshots with chapter files for 5 random chapters
print("\n--- 6a. Snapshot vs Chapter File Comparison (5 random chapters) ---")
random.seed(123)
chapters_with_both = sorted(set(snapshot_by_ch.keys()) & set(chapter_prose.keys()))
sample_chapters_snap = random.sample(chapters_with_both, min(5, len(chapters_with_both)))

for ch in sorted(sample_chapters_snap):
    print(f"\n  Chapter {ch}:")
    chapter_prose_text = chapter_prose.get(ch, "")
    chapter_len = len(chapter_prose_text)
    print(f"    Chapter file prose length: {chapter_len} chars")

    for sf in snapshot_by_ch[ch][:3]:  # Up to 3 snapshots per chapter
        sf_path = os.path.join(SNAPSHOTS_DIR, sf)
        try:
            with open(sf_path) as f:
                snap_content = f.read()

            # Extract prose from snapshot (same META-END logic)
            idx = snap_content.rfind("<!--META-END-->")
            if idx == -1:
                idx = snap_content.rfind("META-END")
            if idx != -1:
                end_marker = snap_content.find("\n", idx)
                if end_marker != -1:
                    snap_prose = snap_content[end_marker:].strip()
                else:
                    snap_prose = snap_content.strip()
            else:
                snap_prose = snap_content.strip()

            snap_len = len(snap_prose)
            sim = similarity_ratio(chapter_prose_text, snap_prose)
            size_ratio = snap_len / chapter_len if chapter_len > 0 else 0

            # Check if snapshot has extra content
            extra_flag = ""
            if snap_len > chapter_len * 1.1:
                extra_flag = f" [SNAPSHOT BIGGER: +{snap_len - chapter_len} chars, {size_ratio:.1%} of chapter]"
            elif chapter_len > snap_len * 1.1:
                extra_flag = f" [CHAPTER BIGGER: +{chapter_len - snap_len} chars]"
            else:
                extra_flag = " [Roughly same size]"

            print(f"    Snapshot {sf}:")
            print(f"      Length: {snap_len} chars, Similarity: {sim:.1%}{extra_flag}")

        except Exception as e:
            print(f"    Snapshot {sf}: ERROR - {e}")

# 6b. Check all snapshots for extra content not in chapter
print("\n--- 6b. Snapshots With Significantly More Content Than Chapter ---")
for ch in sorted(chapters_with_both):
    chapter_prose_text = chapter_prose.get(ch, "")
    chapter_len = len(chapter_prose_text)

    for sf in snapshot_by_ch[ch]:
        sf_path = os.path.join(SNAPSHOTS_DIR, sf)
        try:
            with open(sf_path) as f:
                snap_content = f.read()
            idx = snap_content.rfind("<!--META-END-->")
            if idx == -1:
                idx = snap_content.rfind("META-END")
            if idx != -1:
                end_marker = snap_content.find("\n", idx)
                if end_marker != -1:
                    snap_prose = snap_content[end_marker:].strip()
                else:
                    snap_prose = snap_content.strip()
            else:
                snap_prose = snap_content.strip()

            snap_len = len(snap_prose)
            if chapter_len > 0 and snap_len > chapter_len * 1.15:
                print(
                    f"  Chapter {ch}, {sf}: SNAPSHOT is {snap_len - chapter_len} chars LARGER ({snap_len / chapter_len:.1%} of chapter)"
                )
        except:
            pass

print("\n" + "=" * 80)
print("AUDIT COMPLETE")
print("=" * 80)
