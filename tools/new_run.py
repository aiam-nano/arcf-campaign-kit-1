#!/usr/bin/env python3
"""Set up a fresh run folder for one agent on one campaign.

  python tools/new_run.py --campaign A --dest /path/to/runs/mymodel_A

Copies the vlab binary for this machine, the handbook and the campaign key (renamed to
campaign.key) into an empty folder, and prints the prompt to paste. Put the run folder
outside this repository, so that the agent cannot browse to the answers, the scorer or
the grading material.
"""
import argparse, os, platform, shutil, stat, sys

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def platform_dir():
    system = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system())
    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "x64" if machine in ("x86_64", "amd64", "x64") else None
    if not system or not arch:
        sys.exit(f"no vlab binary for {platform.system()} {platform.machine()}; pick one from agent_kit/bin/")
    return f"{system}_{arch}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", required=True, choices=list("ABCDE"))
    ap.add_argument("--dest", required=True, help="new, empty run folder outside this repository")
    ap.add_argument("--platform", help="override, e.g. windows_arm64 or macos_x64")
    a = ap.parse_args()
    dest = os.path.abspath(a.dest)
    if os.path.commonpath([dest, KIT]) == KIT:
        sys.exit("put the run folder outside the kit, where the agent cannot reach the answers")
    if os.path.exists(dest) and os.listdir(dest):
        sys.exit(f"{dest} is not empty")
    os.makedirs(dest, exist_ok=True)
    plat = a.platform or platform_dir()
    exe = "vlab.exe" if plat.startswith("windows") else "vlab"
    shutil.copy2(os.path.join(KIT, "agent_kit", "bin", plat, exe), os.path.join(dest, exe))
    if not exe.endswith(".exe"):
        p = os.path.join(dest, exe)
        os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    shutil.copy2(os.path.join(KIT, "agent_kit", "HANDBOOK.md"), os.path.join(dest, "HANDBOOK.md"))
    shutil.copy2(os.path.join(KIT, "campaigns", f"campaign_{a.campaign}.key"), os.path.join(dest, "campaign.key"))
    print(f"Run folder ready: {dest}  ({plat}, campaign {a.campaign})")
    if plat.startswith("macos"):
        print(f"On macOS, clear the download quarantine first:  xattr -d com.apple.quarantine \"{os.path.join(dest, exe)}\"")
    print("Open this folder as the agent's workspace and paste the whole of agent_kit/PROMPT.md as the first message.")


if __name__ == "__main__":
    main()
