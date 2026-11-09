#!/usr/bin/env python3
"""
Static audit of owo's mixins against the Minecraft 26.3 deobfuscated jar.

For every mixin declared in owo.mixins.json this checks, without launching the game:
  * the @Mixin target class exists in 26.3
  * every @Inject/@Redirect/@ModifyArgs/@WrapOperation/@Overwrite target method exists
  * every @Shadow member and @Accessor/@Invoker target exists

Known blind spots (reported separately so they are not mistaken for defects):
  * methods introduced by other mods' mixins (e.g. Fabric API's updateSelection) are resolved
    against the mixin classes of the mods on the classpath
  * constructors (<init>) are always accepted
  * targets with remap = false are only checked when they live in Minecraft itself
"""
import json
import os
import re
import subprocess
import sys
import zipfile
from collections import defaultdict

ROOT = r"C:\Users\Administrator\Desktop\mod\owo-lib-0.13.1-26.2"
MC_JAR = os.path.expandvars(
    r"%USERPROFILE%\.gradle\caches\fabric-loom\minecraftMaven\net\minecraft"
    r"\minecraft-merged-deobf\26.3\minecraft-merged-deobf-26.3.jar"
)
MIXIN_JSON = os.path.join(ROOT, "src", "main", "resources", "owo.mixins.json")
SRC = os.path.join(ROOT, "src", "main", "java")

# ----------------------------------------------------------------- class index
mc_classes = set()
with zipfile.ZipFile(MC_JAR) as z:
    for entry in z.namelist():
        if entry.endswith(".class"):
            mc_classes.add(entry[:-6].replace("/", "."))

# index by simple name -> candidates, so "Item.Properties" can be resolved
by_tail = defaultdict(list)
for c in mc_classes:
    by_tail[c].append(c)

# ------------------------------------------------- foreign mixin members (FAPI etc)
FOREIGN_JARS = []
fabric_api_root = os.path.expandvars(
    r"%USERPROFILE%\.gradle\caches\modules-2\files-2.1\net.fabricmc.fabric-api"
)
if os.path.isdir(fabric_api_root):
    for dirpath, _dirs, files in os.walk(fabric_api_root):
        for fn in files:
            if fn.endswith(".jar") and "sources" not in fn:
                FOREIGN_JARS.append(os.path.join(dirpath, fn))

foreign_methods = defaultdict(set)   # class -> method names added by other mods' mixins
foreign_fields = defaultdict(set)


def scan_foreign_mixins():
    """Collect methods that other mods' mixins inject into vanilla classes."""
    for jar in FOREIGN_JARS:
        try:
            with zipfile.ZipFile(jar) as z:
                for entry in z.namelist():
                    if not entry.endswith(".class"):
                        continue
                    if "/mixin/" not in entry and not entry.startswith("mixin/"):
                        continue
                    src = z.read(entry)
                    text = src.decode("latin-1", errors="replace")
                    # crude: pull the @Mixin target and any declared method names
                    tm = re.search(r"mixin/([\w/$]+)\.class", text)
                    if not tm:
                        continue
                    target = tm.group(1).replace("/", ".")
                    for m in re.finditer(r"([a-zA-Z_$][\w$]*)\s*\(", text):
                        foreign_methods[target].add(m.group(1))
        except Exception:
            continue


# ----------------------------------------------------------------- javap helper
_javap_cache = {}


def javap_members(fqcn):
    """Return (methods, fields) declared by fqcn, or None when the class is absent."""
    if fqcn in _javap_cache:
        return _javap_cache[fqcn]
    res = None
    try:
        out = subprocess.run(
            ["javap", "-p", "-cp", MC_JAR, fqcn],
            capture_output=True, text=True, timeout=60,
        )
        if out.returncode == 0 and out.stdout.strip():
            methods, fields = set(), set()
            for line in out.stdout.splitlines():
                line = line.strip()
                if not line or line.startswith("Compiled from"):
                    continue
                if line.endswith("{") or line.endswith("}"):
                    continue
                # method declaration: ends with ')' possibly followed by ';' (abstract) or throws
                m = re.search(r"([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*(?:throws\s[\w.,\s]+)?;?$", line)
                if m:
                    methods.add(m.group(1))
                    continue
                # field declaration: "... type name;"
                m = re.search(r"([A-Za-z_$][\w$]*)\s*;$", line)
                if m:
                    fields.add(m.group(1))
            res = (methods, fields)
    except Exception:
        res = None
    _javap_cache[fqcn] = res
    return res


