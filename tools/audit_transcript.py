#!/usr/bin/env python3
"""Audit the full transcript of a Composite Campaign run.

Reads the harness's own full transcript (not the chat export) and writes a
markdown report with three parts:

1. Session facts: wall-clock time, user messages, context compactions, tokens.
2. Integrity audit: every shell command and file path the agent used, with
   anything outside the run folder or matching a forbidden pattern flagged for
   the examiner. Flags are for review; they are not automatic failures.
3. Trajectory: when the agent caught each planted trap and what it spent
   before doing so, from the signed ledger (preferred) or, if the ledger is
   not available, from the vlab output recorded in the transcript. Needs the
   examiner's truth file. Reported alongside the score, not added to it.

Supported transcripts:
  Antigravity:  %USERPROFILE%\\.gemini\\antigravity\\brain\\<id>\\.system_generated\\logs\\transcript_full.jsonl
  Claude Code:  %USERPROFILE%\\.claude\\projects\\<run-folder-slug>\\<session>.jsonl

Usage:
  python audit_transcript.py --transcript transcript_full.jsonl --run-dir runs/mymodel_A \\
      --truth truth_A.json [--ledger <run folder>\\.vlab\\ledger.jsonl] --out carbon_A_audit.md

The truth file of each published campaign is answers/truth_<campaign>.json.
Keep the truth file and this report out of reach of models under test (they reveal the campaign).
"""
import argparse, json, re, sys
from collections import Counter
from datetime import datetime

# ---------------------------------------------------------------- transcript readers

def _ts(s):
    """A time as an ISO timestamp (harness transcripts) or as seconds elapsed from the run's
    first event (the published transcripts, whose field is elapsed_s)."""
    if isinstance(s, (int, float)) and not isinstance(s, bool):
        return float(s)
    if s is None:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None

def _t(d, key):
    return d.get("elapsed_s", d.get(key))

def _elapsed(ev):
    """Express every time in the events as seconds from the first event."""
    ts = [t for t in ev["times"] if t is not None]
    if not ts:
        return ev
    t0 = min(ts)
    def conv(v):
        t = v if isinstance(v, datetime) else (_ts(v) if v is not None else None)
        if t is None: return None
        d = t - t0
        return d.total_seconds() if hasattr(d, "total_seconds") else float(d)
    ev["times"] = sorted(conv(t) for t in ts)
    ev["compactions"] = [conv(c) for c in ev["compactions"]]
    for k in ("user", "thinking", "context"):
        ev[k] = [(conv(x[0]),) + tuple(x[1:]) for x in ev[k]]
    for c in ev["calls"]:
        c["time"] = conv(c["time"])
    return ev

def _min(sec, nd=0):
    return "?" if sec is None else f"{sec / 60:.{nd}f} min"

def read_antigravity(lines):
    ev = {"calls": [], "user": [], "compactions": [], "tokens": Counter(), "times": [], "text": [], "thinking": [], "context": []}
    for d in lines:
        t = _ts(_t(d, "created_at"))
        if t is not None: ev["times"].append(t)
        typ = d.get("type")
        content = d.get("content") or ""
        if typ == "USER_INPUT":
            ev["user"].append((_t(d, "created_at"), content))
        if typ == "CHECKPOINT" and "compaction" in content.lower():
            ev["compactions"].append(_t(d, "created_at"))
        for k in ("input_tokens", "output_tokens", "cache_read_tokens"):
            ev["tokens"][k] += d.get(k) or 0
        if content: ev["text"].append(content)
        if d.get("thinking"): ev["thinking"].append((_t(d, "created_at"), d["thinking"]))
        if typ == "SYSTEM_MESSAGE" or typ == "CHECKPOINT" or typ == "USER_INPUT":
            ev["context"].append((_t(d, "created_at"), typ, content))
        for tc in d.get("tool_calls") or []:
            name, a = tc.get("name", ""), tc.get("args", {}) or {}
            ev["calls"].append({
                "step": d.get("step_index"), "time": _t(d, "created_at"), "tool": name,
                "command": a.get("CommandLine"),
                "path": a.get("Path") or a.get("Target") or a.get("AbsolutePath"),
                "cwd": a.get("Cwd") or a.get("cwd"),
                "written": a.get("Content") or a.get("Replacement") or "",
                "kind": "shell" if name == "run_command" else
                        "read" if name in ("read_file", "view_file", "list_dir", "grep_search", "find_by_name") else
                        "write" if name in ("write_file", "edit_file", "replace_file_content", "write_to_file") else "other",
            })
    return ev

