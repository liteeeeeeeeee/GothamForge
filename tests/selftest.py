import sys
import shutil
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gothamforge import gamepath, safety, dialogue, chardef, tex, pak 
from gothamforge import audio, roster, model  
from gothamforge import playback, streaks, cddef 
import soundfile as _sf  
from PIL import Image 
import numpy as np 

WORK = ROOT / "work"
PASS, FAIL = [], []


def ok(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}{(' - ' + extra) if extra else ''}")


def main():
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)

    print("\n== 1. Locate game ==")
    game = gamepath.find_game()
    ok("find_game()", game is not None and game.is_valid)
    if not game:
        print("  cannot continue without game")
        return 1
    print(f"     root  : {game.root}")
    print(f"     build : {game.version.get('BuildRecordId')} ({game.version.get('Date')})")
    chars = game.find_chars()
    ok("character .TXT files found", len(chars) > 100, f"{len(chars)} files")

    print("\n== 2. Character abilities (.TXT) ==")
    ww = game.chars_dir / "MINIFIGS" / "WONDERWOMAN" / "WONDERWOMAN.TXT"
    cd = chardef.CharDef(ww)
    ok("parse name", cd.name() == "WONDERWOMAN", repr(cd.name()))
    ok("flag detect super_strength", cd.has_flag("super_strength"))
    ok("value detect hit_points", cd.get_value("hit_points") == "4", repr(cd.get_value("hit_points")))
    ok("addons listed", "FlyingHandlerAddon" in cd.addons(), str(cd.addons()))
    cww = WORK / "WONDERWOMAN.TXT"
    shutil.copyfile(ww, cww)
    cd2 = chardef.CharDef(cww)
    cd2.set_value("hit_points", 99)
    cd2.set_flag("super_strength", False)
    cd2.set_flag("can_fly_test_flag", True)
    cd2.save()
    cd3 = chardef.CharDef(cww)
    ok("edit hit_points", cd3.get_value("hit_points") == "99")
    ok("remove flag", not cd3.has_flag("super_strength"))
    ok("add flag", cd3.has_flag("can_fly_test_flag"))
    import difflib
    orig = ww.read_text(encoding="latin-1").split("\n")
    new = cww.read_text(encoding="latin-1").split("\n")
    ops = [d for d in difflib.ndiff(orig, new) if d[0] in "+-"]
    ok("targeted edit (only touched lines change)", len(ops) <= 5, f"{len(ops)} +/- diff lines")
    cd.cd_sidecar()  

    print("\n== 3. Dialogue (TEXT.CSV) ==")
    tt = dialogue.TextTable(game.text_csv)
    ok("CSV header has languages", "ENGLISH" in tt.header and len(tt.languages()) >= 10,
       f"{len(tt.languages())} langs")
    ok("rows parsed", len(tt.rows) > 1000, f"{len(tt.rows)} rows")
    subs = tt.find(typ="Subtitle")
    ok("subtitle filter", len(subs) > 100, f"{len(subs)} subtitles")
    hits = tt.find("Kryptonite", lang="ENGLISH")
    ok("text search", len(hits) > 0, f"{len(hits)} matches for 'Kryptonite'")
    ccsv = WORK / "TEXT.CSV"
    shutil.copyfile(game.text_csv, ccsv)
    tt2 = dialogue.TextTable(ccsv)
    n0 = len(tt2.rows)
    i = tt2.find("Kryptonite", lang="ENGLISH")[0][0]
    tt2.set(i, "ENGLISH", "GOTHAMFORGE TEST LINE")
    tt2.save()
    tt3 = dialogue.TextTable(ccsv)
    ok("CSV row count preserved", len(tt3.rows) == n0, f"{n0} -> {len(tt3.rows)}")
    ok("CSV edit persisted", tt3.get(i, "ENGLISH") == "GOTHAMFORGE TEST LINE")

    print("\n== 4. Textures (.TEX <-> DDS/PNG, DXT re-encode) ==")
    sample = game.icons_dir / "SUPERMAN_NXG.TEX"
    info = tex.read_info(sample)
    ok("read TEX header", info["fourcc"] in ("DXT1", "DXT5") and info["nu2t"],
       f"{info['width']}x{info['height']} {info['fourcc']} nu2t={info['nu2t']}")
    png = WORK / "superman.png"
    tex.to_png(sample, png)
    ok("TEX -> PNG", png.exists() and Image.open(png).size == (info["width"], info["height"]))
    newtex = WORK / "superman_new.TEX"
    res = tex.encode_to_tex(png, newtex, match=sample)
    ok("PNG -> TEX encode", res["format"] == info["fourcc"] and res["size"] == (info["width"], info["height"]),
       str(res))
    ni = tex.read_info(newtex)
    ok("re-encoded TEX valid header", ni["nu2t"] and ni["fourcc"] == info["fourcc"] and ni["mipcount"] >= 1)
    rt = Image.open(newtex, formats=["DDS"]).convert("RGBA")
    ok("re-encoded TEX decodes", rt.size == (info["width"], info["height"]))
    grad = Image.fromarray(
        np.dstack([
            np.tile(np.linspace(0, 255, 64, dtype=np.uint8), (64, 1)),
            np.tile(np.linspace(0, 255, 64, dtype=np.uint8)[:, None], (1, 64)),
            np.full((64, 64), 128, np.uint8),
            np.full((64, 64), 255, np.uint8),
        ])
    )
    gtex = WORK / "grad.TEX"
    tex.encode_to_tex(grad, gtex, fmt="DXT1")
    dec = np.asarray(Image.open(gtex, formats=["DDS"]).convert("RGB")).astype(int)
    err = np.abs(dec - np.asarray(grad.convert("RGB")).astype(int)).mean()
    ok("DXT1 encode quality (mean err < 12)", err < 12, f"mean abs err={err:.2f}")
    rgba = np.zeros((32, 32, 4), np.uint8)
    rgba[..., 0] = 200
    rgba[..., 3] = np.tile(np.linspace(0, 255, 32, dtype=np.uint8), (32, 1))
    a_tex = WORK / "alpha.TEX"
    tex.encode_to_tex(Image.fromarray(rgba), a_tex, fmt="DXT5")
    adec = np.asarray(Image.open(a_tex, formats=["DDS"]).convert("RGBA"))[..., 3].astype(int)
    aerr = np.abs(adec - rgba[..., 3].astype(int)).mean()
    ok("DXT5 alpha round-trip (err < 12)", aerr < 12, f"alpha err={aerr:.2f}")

    print("\n== 5. PAK archive (extract) ==")
    pk = game.icons_pak
    ok("is_pak()", pak.is_pak(pk))
    listing = pak.list_entries(pk)
    ok("entry count matches header", listing["declared_count"] == listing["found"],
       f"declared={listing['declared_count']} found={listing['found']}")
    first = listing["entries"][0]["name"]
    one = WORK / "from_pak.tex"
    pak.extract_one(pk, first, one)
    ok("extract one entry is valid DDS", one.read_bytes()[:4] == b"DDS ", f"first='{first}'")

    print("\n== 6. Safety (backup / restore) ==")
    sandbox = WORK / "game_sandbox"
    (sandbox / "CHARS").mkdir(parents=True)
    (sandbox / "GAMEVERSION.TXT").write_text("BuildRecordId: 0")
    target = sandbox / "CHARS" / "x.txt"
    target.write_text("original")
    sf = safety.Safety(sandbox, WORK / "store")
    sf.backup(target)
    target.write_text("MODIFIED")
    ok("detects modification", sf.is_modified(target) is True)
    sf.restore(sf.rel(target))
    ok("restore brings original back", target.read_text() == "original")
    newf = sandbox / "CHARS" / "created.txt"
    sf.backup(newf)            
    newf.write_text("new mod")
    sf.restore(sf.rel(newf))   
    ok("restore deletes newly-created file", not newf.exists())

    print("\n== 7. Audio (OGG / banks / CBX / SAMPLES.CFG) ==")
    oggs = audio.list_ogg(game)
    ok("OGG tracks found", len(oggs) > 100, f"{len(oggs)} ogg")
    banks = audio.list_banks(game)
    ok("sound banks found", len(banks) >= 2, f"{[b.name for b in banks]}")
    bank = audio.Bank(game.root / "AUDIO" / "RESTSFX_PC.PAC")
    nwav = sum(1 for e in bank.entries if e["kind"] == "wav")
    ncbx = sum(1 for e in bank.entries if e["kind"] == "cbx")
    ok("bank parses all entries", len(bank.entries) == bank.count, f"{len(bank.entries)}/{bank.count}")
    ok("bank classifies wav+cbx", nwav > 100 and ncbx > 100, f"wav={nwav} cbx={ncbx}")
    wav_entry = next(e for e in bank.entries if e["kind"] == "wav")
    we = WORK / "bank_wav.wav"
    bank.extract(wav_entry, we)
    ok("extract WAV entry", we.read_bytes()[:4] == b"RIFF")
    dec = audio.find_cbxdecoder(game)
    if dec:
        cbx_entry = next(e for e in bank.entries if e["kind"] == "cbx")
        try:
            out = audio.extract_and_decode(bank, cbx_entry, WORK / "cbxout", dec)
            ok("CBX -> WAV decode", out.exists() and out.read_bytes()[:4] == b"RIFF", out.name)
        except Exception as e:
            ok("CBX -> WAV decode", False, str(e))
    else:
        print("  [skip] CBXDecoder.exe not found")
    scfg_src = game.root / "AUDIO" / "SAMPLES.CFG"
    scfg = WORK / "SAMPLES.CFG"
    shutil.copyfile(scfg_src, scfg)
    sc = audio.SamplesCfg(scfg)
    samps = sc.samples()
    ok("SAMPLES.CFG parsed", len(samps) > 500, f"{len(samps)} samples")
    cbx_samp = next(s for s in samps if s["filetype"].upper() == "CBX")
    sc.set_filetype(cbx_samp["name"], "WAV")
    sc.save()
    ok("flip FileType CBX->WAV", audio.SamplesCfg(scfg).find(cbx_samp["name"])["filetype"].upper() == "WAV",
       cbx_samp["name"])

    print("\n== 8. Roster / collection ==")
    coll_src = game.chars_dir / "COLLECTION.TXT"
    coll = WORK / "COLLECTION.TXT"
    shutil.copyfile(coll_src, coll)
    c = roster.Collection(coll)
    ents = c.entries()
    ok("collection parsed", len(ents) > 30, f"{len(ents)} entries")
    buyers = [e for e in ents if e["method"] == "buy_in_shop"]
    ok("detects buy_in_shop + cost", buyers and buyers[0]["cost"] > 0,
       f"{buyers[0]['name']}={buyers[0]['cost']}" if buyers else "none")
    target = buyers[0]["name"]
    c.set_cost(target, 1)
    c.make_free("Joker")
    c.save()
    c2 = roster.Collection(coll)
    ok("edit cost", c2.find(target)["cost"] == 1)
    ok("make free (story)", c2.find("Joker")["method"] == "story")
    cdata = roster.CharData(game.chars_dir / "CHARDATA.TXT")
    ok("chardata registry read", len(cdata.registered()) > 50, f"{len(cdata.registered())} registered")

    print("\n== 9. Model inspector (GHG) ==")
    ghg = game.chars_dir / "MINIFIGS" / "CLAYFACE" / "CLAYFACE_NXG.GHG"
    gm = model.GhgModel(ghg)
    s = gm.summary()
    ok("GHG header parsed", s["root"] == "NU20" and s["version"] == 1, f"id={s['file_id']} root={s['root']}")
    ok("build provenance", bool(s["build_user"] and s["build_date"]), f"{s['build_user']} {s['build_date']}")
    ok("mesh parts extracted", len(s["mesh_parts"]) > 0, str(s["mesh_parts"][:4]))
    ok("vertex attributes detected", "POSITION" in s["attributes"], str(s["attributes"]))
    pc = gm.point_cloud()
    ok("point-cloud preview (experimental)", len(pc) > 0, f"{len(pc)} pts")
    emb = gm.embedded_textures()
    ok("embedded textures detected", len(emb) >= 1, f"{len(emb)} embedded")
    wrote = gm.export_textures(WORK / "modeltex", as_png=True)
    ok("export model textures", any(p.suffix == ".tex" and p.read_bytes()[:4] == b"DDS " for p in wrote),
       f"{len(wrote)} files")
    exe = model.find_extractor(game)
    if exe:
        nm = model.NxgMesh(game.chars_dir / "CREATURES" / "CHICKEN" / "CHICKEN_NXG.GHG", exe)
        ext = (nm.points.max(0) - nm.points.min(0)).max() if len(nm.points) else 0
        ok("accurate mesh extraction", len(nm.points) > 2000 and 0 < ext < 5,
           f"{len(nm.points)} verts, extent {ext:.2f}")
        ok("triangle reconstruction", len(nm.faces) > 2000 and nm.faces.max() < len(nm.points),
           f"{len(nm.faces)} faces")
        v, fc = nm.points, nm.faces
        diag = float(np.linalg.norm(v.max(0) - v.min(0)))
        elen = np.linalg.norm(v[fc[:, 0]] - v[fc[:, 1]], axis=1)
        ok("mesh topology sane (few long edges)", (elen > 0.25 * diag).mean() < 0.02,
           f"{(elen > 0.25 * diag).mean() * 100:.1f}% long edges")
        obj = WORK / "chicken.obj"
        nm.to_obj(obj)
        ok("OBJ export", obj.exists() and obj.read_text().count("\nf ") > 2000)
        img = model.render_mesh(nm.points, nm.faces, 0.6, 0.4)
        ok("solid render produces image", (img != [16, 16, 20]).any(2).sum() > 5000,
           f"{(img != [16, 16, 20]).any(2).sum()} lit px")
    else:
        print("  [skip] ExtractNxgMESH.exe not found")

    print("\n== 10. Audio playback (decode pipeline) ==")
    ok("playback backend available", playback.available(), str(playback.backends()))
    ogg = audio.list_ogg(game)[0]
    data, sr = _sf.read(str(ogg), dtype="int16", always_2d=True)
    if data.shape[1] > 2:
        data = data[:, :2]
    tmpwav = WORK / "decoded_preview.wav"
    _sf.write(str(tmpwav), data[:sr], sr, subtype="PCM_16")  
    ok("OGG decodes to playable WAV", tmpwav.read_bytes()[:4] == b"RIFF", f"{ogg.name} sr={sr}")

    print("\n== 11. Streak / flight-trail colours ==")
    sc_chars = streaks.find_streak_chars(game)
    ok("streak characters found", len(sc_chars) > 20, f"{len(sc_chars)} chars")
    sww = WORK / "WW_streaks.TXT"
    shutil.copyfile(game.chars_dir / "MINIFIGS" / "WONDERWOMAN" / "WONDERWOMAN.TXT", sww)
    sf = streaks.StreakFile(sww)
    fly = sf.flying()
    ok("FlyingStreak entries parsed", len(fly) >= 3, f"{len(fly)} streaks")
    sf.set_flying(fly[0]["line"], 10, 20, 30, a=200)
    sf.save()
    again = streaks.StreakFile(sww).flying()[0]
    ok("edit streak colour", (again["r"], again["g"], again["b"], again["a"]) == (10, 20, 30, 200),
       str((again["r"], again["g"], again["b"], again["a"])))

    print("\n== 12. Cheat codes (COLLECTION.TXT) ==")
    ccoll = WORK / "COLLECTION_cc.TXT"
    shutil.copyfile(game.chars_dir / "COLLECTION.TXT", ccoll)
    cc = roster.Collection(ccoll)
    coded = [e for e in cc.entries() if e["cheat_code"]]
    ok("cheat codes parsed", len(coded) >= 5, f"{len(coded)} coded entries")
    ok("known code present", any(e["cheat_code"] == "V9SAGT" for e in coded))
    cc.set_cheat_code("LexBot", "ABC123")
    cc.set_cheat_code("Batman", "NEWHERO")
    cc.save()
    cc2 = roster.Collection(ccoll)
    ok("edit existing code", cc2.find("LexBot")["cheat_code"] == "ABC123")
    ok("add code keeps unlock", cc2.find("Batman")["cheat_code"] == "NEWHERO"
       and cc2.find("Batman")["method"] == "story")

    print("\n== 13. Part colours (.CD materials) ==")
    cols = cddef.LegoColours(game)
    ok("LEGO colours read", len(cols.names()) >= 40, f"{len(cols.names())} colours")
    ok("colour RGB read", cols.rgb("LEGO_BLACK") == (0, 0, 0), str(cols.rgb("LEGO_BLACK")))
    ccd = WORK / "BATMAN.CD"
    shutil.copyfile(game.chars_dir / "MINIFIGS" / "BATMAN" / "BATMAN.CD", ccd)
    cf = cddef.CdFile(ccd)
    mats = cf.materials()
    ok("CD materials parsed", len(mats) >= 8, f"{len(mats)} materials")
    colour_mats = [m for m in mats if m["kind"] == "colour"]
    ok("colour materials found", len(colour_mats) >= 1, f"{len(colour_mats)} colour mats")
    target = colour_mats[0]["index"]
    ok("recolour part (validated splice)", cf.set_colour(target, "LEGO_BRIGHTRED"))
    cf.save()
    ok("recolour persisted", cddef.CdFile(ccd).materials()[target]["name"] == "LEGO_BRIGHTRED")

    print("\n== 14. Part visibility (CD layer bytes) ==")
    minis = sorted((game.chars_dir / "MINIFIGS").rglob("*.CD"))
    found = sum(1 for p in minis if cddef.CdFile(p).layers())
    ok("layer block located on most minifigs", found > len(minis) * 0.85, f"{found}/{len(minis)}")
    lcd = WORK / "ROBIN.CD"
    shutil.copyfile(game.chars_dir / "MINIFIGS" / "ROBIN" / "ROBIN.CD", lcd)
    lf = cddef.CdFile(lcd)
    L0 = lf.layers()
    ok("read layer bytes", L0 and L0["byte1"] == 0xBF, str(L0))
    ok("set_layers (no size change)", lf.set_layers(0xDF, 0x03, 0x0C))
    lf.save()
    L1 = cddef.CdFile(lcd).layers()
    ok("layers persisted main+cutscene",
       (L1["byte1"], L1["byte2"], L1["byte3"]) == (0xDF, 0x03, 0x0C), str(L1))
    ok("CD size unchanged by layer edit",
       lcd.stat().st_size == (game.chars_dir / "MINIFIGS" / "ROBIN" / "ROBIN.CD").stat().st_size)

    print("\n== 15. Face / head swapper ==")
    heads = cddef.head_catalogue(game)
    ok("head catalogue", len(heads) > 30, f"{len(heads)} heads")
    hcd = WORK / "BATMAN.CD"
    shutil.copyfile(game.chars_dir / "MINIFIGS" / "BATMAN" / "BATMAN.CD", hcd)
    hf = cddef.CdFile(hcd)
    slots = hf.head_materials()
    ok("head slot detected", len(slots) >= 1 and "head" in slots[0]["path"].lower(), str(slots[:1]))
    ok("swap head", hf.set_material(slots[0]["index"], "HEAD_JOKER_FRONT"))
    hf.save()
    ok("head swap persisted",
       cddef.CdFile(hcd).head_materials()[0]["name"] == "HEAD_JOKER_FRONT")

    print("\n== 16. Vehicle stats editor ==")
    vehs = game.find_vehicles()
    ok("vehicles found", len(vehs) > 50, f"{len(vehs)} vehicles")
    bm = next((p for p in vehs if p.stem == "BATMOBILE"), vehs[0])
    vcopy = WORK / "BATMOBILE.TXT"
    shutil.copyfile(bm, vcopy)
    vd = chardef.CharDef(vcopy)
    ok("vehicle flags parsed", "vehicle" in vd.flags(), str(list(vd.flags())[:5]))
    ok("vehicle stats parsed", "run_speed" in vd.values(), f"run_speed={vd.values().get('run_speed')}")
    vd.set_value("run_speed", 20)
    vd.set_flag("respawn", True)
    vd.save()
    vd2 = chardef.CharDef(vcopy)
    ok("vehicle edit persisted", vd2.get_value("run_speed") == "20" and vd2.has_flag("respawn"))

    print(f"\n==== {len(PASS)} passed, {len(FAIL)} failed ====")
    if FAIL:
        print("FAILED:", ", ".join(FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
