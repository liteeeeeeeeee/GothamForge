import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gothamforge import gamepath, safety, dialogue, chardef, tex, pak  
from gothamforge import audio, roster, model, streaks, cddef  

TOOL_DIR = Path(__file__).resolve().parent


def get_game(args):
    g = gamepath.find_game(getattr(args, "game", None))
    if not g:
        sys.exit("ERROR: could not find the LEGO Batman 2 install. Use --game <path>.")
    return g


def get_safety(game):
    return safety.Safety(game.root, TOOL_DIR)


def resolve_char(game, name):
    name = name.lower()
    exact = [p for p in game.find_chars() if p.stem.lower() == name]
    if exact:
        return exact[0]
    partial = [p for p in game.find_chars() if name in p.stem.lower()]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        sys.exit("Ambiguous name; matches: " + ", ".join(p.stem for p in partial[:20]))
    sys.exit(f"No character matching '{name}'")


def cmd_info(args):
    g = get_game(args)
    print(f"Install : {g.root}")
    print(f"Build   : {g.version.get('BuildRecordId')}  ({g.version.get('Date')})")
    print(f"Stream  : {g.version.get('AccurevStream')}")
    print(f"Chars   : {len(g.find_chars())} definition files")
    sf = get_safety(g)
    print(f"Backups : {len(sf.list())} files protected (store: {sf.store})")


def cmd_char(args):
    g = get_game(args)
    if args.action == "list":
        flt = (args.name or "").lower()
        for p in g.find_chars():
            if flt in p.stem.lower():
                print(p.stem, "  <-", p.relative_to(g.root))
        return
    path = resolve_char(g, args.name)
    cd = chardef.CharDef(path)
    if args.action == "show":
        print(f"# {cd.name()}   ({path.relative_to(g.root)})")
        print("\nFlags (abilities):")
        for f in cd.flags():
            desc = chardef.KNOWN_FLAGS.get(f, "")
            print(f"  - {f}{('   # ' + desc) if desc else ''}")
        print("\nValues:")
        for k, v in cd.values().items():
            desc = chardef.KNOWN_VALUES.get(k, "")
            print(f"  {k} = {v}{('   # ' + desc) if desc else ''}")
        print("\nAddOns:", ", ".join(cd.addons()) or "(none)")
        if cd.cd_sidecar():
            print("\nNote: a compiled .CD twin exists; it will be neutralised on save.")
        return
    sf = get_safety(g)
    sf.backup(path)
    if args.action == "set-flag":
        on = args.value.lower() in ("on", "true", "1", "yes")
        cd.set_flag(args.key, on)
        print(f"{cd.name()}: flag {args.key} -> {'ON' if on else 'OFF'}")
    elif args.action == "set-value":
        cd.set_value(args.key, args.value)
        print(f"{cd.name()}: {args.key} -> {args.value}")
    cd.save()


def cmd_dialogue(args):
    g = get_game(args)
    tt = dialogue.TextTable(g.text_csv)
    if args.action == "search":
        for i, row in tt.find(args.query, typ=args.type, lang=args.lang)[: args.limit]:
            label = row[0]
            text = tt.get(i, args.lang or "ENGLISH")
            print(f"{label}\t[{row[2] if len(row) > 2 else '?'}]\t{text}")
        return
    if args.action == "set":
        i = tt.find_by_label(args.query)
        if i is None:
            sys.exit(f"No string with LABEL '{args.query}'")
        sf = get_safety(g)
        sf.backup(g.text_csv)
        tt.set(i, args.lang, args.text)
        tt.save()
        print(f"Set {args.query} [{args.lang}] -> {args.text}")


def cmd_tex(args):
    g = get_game(args)
    if args.action == "info":
        print(tex.read_info(args.file))
    elif args.action == "topng":
        tex.to_png(args.file, args.out)
        print(f"Wrote {args.out}")
    elif args.action == "todds":
        out = args.out or str(Path(args.file).with_suffix(".dds"))
        tex.to_dds(args.file, out)
        print(f"Wrote {out}")
    elif args.action == "import":
        target = Path(args.target)
        sf = get_safety(g)
        if target.exists():
            sf.backup(target)
            res = tex.encode_to_tex(args.image, target, match=target)
        else:
            res = tex.encode_to_tex(args.image, target)
        print(f"Imported {args.image} -> {target.name}: {res}")


def cmd_pak(args):
    if args.action == "list":
        info = pak.list_entries(args.file)
        print(f"{info['found']} textures (header declares {info['declared_count']}):")
        for e in info["entries"]:
            print(f"  {e['index']:3d}  {e['name']:<40} {e['size']:>8} bytes")
    elif args.action == "extract":
        info = pak.extract_all(args.file, args.out)
        print(f"Extracted {info['found']} textures to {args.out}")