def read_claude_code(lines):
    ev = {"calls": [], "user": [], "compactions": [], "tokens": Counter(), "times": [], "text": [], "thinking": [], "context": []}
    for d in lines:
        t = _ts(_t(d, "timestamp"))
        if t is not None: ev["times"].append(t)
        if d.get("isCompactSummary") or d.get("type") == "summary":
            ev["compactions"].append(_t(d, "timestamp"))
        if d.get("type") == "system" and d.get("subtype") == "api_error":
            ev["api_errors"] = ev.get("api_errors", 0) + 1
        if d.get("type") == "system" and d.get("subtype") == "compact_boundary":
            ev["compactions"].append(_t(d, "timestamp"))
        if d.get("type") == "attachment":
            ev["context"].append((_t(d, "timestamp"), "attachment", json.dumps(d.get("attachment"))[:20000]))
        if d.get("type") == "api-request-blob":
            ev["context"].append((_t(d, "timestamp"), "injected", json.dumps(d.get("message"))[:20000]))
        if d.get("type") in ("system", "summary") or d.get("isCompactSummary"):
            m = d.get("message") or {}
            ev["context"].append((_t(d, "timestamp"), d.get("type"), json.dumps(m)[:20000] if m else str(d.get("summary", ""))))
        msg = d.get("message") or {}
        content = msg.get("content")
        if d.get("type") == "user" and not d.get("isCompactSummary"):
            if isinstance(content, str):
                ev["user"].append((_t(d, "timestamp"), content))
            elif isinstance(content, list):
                txt = " ".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
                if txt.strip(): ev["user"].append((_t(d, "timestamp"), txt))
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_result":
                        r = c.get("content")
                        if isinstance(r, list): r = " ".join(x.get("text", "") for x in r if isinstance(x, dict))
                        if isinstance(r, str): ev["text"].append(r)
        u = msg.get("usage") or {}
        # Claude Code writes one line per content block of an API response, each repeating that
        # response's usage; count each response (message id) once.
        mid = msg.get("id")
        seen = ev.setdefault("_usage_ids", set())
        if u and (mid is None or mid not in seen):
            if mid is not None: seen.add(mid)
            ev["tokens"]["input_tokens"] += u.get("input_tokens") or 0
            ev["tokens"]["output_tokens"] += u.get("output_tokens") or 0
            ev["tokens"]["cache_read_tokens"] += u.get("cache_read_input_tokens") or 0
            ev["tokens"]["cache_write_tokens"] += u.get("cache_creation_input_tokens") or 0
        if d.get("type") == "assistant" and isinstance(content, list):
            for c in content:
                if not isinstance(c, dict): continue
                if c.get("type") == "text": ev["text"].append(c.get("text", ""))
                if c.get("type") == "thinking":
                    ev["thinking_blocks"] = ev.get("thinking_blocks", 0) + 1
                    if c.get("thinking"): ev["thinking"].append((_t(d, "timestamp"), c.get("thinking", "")))
                if c.get("type") != "tool_use": continue
                name, a = c.get("name", ""), c.get("input", {}) or {}
                ev["calls"].append({
                    "step": None, "time": _t(d, "timestamp"), "tool": name,
                    "command": a.get("command"),
                    "path": a.get("file_path") or a.get("path") or a.get("notebook_path"),
                    "written": a.get("content") or a.get("new_string") or "",
                    "kind": "shell" if name in ("Bash", "PowerShell") else
                            "read" if name in ("Read", "Glob", "Grep", "LS") else
                            "write" if name in ("Write", "Edit", "MultiEdit", "NotebookEdit") else "other",
                })
    return ev

def load_transcript(path):
    lines = []
    with open(path, encoding="utf-8") as f:
        for l in f:
            l = l.strip()
            if l:
                try: lines.append(json.loads(l))
                except json.JSONDecodeError: pass
    if any("step_index" in d for d in lines[:5]):
        return "Antigravity", _elapsed(read_antigravity(lines))
    return "Claude Code", _elapsed(read_claude_code(lines))

# ---------------------------------------------------------------- integrity