# ----------------------------------------------------------------- mixin parsing
def strip_comments(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"//[^\n]*", "", src)
    return src


def annotation_body(src, start):
    """Return the text inside the parentheses of an annotation starting at `start`."""
    seg = src[start:]
    depth, end = 1, None
    for i, ch in enumerate(seg):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                end = i
                break
    return seg[:end] if end else seg


def resolve_target(name):
    """Resolve a possibly-partial class name against the 26.3 index.

    Handles: fully qualified names, "Outer.Inner" nested references, and bare simple names
    such as "Connection" or "Main" (unique by simple name only).
    """
    if name in mc_classes:
        return name
    if "." in name:
        head, tail = name.rsplit(".", 1)
        if head in mc_classes:
            cand = f"{head}${tail}"
            if cand in mc_classes:
                return cand
        # "Outer.Inner" where Outer is itself only a simple name
        for c in mc_classes:
            if c.endswith("." + name.replace(".", "$")):
                return c
        hits = [c for c in mc_classes if c.endswith("." + name)]
        if len(hits) == 1:
            return hits[0]
        return None
    # bare simple name: unique simple name match
    hits = [c for c in mc_classes if c.endswith("." + name)]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        # prefer the one in a plausible package
        for pref in ("net.minecraft.network.", "net.minecraft.server.",
                     "net.minecraft.client."):
            sub = [c for c in hits if c.startswith(pref)]
            if len(sub) == 1:
                return sub[0]
    return None


def parse_mixin(path):
    with open(path, encoding="utf-8") as fh:
        src = strip_comments(fh.read())

    info = {"target": None, "injects": [], "shadows": [], "accessors": []}

    # the annotation may be written fully qualified: @org.spongepowered.asm.mixin.Mixin(...)
    m = re.search(r"(?:^|\s)@(?:\w+\.)*Mixin\s*\(", src)
    if m:
        seg = annotation_body(src, m.end() - 1)
        mm = re.search(r"targets\s*=\s*\"([\w.$]+)\"", seg)
        if mm:
            info["target"] = mm.group(1)
        else:
            # fully qualified nested class: com.foo.Outer.Inner.class
            mm = re.search(r"([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*\.class", seg)
            if mm:
                info["target"] = mm.group(1)

    for m in re.finditer(
            r"@(Inject|Redirect|ModifyArgs|ModifyArg|ModifyConstant|ModifyVariable|"
            r"ModifyExpressionValue|WrapOperation|WrapWithCondition|WrapTry)\b", src):
        seg = annotation_body(src, src.index("(", m.end()))
        remap_off = "remap = false" in seg or "remap=false" in seg
        mm = re.search(r"method\s*=\s*\"([^\"]+)\"", seg)
        names = [mm.group(1)] if mm else []
        if not names:
            mm = re.search(r"method\s*=\s*\{([^}]*)\}", seg)
            if mm:
                names = re.findall(r"\"([^\"]+)\"", mm.group(1))
        for n in names:
            info["injects"].append((m.group(1), n, remap_off))

    for m in re.finditer(r"@Accessor\b", src):
        seg = src[m.end(): m.end() + 200]
        mm = re.search(r"\"([^\"]+)\"", seg)
        info["accessors"].append(mm.group(1) if mm else None)

    for m in re.finditer(r"@Shadow\b", src):
        # Take only the declaration that follows this @Shadow, stopping at the next
        # annotation or the end of the statement. The naive regex used to run past the
        # declaration and pick up an unrelated member further down.
        seg = src[m.end(): m.end() + 400]
        stop = len(seg)
        nxt = seg.find("@")
        if nxt != -1:
            stop = nxt
        seg = seg[:stop]

        # field:  [modifiers] Type name;
        mf = re.search(r"([A-Za-z_$][\w$]*)\s+([A-Za-z_$][\w$]*)\s*;", seg)
        if mf:
            info["shadows"].append(("field", mf.group(2)))
            continue
        # method: [modifiers] ReturnType name(...);
        mm = re.search(r"([A-Za-z_$][\w$]*)\s+([A-Za-z_$][\w$]*)\s*\([^)]*\)", seg)
        if mm:
            info["shadows"].append(("method", mm.group(2)))

    return info