def cmd_audio(args):
    g = get_game(args)
    if args.action == "ogg-list":
        for p in audio.list_ogg(g):
            if (args.name or "").lower() in p.name.lower():
                print(p.relative_to(g.root))
    elif args.action == "banks":
        for b in audio.list_banks(g):
            print(b.name)
    elif args.action == "bank-list":
        bank = audio.Bank(g.root / "AUDIO" / args.name)
        for e in bank.entries:
            if (args.key or "").lower() in e["name"].lower():
                print(f"{e['index']:5d}  {e['kind'].upper():4}  {e['size']:>8}  {e['name']}")
    elif args.action == "extract":
        bank = audio.Bank(g.root / "AUDIO" / args.name)
        hits = bank.find(args.key)
        if not hits:
            sys.exit("no entry matches " + args.key)
        e = hits[0]
        out = args.value or (Path(e["name"]).stem + (".wav" if e["kind"] == "wav" else ".cbx"))
        bank.extract(e, out)
        print("extracted", out)
    elif args.action == "decode":
        bank = audio.Bank(g.root / "AUDIO" / args.name)
        dec = audio.find_cbxdecoder(g)
        if not dec:
            sys.exit("CBXDecoder.exe not found")
        hits = bank.find(args.key)
        if not hits:
            sys.exit("no entry matches " + args.key)
        out = audio.extract_and_decode(bank, hits[0], args.value or ".", dec)
        print("wrote", out)
    elif args.action == "set-filetype":
        sc = audio.SamplesCfg(g.root / "AUDIO" / "SAMPLES.CFG")
        get_safety(g).backup(sc.path)
        if sc.set_filetype(args.name, (args.key or "WAV").upper()):
            sc.save()
            print(f"{args.name} -> FileType {(args.key or 'WAV').upper()}")
        else:
            sys.exit("sample not found")


def cmd_roster(args):
    g = get_game(args)
    coll = roster.Collection(g.chars_dir / "COLLECTION.TXT")
    if args.action == "list":
        for e in coll.entries():
            ca = e["cost"] if e["cost"] is not None else (e["area"] or "")
            print(f"{e['name']:<24} {e['method']:<14} {ca}")
        return
    get_safety(g).backup(coll.path)
    if args.action == "set-cost":
        coll.set_cost(args.name, int(args.value))
    elif args.action == "free":
        coll.make_free(args.name)
    elif args.action == "free-all":
        for e in coll.entries():
            if e["method"] == "buy_in_shop":
                coll.make_free(e["name"])
    coll.save()
    print("saved COLLECTION.TXT")


def cmd_model(args):
    g = get_game(args)
    p = Path(args.file)
    p = p if p.exists() else g.root / args.file
    gm = model.GhgModel(p)
    if args.action == "info":
        d = gm.summary()
        print(f"{d['file']}: {d['bytes']:,} bytes  v{d['version']} {d['root']}  id {d['file_id']}")
        print(f"built by {d['build_user']} on {d['build_date']}")
        if d["source_path"]:
            print("source:", d["source_path"])
        print("attributes:", ", ".join(d["attributes"]))
        print(f"embedded textures: {len(gm.embedded_textures())}")
        print(f"mesh parts ({len(d['mesh_parts'])}):", ", ".join(d["mesh_parts"][:20]))
        print(f"texture refs ({len(d['texture_refs'])}):", ", ".join(d["texture_refs"][:15]))
    elif args.action == "textures":
        out = args.out or "model_textures"
        written = gm.export_textures(out, as_png=True)
        print(f"exported {len(gm.embedded_textures())} texture(s) ({len(written)} files) to {out}")
    elif args.action in ("mesh", "obj"):
        exe = model.find_extractor(g)
        if not exe:
            sys.exit("ExtractNxgMESH.exe not found")
        nm = model.NxgMesh(p, exe)
        if nm.error:
            sys.exit(nm.error)
        if args.action == "mesh":
            bb = (nm.points.max(0) - nm.points.min(0)).round(3) if len(nm.points) else None
            print(f"{p.name}: {len(nm.points):,} vertices, {len(nm.faces):,} faces, "
                  f"{nm.vertex_lists} parts kept / {nm.parts}, bbox extent {bb}")
        else:
            out = args.out or (p.stem + ".obj")
            nm.to_obj(out)
            print(f"exported {len(nm.points):,} verts / {len(nm.faces):,} faces -> {out}")