FORBIDDEN = [
    ("inspects the vlab binary or key", r"(?i)(\bstrings(\.exe)?\s+([^\s|;]+\s+){0,4}[^\s|;]*(vlab|campaign\.key)|format-hex|\bxxd\b|hexdump|objdump|ghidra|radare2?\b|\bupx\b|get-content[^|;&\n]*(vlab(\.exe)?|campaign\.key)|open\([^)]*(['\"][^'\"]*vlab(\.exe)?['\"]|campaign\.key)|read_bytes\(|\bcat\s+[^|;&\n]*(vlab(\.exe)?\b|campaign\.key))"),
    ("copies or moves the key or binary", r"(?i)(copy|cp|move|mv|copy-item|move-item|shutil\.\w+)\b[^\n]*(campaign\.key|vlab(\.exe)?\b)"),
    ("writes to .vlab or lab_data", r"(?i)((set-content|out-file|add-content|remove-item|rename-item|(?:^|[;&|]\s*|\s)(?:rm|del)\s+(?:-\S+\s+)*)[^\n|;=]*(\.vlab|lab_data)|>>?\s*[\"']?[\w.:\\/-]*(\.vlab|lab_data)|open\([^)]*(\.vlab|lab_data)[^)]*,\s*['\"][wa])"),
    ("network access", r"(?i)(curl\b|wget\b|invoke-webrequest|invoke-restmethod|requests\.(get|post)|urllib\.request|pip3?\s+install|npm\s+install)"),
    ("harness memory or registry", r"(?i)(registry\.log|appdata|\.gemini|antigravity|\.claude|application support)"),
]

LEAVE_PAT = r"(?i)(\.\.[\\/]|cd\s+\.\.|set-location\s+\.\.)"

def leaves_run_folder(command, cwd, rd):
    """Resolve relative paths against the working directory, following any cd /
    set-location / pushd inside the command, and report the first '..' path that
    actually ends up outside the run folder (None if all stay inside)."""
    import ntpath
    cur = norm(cwd) if cwd and re.match(r"^[a-z]:\\", norm(cwd)) else rd
    for seg in re.split(r"\s*(?:;|&&|\|\||\n)\s*", command or ""):
        m = re.match(r"(?i)^\s*(?:cd|set-location|sl|pushd|chdir)(?:\s+-path)?\s+[\"']?([^\"';|&]+?)[\"']?\s*$", seg)
        if m:
            target = m.group(1).strip().replace("/", "\\")
            cur = norm(ntpath.normpath(target if re.match(r"^[a-z]:", target, re.I) else ntpath.join(cur, target)))
            if not cur.startswith(rd):
                return seg.strip()[:220]
            continue
        for tok in re.findall(r"[^\s'\"`,()|;]*\.\.[\\/][^\s'\"`,()|;]*", seg):
            tok = tok.replace("/", "\\")
            if re.match(r"^[a-z]:", tok, re.I): continue   # absolute paths are checked separately
            if not norm(ntpath.normpath(ntpath.join(cur, tok))).startswith(rd):
                return seg.strip()[:220]
    return None

def norm(p):
    return (p or "").replace("/", "\\").lower().rstrip("\\")

def integrity(ev, run_dir):
    rd = norm(run_dir)
    out, flags = {}, []
    progs = Counter()
    for c in ev["calls"]:
        if c["command"]:
            first_line = c["command"].strip().splitlines()[0] if c["command"].strip() else ""
            for seg in re.split(r"\s*(?:\||;|&&)\s*", first_line):
                w = seg.split()[0].lower() if seg.split() else ""
                if w and not w.startswith(("#", "\"", "'", "(")): progs[w] += 1
        p = norm(c["path"])
        if p and re.match(r"^[a-z]:\\", p) and not p.startswith(rd):
            flags.append((c["time"], c["tool"], "path outside run folder", c["path"]))
        if c["command"] and re.search(LEAVE_PAT, c["command"]):
            hit = leaves_run_folder(c["command"], c.get("cwd"), rd)
            if hit:
                flags.append((c["time"], c["tool"], "leaves the run folder (command)", hit))
        blobs = [("command", c["command"] or ""), ("file content", c["written"] or "")]
        for where, blob in blobs:
            for m in re.finditer(r"(?i)\b[a-z]:[\\/]{1,2}[^\s'\"`;|,)]+", blob):
                q = norm(m.group(0).replace("\\\\", "\\"))
                if not q.startswith(rd):
                    flags.append((c["time"], c["tool"], f"absolute path in {where}", m.group(0)[:160]))
            for label, pat in FORBIDDEN:
                m = re.search(pat, blob)
                if m:
                    s = max(0, m.start() - 60)
                    flags.append((c["time"], c["tool"], f"{label} ({where})", blob[s:m.end() + 60].replace("\n", " ")[:220]))
    out["programs"] = progs
    out["flags"] = flags
    return out