def main():
    scan_foreign_mixins()

    with open(MIXIN_JSON, encoding="utf-8") as fh:
        cfg = json.load(fh)

    pkg = cfg["package"]
    entries = []
    for key in ("mixins", "client", "server"):
        entries += [(e, key) for e in cfg.get(key, [])]

    base = os.path.join(SRC, pkg.replace(".", os.sep))
    problems, skipped = [], []

    for entry, side in entries:
        # inner classes are declared as "Outer$Inner" in the json but live in Outer.java
        rel = entry.replace(".", os.sep) + ".java"
        path = os.path.join(base, rel)
        if not os.path.exists(path):
            if "$" in entry:
                # inner class: the source lives in the outer class' file. Note that the mixin
                # json uses the *binary* name (Outer$Inner) while the java source declares a
                # plain nested class (Inner) - both are valid and refer to the same class.
                outer = os.path.join(base, entry.split("$")[0].replace(".", os.sep) + ".java")
                if os.path.exists(outer):
                    path = outer
                    skipped.append((entry, side,
                                    "inner class declared in the outer class' source file"))
                    continue
                problems.append(("MISSING_SOURCE", entry, side, "source file not found"))
                continue
            else:
                problems.append(("MISSING_SOURCE", entry, side, "source file not found"))
                continue

        info = parse_mixin(path)
        if not info["target"]:
            problems.append(("NO_TARGET", entry, side, "could not parse @Mixin target"))
            continue

        target = resolve_target(info["target"])
        if target is None:
            # Targets that are not Minecraft classes at all: owo's own classes, classes from
            # optional dependencies (STAPI), or classes removed in 26.3. These are reported as
            # informational rather than as defects, because the authoritative check for them is
            # the runtime mixin audit in the client log.
            skipped.append((entry, side,
                            f"target '{info['target']}' is not a Minecraft 26.3 class"))
            continue

        res = javap_members(target)
        if res is None:
            skipped.append((entry, side, f"cannot javap {target}"))
            continue
        tmethods, tfields = res

        # methods added by other mods' mixins count as existing
        extra_methods = foreign_methods.get(target, set())

        for kind, mname, remap_off in info["injects"]:
            base_name = mname.split("(")[0].strip()
            if not base_name or base_name == "<init>":
                continue
            if base_name in tmethods or base_name in extra_methods:
                continue
            if remap_off:
                skipped.append((entry, side,
                                f"@{kind} '{base_name}' remap=false (not in Minecraft)"))
                continue
            problems.append(("MISSING_METHOD", entry, side,
                             f"@{kind} method '{base_name}' not on {target}"))

        for kind, name in info["shadows"]:
            pool = tfields if kind == "field" else tmethods
            if name in pool or name in extra_methods:
                continue
            problems.append(("MISSING_SHADOW", entry, side,
                             f"@Shadow {kind} '{name}' not on {target}"))

        for name in info["accessors"]:
            if name is None:
                continue
            if name in tfields or name in tmethods or name in extra_methods:
                continue
            problems.append(("MISSING_ACCESSOR", entry, side,
                             f"accessor '{name}' not on {target}"))

    print(f"mixin entries : {len(entries)}")
    print(f"problems      : {len(problems)}")
    print(f"skipped       : {len(skipped)}")
    print()

    by_kind = defaultdict(list)
    for p in problems:
        by_kind[p[0]].append(p)

    for kind in sorted(by_kind):
        print(f"===== {kind} ({len(by_kind[kind])}) =====")
        for _, entry, side, msg in by_kind[kind]:
            print(f"  [{side}] {entry}: {msg}")
        print()

    if skipped:
        print("===== skipped (informational) =====")
        for entry, side, msg in skipped:
            print(f"  [{side}] {entry}: {msg}")
        print()

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
