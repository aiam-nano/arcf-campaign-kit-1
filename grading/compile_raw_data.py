#!/usr/bin/env python3
"""Compile the raw data files a grader asked for into one text file (step 2 of the grading prompt).

  python grading/compile_raw_data.py --run-dir <run folder> --out raw_data_compiled.txt lab_data/E0012_tensile_B004.csv ...

Each file is written between a "===== FILE: <name>" line and a "===== END: <name>" line.
"""
import argparse, os, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("files", nargs="+", help="paths relative to the run folder, as listed by the grader")
    a = ap.parse_args()
    root = os.path.abspath(a.run_dir)
    with open(a.out, "w", encoding="utf-8") as out:
        for name in a.files:
            p = os.path.abspath(os.path.join(root, name))
            if os.path.commonpath([p, root]) != root or not os.path.isfile(p):
                sys.exit(f"not a file in the run folder: {name}")
            out.write(f"===== FILE: {name}\n")
            out.write(open(p, encoding="utf-8", errors="replace").read().rstrip("\n") + "\n")
            out.write(f"===== END: {name}\n\n")
    print(f"wrote {a.out} ({len(a.files)} files)")


if __name__ == "__main__":
    main()