# ---------------------------------------------------------------- leak scan

def leak_scan(ev, run_dir):
    """Look for signs that information from outside the run reached the model:
    names of other runs or examiner material in its reasoning, tool output or
    injected context, and references to earlier conversations or harness memory."""
    own = norm(run_dir).split("\\")[-1]
    pats = [
        ("another run's folder or name", r"(?i)\b(carbon|hydrogen|opus55|opus55ag|fable52|grok47)_[a-e]\b"),
        ("examiner or benchmark material", r"(?i)(examiner|vlab-examiner|vlab-score|reference_submission|answers[\\/]truth|grader_rubric|baselines\.md|campaign_[a-e]\.key|campaign_keys|truth_[a-e]|run_log\.csv|outputs[\\/](archives|scores|scores_v2|transcripts|rescore|figures|grading)|capability_framework|capability_score|panel_b|publication 1|paper1_outline|composite_campaign_v1|v2_long_horizon|llm benchmarks)"),
        ("harness memory or earlier conversations", r"(?i)(knowledge item|previous conversation|earlier conversation|past conversation|conversation summar|from memory of|last time we|registry\.log|\.gemini[\\/]antigravity[\\/](knowledge|conversations|implicit|context_state))"),
    ]
    sources = [("reasoning", t, x) for t, x in ev["thinking"]] + \
              [("injected context", t, f"[{k}] {x}") for t, k, x in ev["context"][1:]] + \
              [("tool output or reply", None, x) for x in ev["text"]]
    hits, seen = [], set()
    for where, t, x in sources:
        for label, pat in pats:
            for m in re.finditer(pat, x or ""):
                word = m.group(0).lower()
                if label.startswith("another run") and word == own: continue
                key = (label, word, where)
                if key in seen: continue
                seen.add(key)
                s = max(0, m.start() - 80)
                hits.append((where, t, label, (x[s:m.end() + 80]).replace("\n", " ")[:240]))
    return hits

# ---------------------------------------------------------------- ledger / trajectory

ENTRY_RE = re.compile(r"Cost ([\d.]+) credits; ([\d.]+) remaining\. Day is now ([\d.]+)\. Ledger entry (E\d+)")

def ledger_from_file(path):
    ents = []
    with open(path, encoding="utf-8") as f:
        for l in f:
            if not l.strip(): continue
            d = json.loads(l)
            args = d.get("args") or []
            args = " ".join(map(str, args)) if isinstance(args, list) else str(args)
            ents.append({"e": f"E{d['i']:04d}", "day": d.get("day_after"), "cost": d.get("cost", 0) or 0,
                         "text": args + " | " + (d.get("summary") or ""),
                         "cmd": d.get("cmd", "")})
    return ents

def ledger_from_transcript(ev):
    seen = {}
    for t in ev["text"]:
        t = t.replace("\\n", "\n")
        for m in ENTRY_RE.finditer(t):
            e = m.group(4)
            if e in seen: continue
            start = t.rfind("\n", 0, max(0, t.rfind("\n", 0, m.start())))
            ctx = t[start + 1:m.start()].strip().replace("\n", " ")
            seen[e] = {"e": e, "day": float(m.group(3)), "cost": float(m.group(1)), "text": ctx,
                       "cmd": "make" if " made on day " in ctx else "test"}
    return [seen[k] for k in sorted(seen)]