def cmd_streaks(args):
    g = get_game(args)
    if args.action == "list":
        for p in streaks.find_streak_chars(g):
            print(p.stem)
        return
    path = resolve_char(g, args.name)
    sf = streaks.StreakFile(path)
    n = sf.named()
    print(f"# {path.stem}")
    if n:
        print("named streak:", n["name"])
    for fs in sf.flying():
        print(f"  FlyingStreak #{fs['idx']} loc{fs['loc']} width {fs['width']} "
              f"rgba=({fs['r']},{fs['g']},{fs['b']},{fs['a']})")


def cmd_cheats(args):
    g = get_game(args)
    coll = roster.Collection(g.chars_dir / "COLLECTION.TXT")
    if args.action == "list":
        for e in coll.entries():
            if e["cheat_code"] or not args.coded:
                only = " [code-only]" if e["cheat_code_only"] else ""
                print(f"{e['name']:<26} {e['cheat_code'] or '-':<10}{only}")
        return
    get_safety(g).backup(coll.path)
    if args.action == "set-code":
        coll.set_cheat_code(args.name, args.value)
        print(f"{args.name}: cheat_code -> {args.value}")
    elif args.action == "remove-code":
        coll.set_cheat_code(args.name, None)
        coll.set_cheat_code_only(args.name, False)
        print(f"{args.name}: cheat_code removed")
    coll.save()


def _decode_layer(bits, val):
    return ", ".join(name for name, mask in bits if val & mask) or "(none)"


def cmd_colors(args):
    g = get_game(args)
    path = resolve_char(g, args.name)
    cd = path.with_suffix(".CD")
    if not cd.exists():
        sys.exit(f"{path.stem} has no .CD (no part materials to recolour)")
    cf = cddef.CdFile(cd)
    if args.action == "list":
        colours = cddef.LegoColours(g)
        for m in cf.materials():
            rgb = colours.rgb(m["name"]) if m["kind"] == "colour" else None
            print(f"  {m['index']:2d}  {m['kind']:7}  {m['name']}{('  rgb=' + str(rgb)) if rgb else ''}")
    elif args.action == "set":
        get_safety(g).backup(cd)
        if cf.set_colour(int(args.a), args.b):
            cf.save()
            print(f"{path.stem}: part #{args.a} -> {args.b}")
        else:
            sys.exit("edit failed (safety check)")
    elif args.action == "layers":
        L = cf.layers()
        if not L:
            sys.exit(f"{path.stem} has no editable minifig layers")
        print(f"byte1=0x{L['byte1']:02X}  body:   {_decode_layer(cddef.LAYER_BYTE1, L['byte1'])}")
        print(f"byte2=0x{L['byte2']:02X}  legs:   {_decode_layer(cddef.LAYER_BYTE2, L['byte2'])}")
        print(f"byte3=0x{L['byte3']:02X}  access: {_decode_layer(cddef.LAYER_BYTE3, L['byte3'])}")
    elif args.action == "set-layers":
        get_safety(g).backup(cd)
        b1, b2, b3 = (int(x, 16) for x in (args.a, args.b, args.c))
        if cf.set_layers(b1, b2, b3):
            cf.save()
            print(f"{path.stem}: layers -> 0x{b1:02X} 0x{b2:02X} 0x{b3:02X}")
        else:
            sys.exit("no layer block found")
    elif args.action == "heads":
        slots = cf.head_materials()
        if not slots:
            sys.exit(f"{path.stem} has no head slot")
        for m in slots:
            print(f"  slot #{m['index']}  current: {m['name']}")
        heads = sorted(cddef.head_catalogue(g))
        print(f"\n{len(heads)} heads available, e.g.: {', '.join(heads[:8])} ...")
    elif args.action == "set-head":
        slots = cf.head_materials()
        if not slots:
            sys.exit(f"{path.stem} has no head slot")
        slot = int(args.b) if args.b else slots[0]["index"]
        get_safety(g).backup(cd)
        if cf.set_material(slot, args.a):
            cf.save()
            print(f"{path.stem}: head slot #{slot} -> {args.a}")
        else:
            sys.exit("edit failed (safety check)")


def cmd_backup(args):
    g = get_game(args)
    sf = get_safety(g)
    for rel, meta in sf.list().items():
        flag = "" if meta.get("existed") else "  (was newly created)"
        print(f"  {rel}{flag}")
    if not sf.list():
        print("  (no backups yet)")


def cmd_restore(args):
    g = get_game(args)
    sf = get_safety(g)
    if sf.restore(args.relpath):
        print(f"Restored {args.relpath}")
    else:
        sys.exit("No such backup")