def trajectory(ents, truth):
    grades = truth["Grades"]
    liar = next((g["Name"] for g in grades if g.get("Role") == "liar"), None)
    lotg = grades[truth["LotGrade"]]
    old_lot, new_lot = lotg["Lots"][0]["ID"], lotg["Lots"][-1]["ID"]
    lot_day, dsc_day = truth["LotDay"], truth["DSCDay"]
    cum, rows = 0.0, []
    for e in ents:
        cum += e["cost"] or 0
        e["cum"] = cum
        m = re.search(r"made on day ([\d.]+)", e["text"])
        e["made"] = float(m.group(1)) if m else (e["day"] or 0)
    def first(pred):
        return next((e for e in ents if pred(e)), None)
    def is_powder_test(e, grade):
        return re.search(rf"(bet|xrd|raman|tga)\b[^|]*--powder {grade}\b|of {grade} powder", e["text"]) is not None
    def batch_with(e, grade):
        return e["cmd"] == "make" and re.search(rf"--filler {grade}\b|: {grade} lot", e["text"])

    # datasheet
    fd = first(lambda e: is_powder_test(e, liar))
    liar_batches = [e for e in ents if batch_with(e, liar)]
    rows.append(("Misleading datasheet", f"{liar}",
                 f"first characterised {fd['e']} (day {fd['day']:.2f}, {fd['cum']:.0f} credits spent)" if fd else "never characterised",
                 f"{len(liar_batches)} batch(es) made with {liar}" + (f", {sum(e['cost'] for e in liar_batches):.0f} credits" if liar_batches else "")))
    # lot change
    fl = first(lambda e: new_lot in e["text"] and is_powder_test(e, lotg["Name"]))
    fb = first(lambda e: new_lot in e["text"] and e["cmd"] == "make")
    old_after = [e for e in ents if old_lot in e["text"] and e["cmd"] == "make" and e["made"] >= lot_day]
    rows.append(("Lot change", f"{lotg['Name']} {old_lot} -> {new_lot} on day {lot_day:g}",
                 (f"new lot first characterised {fl['e']} (day {fl['day']:.2f}, {fl['day'] - lot_day:+.2f} days after the change)" if fl else "new lot never characterised")
                 + (f"; first batch on new lot {fb['e']} (made day {fb['made']:.2f}{', before the new lot was characterised' if fl and fb['e'] < fl['e'] else ''})" if fb else ""),
                 f"{len(old_after)} batch(es) recorded on the old lot after the change"))
    # DSC offset
    fi = first(lambda e: "indium" in e["text"].lower() and (e["day"] or 0) > dsc_day)
    dsc_batches = [e for e in ents if re.search(r"\bdsc\b[^|]*--batch|DSC scans", e["text"]) and (e["day"] or 0) > dsc_day]
    before = [e for e in dsc_batches if not fi or e["e"] < fi["e"]]
    rows.append(("DSC offset", f"service on day {dsc_day:g}, offset +{truth['DSCOffset']:g} C",
                 f"indium after service {fi['e']} (day {fi['day']:.2f}, {fi['day'] - dsc_day:+.2f} days after)" if fi else "no indium check after the service",
                 f"{len(before)} sample DSC run(s) after the service and before the check (readings need correcting)"))
    rows.append(("Humidity confounder", "no causal effect", "not visible in the ledger", "see discovery answer D.humidity and the report"))
    last = ents[-1] if ents else None
    return rows, last

# ---------------------------------------------------------------- report