def cmd_restore_all(args):
    g = get_game(args)
    sf = get_safety(g)
    n = sf.restore_all()
    print(f"Restored {n} files to their originals")


def build_parser():
    p = argparse.ArgumentParser(prog="gf", description="GothamForge - LEGO Batman 2 mod toolkit")
    p.add_argument("--game", help="path to the game install (auto-detected if omitted)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("info").set_defaults(func=cmd_info)

    c = sub.add_parser("char", help="view/edit character abilities")
    c.add_argument("action", choices=["list", "show", "set-flag", "set-value"])
    c.add_argument("name", nargs="?", default="")
    c.add_argument("key", nargs="?")
    c.add_argument("value", nargs="?")
    c.set_defaults(func=cmd_char)

    d = sub.add_parser("dialogue", help="search/edit text & subtitles")
    d.add_argument("action", choices=["search", "set"])
    d.add_argument("query")
    d.add_argument("--lang", default="ENGLISH")
    d.add_argument("--type", dest="type", default=None)
    d.add_argument("--limit", type=int, default=50)
    d.add_argument("text", nargs="?")
    d.set_defaults(func=cmd_dialogue)

    t = sub.add_parser("tex", help="texture conversion / import")
    t.add_argument("action", choices=["info", "topng", "todds", "import"])
    t.add_argument("file", nargs="?")
    t.add_argument("out", nargs="?")
    t.add_argument("image", nargs="?")
    t.add_argument("target", nargs="?")
    t.set_defaults(func=cmd_tex)

    k = sub.add_parser("pak", help="inspect/extract .PAK archives")
    k.add_argument("action", choices=["list", "extract"])
    k.add_argument("file")
    k.add_argument("out", nargs="?", default="extracted")
    k.set_defaults(func=cmd_pak)

    a = sub.add_parser("audio", help="OGG / sound banks / CBX / SAMPLES.CFG")
    a.add_argument("action", choices=["ogg-list", "banks", "bank-list", "extract", "decode", "set-filetype"])
    a.add_argument("name", nargs="?", help="bank file, sample name, or filter")
    a.add_argument("key", nargs="?", help="entry filter / filetype")
    a.add_argument("value", nargs="?", help="output path/dir")
    a.set_defaults(func=cmd_audio)

    r2 = sub.add_parser("roster", help="view/edit COLLECTION.TXT unlocks")
    r2.add_argument("action", choices=["list", "set-cost", "free", "free-all"])
    r2.add_argument("name", nargs="?")
    r2.add_argument("value", nargs="?")
    r2.set_defaults(func=cmd_roster)

    mp = sub.add_parser("model", help="inspect / extract a .GHG model")
    mp.add_argument("action", choices=["info", "textures", "mesh", "obj"])
    mp.add_argument("file")
    mp.add_argument("out", nargs="?", help="output dir for 'textures' / file for 'obj'")
    mp.set_defaults(func=cmd_model)

    st = sub.add_parser("streaks", help="view character flight-trail streaks")
    st.add_argument("action", choices=["list", "show"])
    st.add_argument("name", nargs="?")
    st.set_defaults(func=cmd_streaks)

    ch = sub.add_parser("cheats", help="view/edit Batcomputer unlock codes (COLLECTION.TXT)")
    ch.add_argument("action", nargs="?", choices=["list", "set-code", "remove-code"], default="list")
    ch.add_argument("name", nargs="?")
    ch.add_argument("value", nargs="?")
    ch.add_argument("--coded", action="store_true", help="only entries that have a code")
    ch.set_defaults(func=cmd_cheats)

    co = sub.add_parser("colors", help="view/edit character part colours & visibility (.CD)")
    co.add_argument("action", choices=["list", "set", "layers", "set-layers", "heads", "set-head"])
    co.add_argument("name")
    co.add_argument("a", nargs="?", help="material index / byte1 (hex) / HEAD name")
    co.add_argument("b", nargs="?", help="LEGO colour name / byte2 (hex) / head slot index")
    co.add_argument("c", nargs="?", help="byte3 (hex) for set-layers")
    co.set_defaults(func=cmd_colors)

    sub.add_parser("backup", help="list protected files").set_defaults(func=cmd_backup)
    r = sub.add_parser("restore", help="restore one file")
    r.add_argument("relpath")
    r.set_defaults(func=cmd_restore)
    sub.add_parser("restore-all", help="restore every modified file").set_defaults(func=cmd_restore_all)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if getattr(args, "cmd", None) == "tex" and args.action == "import":
        if args.image is None and args.out is not None:
            args.image, args.target = args.file, args.out
    args.func(args)


if __name__ == "__main__":
    main()