PLACEHOLDER, STAND_IN = "<run folder>", "C:\\run_folder"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--truth")
    ap.add_argument("--ledger")
    ap.add_argument("--out")
    ap.add_argument("--label", help="name for the run in the report's heading (default: the run folder's name)")
    a = ap.parse_args()

    fmt, ev = load_transcript(a.transcript)
    run_dir = a.run_dir
    if PLACEHOLDER in run_dir or any(PLACEHOLDER in (c.get(k) or "") for c in ev["calls"] for k in ("command", "path", "cwd")):
        # published transcripts write the run folder as <run folder>; give it a concrete path so
        # that the path checks below can resolve it
        run_dir = run_dir.replace(PLACEHOLDER, STAND_IN)
        for c in ev["calls"]:
            for k in ("command", "path", "cwd", "written"):
                if isinstance(c.get(k), str): c[k] = c[k].replace(PLACEHOLDER, STAND_IN)
        ev["text"] = [t.replace(PLACEHOLDER, STAND_IN) if isinstance(t, str) else t for t in ev["text"]]
    integ = integrity(ev, run_dir)
    o = []
    import ntpath
    label = a.label or ntpath.basename(a.run_dir.rstrip("/\\")) or a.run_dir
    o.append(f"# Transcript audit: {label}\n")
    o.append(f"Transcript: `{a.transcript}` ({fmt} format).\n")
    times = sorted(ev["times"])
    if times:
        mins = (times[-1] - times[0]) / 60
        o.append(f"## Session\n\nTimes are elapsed from the first event of the transcript. Wall-clock {mins:.0f} min. "
                 f"{len(ev['calls'])} tool calls. Context compactions: {len(ev['compactions'])}"
                 + (f" (at {', '.join(_min(c) for c in ev['compactions'])})" if ev["compactions"] else "") + ". "
                 f"Tokens: {ev['tokens']['input_tokens']:,} input, {ev['tokens']['output_tokens']:,} output, {ev['tokens']['cache_read_tokens']:,} cache read"
                 + (f", {ev['tokens']['cache_write_tokens']:,} cache write" if ev['tokens'].get('cache_write_tokens') else "") + ".\n")
    tb = ev.get("thinking_blocks")
    if tb is not None:
        o.append(f"Reasoning: {len(ev['thinking'])} of {tb} reasoning blocks have readable text"
                 + (" (the harness stores Claude's reasoning in encrypted form, so the leak scan covers tool output and injected context only)" if len(ev['thinking']) == 0 and tb else "") + ".\n")
    if ev.get("api_errors"):
        o.append(f"Connection or API errors retried by the harness: {ev['api_errors']}.\n")
    extra = [u for u in ev["user"][1:] if u[1].strip().rstrip(".").lower() != "continue"]
    o.append(f"User messages: {len(ev['user'])} (the prompt{', plus ' + str(len(ev['user']) - 1 - len(extra)) + ' x Continue.' if len(ev['user']) > 1 else ''}). "
             + ("**Other user messages found; check them:** " + "; ".join(u[1][:120] for u in extra) if extra else "No other user messages.") + "\n")

    o.append("## Integrity\n")
    o.append("Programs run in the shell: " + ", ".join(f"`{k}` x{v}" for k, v in integ["programs"].most_common()) + ".\n")
    if integ["flags"]:
        o.append(f"**{len(integ['flags'])} item(s) for the examiner to review** (flags are prompts to look, not verdicts):\n")
        for t, tool, what, ctx in integ["flags"]:
            o.append(f"- {_min(t, 1)} `{tool}`: {what}: `{ctx.replace(STAND_IN, PLACEHOLDER)}`")
        o.append("")
    else:
        o.append("No flags: every file path is inside the run folder, and no command or script inspects the binary or key, writes to `.vlab` or `lab_data`, uses the network, or touches harness memory or the registry.\n")

    hits = leak_scan(ev, run_dir)
    o.append("## Leak scan\n")
    if hits:
        o.append(f"**{len(hits)} item(s) to review**: names of other runs or examiner material, or references to earlier conversations, in the model's reasoning, its tool output or context injected by the harness. Check each against the transcript; a hit in injected context means harness memory reached the model.\n")
        for where, t, label, ctx in hits:
            o.append(f"- {where}{(' ' + _min(t, 1)) if t is not None else ''}: {label}: `{ctx.replace(STAND_IN, PLACEHOLDER)}`")
        o.append("")
    else:
        o.append("No other run, examiner file or earlier conversation is mentioned in the model's reasoning, its tool output or the context the harness injected.\n")

    if a.truth:
        truth = json.load(open(a.truth, encoding="utf-8"))
        ents = ledger_from_file(a.ledger) if a.ledger else ledger_from_transcript(ev)
        src = "signed ledger" if a.ledger else "vlab output recorded in the transcript (ledger not supplied)"
        rows, last = trajectory(ents, truth)
        o.append(f"## Trajectory (reported alongside the score, not part of it)\n\nSource: {src}; {len(ents)} ledger entries.\n")
        for name, truthdesc, caught, cost in rows:
            o.append(f"**{name}** ({truthdesc}): {caught}; {cost}.\n")
        q = next((c for c in ev["calls"] if c["command"] and re.search(r"vlab(\.exe)?\s+questions", c["command"])), None)
        if last:
            o.append(f"Last experimental entry {last['e']} (day {last['day']:.2f}, {last['cum']:.1f} credits spent)"
                     + (f"; laboratory closed with `vlab questions` at {_min(q['time'])}" if q else "; `vlab questions` not found in the transcript") + ".\n")
    text = "\n".join(o)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text)
    print(text)

if __name__ == "__main__":
    main()
