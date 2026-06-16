import sys
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gothamforge import gamepath, safety, dialogue, chardef, tex, pak  
from gothamforge import audio, roster, model  
from gothamforge import playback, streaks, cddef  
from tkinter import colorchooser  
import shutil  
import numpy as np  

TOOL_DIR = Path(__file__).resolve().parent

try:
    from PIL import Image, ImageTk
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GothamForge - LEGO Batman 2 Mod Studio")
        self.geometry("1240x740")
        self.minsize(900, 600)

        self.game = gamepath.find_game()
        if not self.game:
            self._prompt_for_game()
        if not self.game:
            messagebox.showerror("GothamForge", "No game install selected. Exiting.")
            self.destroy()
            return
        self.safety = safety.Safety(self.game.root, TOOL_DIR)
        self._preview_ref = None  
        self._tmp = TOOL_DIR / "work"
        self._tmp.mkdir(parents=True, exist_ok=True)

        self._build_menu()
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        self._build_dashboard()
        self._build_abilities()
        self._build_vehicles()
        self._build_dialogue()
        self._build_textures()
        self._build_audio()
        self._build_roster()
        self._build_model()
        self._build_cheats()
        self._build_colors()
        self._build_streaks()
        self._build_archives()
        self._build_backups()

    def _prompt_for_game(self):
        messagebox.showinfo("GothamForge", "Select your 'LEGO Batman 2' install folder.")
        d = filedialog.askdirectory(title="Select LEGO Batman 2 folder")
        if d:
            g = gamepath.find_game(d)
            self.game = g

    def _build_menu(self):
        m = tk.Menu(self)
        fm = tk.Menu(m, tearoff=0)
        fm.add_command(label="Change game folder...", command=self._change_game)
        fm.add_separator()
        fm.add_command(label="Restore ALL (undo every mod)", command=self.restore_all)
        fm.add_separator()
        fm.add_command(label="Exit", command=self.destroy)
        m.add_cascade(label="File", menu=fm)
        hm = tk.Menu(m, tearoff=0)
        hm.add_command(label="About", command=lambda: messagebox.showinfo(
            "About GothamForge",
            "GothamForge 1.0\nA modding toolkit for LEGO Batman 2: DC Super Heroes.\n\n"
            "Edits dialogue, abilities, textures & icons.\nEvery change is backed up; "
            "use File -> Restore ALL to undo."))
        m.add_cascade(label="Help", menu=hm)
        self.config(menu=m)

    def _change_game(self):
        d = filedialog.askdirectory(title="Select LEGO Batman 2 folder")
        if d:
            g = gamepath.find_game(d)
            if g:
                self.game = g
                self.safety = safety.Safety(g.root, TOOL_DIR)
                messagebox.showinfo("GothamForge", f"Now using:\n{g.root}")
                self.refresh_all()
            else:
                messagebox.showerror("GothamForge", "That folder is not a LEGO Batman 2 install.")

    def report(self, e):
        traceback.print_exc()
        messagebox.showerror("GothamForge - error", str(e))

    def refresh_all(self):
        try:
            self._fill_dashboard()
            self._fill_char_list()
            self._fill_texture_list()
            self._fill_backups()
        except Exception as e:
            self.report(e)

    def _build_dashboard(self):
        f = ttk.Frame(self.nb, padding=16)
        self.nb.add(f, text="Dashboard")
        self.dash = tk.Text(f, height=14, wrap="word", relief="flat",
                            background=self.cget("background"))
        self.dash.pack(fill="x")
        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=10)
        ttk.Button(bar, text="Restore ALL (undo every mod)", command=self.restore_all).pack(side="left")
        ttk.Button(bar, text="Change game folder...", command=self._change_game).pack(side="left", padx=8)
        ttk.Button(bar, text="Refresh", command=self.refresh_all).pack(side="left")
        tips = ttk.LabelFrame(f, text="Quick start", padding=10)
        tips.pack(fill="both", expand=True, pady=8)
        ttk.Label(tips, justify="left", text=(
            "Abilities  - pick a character, toggle powers / edit stats, Save.\n"
            "Dialogue   - search any line, edit it in any language, Save line.\n"
            "Textures   - browse icons/skins, Export to PNG, paint, Import to swap.\n"
            "Archives   - open ICONS_TEX.PAK to list / extract packed textures.\n"
            "Backups    - see every file you changed and restore individually.\n\n"
            "Safety: the original of every file you touch is copied first. Nothing\n"
            "here launches the game; it only edits files on disk.")).pack(anchor="w")
        self._fill_dashboard()

    def _fill_dashboard(self):
        g = self.game
        self.dash.config(state="normal")
        self.dash.delete("1.0", "end")
        self.dash.insert("end", "GothamForge - LEGO Batman 2 Mod Studio\n\n", ("h",))
        self.dash.insert("end", f"Install : {g.root}\n")
        self.dash.insert("end", f"Build   : {g.version.get('BuildRecordId')}  ({g.version.get('Date')})\n")
        self.dash.insert("end", f"Stream  : {g.version.get('AccurevStream')}\n")
        self.dash.insert("end", f"Chars   : {len(g.find_chars())} character definitions\n")
        self.dash.insert("end", f"Backups : {len(self.safety.list())} files protected\n")
        if not HAVE_PIL:
            self.dash.insert("end", "\n[!] Pillow not available - texture previews/convert disabled.\n")
        self.dash.tag_config("h", font=("Segoe UI", 13, "bold"))
        self.dash.config(state="disabled")

    def restore_all(self):
        if messagebox.askyesno("Restore ALL", "Undo every change and restore all original files?"):
            try:
                n = self.safety.restore_all()
                messagebox.showinfo("GothamForge", f"Restored {n} files.")
                self.refresh_all()
            except Exception as e:
                self.report(e)

    def _build_abilities(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text="Abilities")
        left = ttk.Frame(f)
        left.pack(side="left", fill="y")
        ttk.Label(left, text="Character:").pack(anchor="w")
        self.char_search = tk.StringVar()
        e = ttk.Entry(left, textvariable=self.char_search)
        e.pack(fill="x")
        e.bind("<KeyRelease>", lambda _e: self._fill_char_list())
        self.char_list = tk.Listbox(left, width=34, height=34, exportselection=False)
        self.char_list.pack(fill="y", expand=True, pady=4)
        self.char_list.bind("<<ListboxSelect>>", self._on_char_select)

        right = ttk.Frame(f)
        right.pack(side="left", fill="both", expand=True, padx=8)
        self.char_title = ttk.Label(right, text="Select a character", font=("Segoe UI", 12, "bold"))
        self.char_title.pack(anchor="w")

        panes = ttk.Frame(right)
        panes.pack(fill="both", expand=True)
        fl = ttk.LabelFrame(panes, text="Abilities (toggle on/off)", padding=4)
        fl.pack(side="left", fill="both", expand=True)
        self.flag_canvas = tk.Canvas(fl, borderwidth=0, width=320)
        fsb = ttk.Scrollbar(fl, orient="vertical", command=self.flag_canvas.yview)
        self.flag_inner = ttk.Frame(self.flag_canvas)
        self.flag_inner.bind("<Configure>", lambda _e: self.flag_canvas.configure(
            scrollregion=self.flag_canvas.bbox("all")))
        self.flag_canvas.create_window((0, 0), window=self.flag_inner, anchor="nw")
        self.flag_canvas.configure(yscrollcommand=fsb.set)
        self.flag_canvas.pack(side="left", fill="both", expand=True)
        fsb.pack(side="right", fill="y")

        vr = ttk.LabelFrame(panes, text="Stats / values", padding=4)
        vr.pack(side="left", fill="both", expand=True, padx=6)
        self.value_canvas = tk.Canvas(vr, borderwidth=0, width=260)
        vsb = ttk.Scrollbar(vr, orient="vertical", command=self.value_canvas.yview)
        self.value_inner = ttk.Frame(self.value_canvas)
        self.value_inner.bind("<Configure>", lambda _e: self.value_canvas.configure(
            scrollregion=self.value_canvas.bbox("all")))
        self.value_canvas.create_window((0, 0), window=self.value_inner, anchor="nw")
        self.value_canvas.configure(yscrollcommand=vsb.set)
        self.value_canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        bottom = ttk.Frame(right)
        bottom.pack(fill="x", pady=6)
        ttk.Label(bottom, text="Add flag:").pack(side="left")
        self.new_flag = tk.StringVar()
        ttk.Entry(bottom, textvariable=self.new_flag, width=22).pack(side="left", padx=4)
        ttk.Button(bottom, text="Add", command=self._add_flag).pack(side="left")
        ttk.Button(bottom, text="Save character", command=self._save_char).pack(side="right")
        self.addon_label = ttk.Label(right, text="")
        self.addon_label.pack(anchor="w")

        self.flag_vars = {}
        self.value_vars = {}
        self.current_char = None
        self._fill_char_list()

    def _fill_char_list(self):
        flt = self.char_search.get().lower()
        self._chars = [p for p in self.game.find_chars() if flt in p.stem.lower()]
        self.char_list.delete(0, "end")
        for p in self._chars:
            self.char_list.insert("end", p.stem)

    def _on_char_select(self, _e=None):
        sel = self.char_list.curselection()
        if not sel:
            return
        path = self._chars[sel[0]]
        self.current_char = path
        try:
            cd = chardef.CharDef(path)
        except Exception as e:
            return self.report(e)
        self.char_title.config(text=f"{cd.name() or path.stem}   ({path.relative_to(self.game.root)})")
        for w in self.flag_inner.winfo_children():
            w.destroy()
        for w in self.value_inner.winfo_children():
            w.destroy()
        self.flag_vars = {}
        self.value_vars = {}
        present = set(cd.flags())
        ordered = sorted(present) + [f for f in chardef.KNOWN_FLAGS if f not in present]
        for name in ordered:
            var = tk.BooleanVar(value=name in present)
            self.flag_vars[name] = var
            txt = name
            desc = chardef.KNOWN_FLAGS.get(name)
            cb = ttk.Checkbutton(self.flag_inner, text=txt, variable=var)
            cb.pack(anchor="w")
            if desc:
                self._tip(cb, desc)
        for k, v in cd.values().items():
            row = ttk.Frame(self.value_inner)
            row.pack(fill="x", pady=1)
            ttk.Label(row, text=k, width=20).pack(side="left")
            var = tk.StringVar(value=v)
            self.value_vars[k] = var
            ttk.Entry(row, textvariable=var, width=10).pack(side="left")
            d = chardef.KNOWN_VALUES.get(k)
            if d:
                ttk.Label(row, text=d, foreground="#888").pack(side="left", padx=4)
        self.addon_label.config(text="AddOns: " + (", ".join(cd.addons()) or "(none)"))

    def _add_flag(self):
        name = self.new_flag.get().strip()
        if not name or name in self.flag_vars:
            return
        var = tk.BooleanVar(value=True)
        self.flag_vars[name] = var
        ttk.Checkbutton(self.flag_inner, text=name, variable=var).pack(anchor="w")
        self.new_flag.set("")

    def _save_char(self):
        if not self.current_char:
            return
        try:
            self.safety.backup(self.current_char)
            cd = chardef.CharDef(self.current_char)
            for name, var in self.flag_vars.items():
                cd.set_flag(name, var.get())
            for k, var in self.value_vars.items():
                cd.set_value(k, var.get())
            cd.save()
            self._fill_dashboard()
            messagebox.showinfo("GothamForge", f"Saved {cd.name()}.")
        except Exception as e:
            self.report(e)

    def _tip(self, widget, text):
        def enter(_e):
            self._tipwin = tw = tk.Toplevel(widget)
            tw.wm_overrideredirect(True)
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + 20
            tw.wm_geometry(f"+{x}+{y}")
            tk.Label(tw, text=text, background="#ffffe0", relief="solid", borderwidth=1,
                     justify="left", wraplength=280).pack()

        def leave(_e):
            w = getattr(self, "_tipwin", None)
            if w:
                w.destroy()
                self._tipwin = None
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def _build_vehicles(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text="Vehicles")
        left = ttk.Frame(f)
        left.pack(side="left", fill="y")
        ttk.Label(left, text="Vehicle:").pack(anchor="w")
        self.veh_q = tk.StringVar()
        e = ttk.Entry(left, textvariable=self.veh_q)
        e.pack(fill="x")
        e.bind("<KeyRelease>", lambda _e: self._veh_fill_list())
        self.veh_list = tk.Listbox(left, width=30, height=34, exportselection=False)
        self.veh_list.pack(fill="y", expand=True, pady=4)
        self.veh_list.bind("<<ListboxSelect>>", self._veh_pick)

        right = ttk.Frame(f)
        right.pack(side="left", fill="both", expand=True, padx=8)
        self.veh_title = ttk.Label(right, text="Select a vehicle", font=("Segoe UI", 12, "bold"))
        self.veh_title.pack(anchor="w")
        panes = ttk.Frame(right)
        panes.pack(fill="both", expand=True)
        flf = ttk.LabelFrame(panes, text="Flags (toggle on/off)", padding=4)
        flf.pack(side="left", fill="both", expand=True)
        self.veh_flag_canvas = tk.Canvas(flf, borderwidth=0, width=320)
        fsb = ttk.Scrollbar(flf, orient="vertical", command=self.veh_flag_canvas.yview)
        self.veh_flag_inner = ttk.Frame(self.veh_flag_canvas)
        self.veh_flag_inner.bind("<Configure>", lambda _e: self.veh_flag_canvas.configure(
            scrollregion=self.veh_flag_canvas.bbox("all")))
        self.veh_flag_canvas.create_window((0, 0), window=self.veh_flag_inner, anchor="nw")
        self.veh_flag_canvas.configure(yscrollcommand=fsb.set)
        self.veh_flag_canvas.pack(side="left", fill="both", expand=True)
        fsb.pack(side="right", fill="y")
        vrf = ttk.LabelFrame(panes, text="Stats / values", padding=4)
        vrf.pack(side="left", fill="both", expand=True, padx=6)
        self.veh_val_canvas = tk.Canvas(vrf, borderwidth=0, width=300)
        vsb = ttk.Scrollbar(vrf, orient="vertical", command=self.veh_val_canvas.yview)
        self.veh_val_inner = ttk.Frame(self.veh_val_canvas)
        self.veh_val_inner.bind("<Configure>", lambda _e: self.veh_val_canvas.configure(
            scrollregion=self.veh_val_canvas.bbox("all")))
        self.veh_val_canvas.create_window((0, 0), window=self.veh_val_inner, anchor="nw")
        self.veh_val_canvas.configure(yscrollcommand=vsb.set)
        self.veh_val_canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        bottom = ttk.Frame(right)
        bottom.pack(fill="x", pady=6)
        ttk.Label(bottom, text="Add flag:").pack(side="left")
        self.veh_new_flag = tk.StringVar()
        ttk.Entry(bottom, textvariable=self.veh_new_flag, width=22).pack(side="left", padx=4)
        ttk.Button(bottom, text="Add", command=self._veh_add_flag).pack(side="left")
        ttk.Button(bottom, text="Save vehicle", command=self._veh_save).pack(side="right")
        self.veh_flag_vars = {}
        self.veh_val_vars = {}
        self.current_veh = None
        self.after(80, self._veh_lazylist)

    def _veh_lazylist(self):
        self._veh_all = self.game.find_vehicles()
        self._veh_fill_list()

    def _veh_fill_list(self):
        flt = self.veh_q.get().lower()
        self._vehs = [p for p in getattr(self, "_veh_all", []) if flt in p.stem.lower()]
        self.veh_list.delete(0, "end")
        for p in self._vehs:
            self.veh_list.insert("end", p.stem)

    def _veh_pick(self, _e=None):
        s = self.veh_list.curselection()
        if not s:
            return
        path = self._vehs[s[0]]
        self.current_veh = path
        try:
            cd = chardef.CharDef(path)
        except Exception as e:
            return self.report(e)
        self.veh_title.config(text=f"{cd.name() or path.stem}   ({path.relative_to(self.game.root)})")
        for w in self.veh_flag_inner.winfo_children():
            w.destroy()
        for w in self.veh_val_inner.winfo_children():
            w.destroy()
        self.veh_flag_vars = {}
        self.veh_val_vars = {}
        present = set(cd.flags())
        ordered = sorted(present) + [f for f in chardef.VEHICLE_FLAGS if f not in present]
        for name in ordered:
            var = tk.BooleanVar(value=name in present)
            self.veh_flag_vars[name] = var
            cb = ttk.Checkbutton(self.veh_flag_inner, text=name, variable=var)
            cb.pack(anchor="w")
            desc = chardef.VEHICLE_FLAGS.get(name)
            if desc:
                self._tip(cb, desc)
        for k, v in cd.values().items():
            row = ttk.Frame(self.veh_val_inner)
            row.pack(fill="x", pady=1)
            ttk.Label(row, text=k, width=18).pack(side="left")
            var = tk.StringVar(value=v)
            self.veh_val_vars[k] = var
            ttk.Entry(row, textvariable=var, width=10).pack(side="left")
            desc = chardef.VEHICLE_VALUES.get(k)
            if desc:
                ttk.Label(row, text=desc, foreground="#888").pack(side="left", padx=4)

    def _veh_add_flag(self):
        name = self.veh_new_flag.get().strip()
        if not name or name in self.veh_flag_vars:
            return
        var = tk.BooleanVar(value=True)
        self.veh_flag_vars[name] = var
        ttk.Checkbutton(self.veh_flag_inner, text=name, variable=var).pack(anchor="w")
        self.veh_new_flag.set("")

    def _veh_save(self):
        if not self.current_veh:
            return
        try:
            self.safety.backup(self.current_veh)
            cd = chardef.CharDef(self.current_veh)
            for name, var in self.veh_flag_vars.items():
                cd.set_flag(name, var.get())
            for k, var in self.veh_val_vars.items():
                cd.set_value(k, var.get())
            cd.save()
            self._fill_dashboard()
            messagebox.showinfo("GothamForge", f"Saved {cd.name()}.")
        except Exception as e:
            self.report(e)

    def _build_dialogue(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text="Dialogue")
        top = ttk.Frame(f)
        top.pack(fill="x")
        ttk.Label(top, text="Search:").pack(side="left")
        self.dlg_q = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.dlg_q, width=30)
        ent.pack(side="left", padx=4)
        ent.bind("<Return>", lambda _e: self._dlg_search())
        ttk.Label(top, text="Type:").pack(side="left")
        self.dlg_type = tk.StringVar(value="All")
        self.dlg_type_cb = ttk.Combobox(top, textvariable=self.dlg_type, width=12, state="readonly")
        self.dlg_type_cb.pack(side="left", padx=4)
        ttk.Label(top, text="Language:").pack(side="left")
        self.dlg_lang = tk.StringVar(value="ENGLISH")
        self.dlg_lang_cb = ttk.Combobox(top, textvariable=self.dlg_lang, width=14, state="readonly")
        self.dlg_lang_cb.pack(side="left", padx=4)
        self.dlg_lang_cb.bind("<<ComboboxSelected>>", lambda _e: self._dlg_search())
        ttk.Button(top, text="Search", command=self._dlg_search).pack(side="left", padx=4)

        cols = ("label", "type", "text")
        self.dlg_tree = ttk.Treeview(f, columns=cols, show="headings", height=16)
        for c, w in zip(cols, (260, 90, 640)):
            self.dlg_tree.heading(c, text=c.title())
            self.dlg_tree.column(c, width=w, anchor="w")
        self.dlg_tree.pack(fill="both", expand=True, pady=6)
        self.dlg_tree.bind("<<TreeviewSelect>>", self._dlg_pick)

        edit = ttk.LabelFrame(f, text="Edit selected line", padding=6)
        edit.pack(fill="x")
        self.dlg_edit = tk.Text(edit, height=4, wrap="word")
        self.dlg_edit.pack(fill="x")
        ttk.Button(edit, text="Save line", command=self._dlg_save).pack(anchor="e", pady=4)

        self.tt = None
        self._dlg_loaded_for = None
        self.after(50, self._dlg_lazyload)

    def _dlg_lazyload(self):
        try:
            self._ensure_text_table()
            self.dlg_lang_cb["values"] = self.tt.languages()
            self.dlg_type_cb["values"] = ["All"] + self.tt.types()
            self._dlg_search()
        except Exception as e:
            self.report(e)

    def _dlg_search(self):
        if not self.tt:
            return
        typ = None if self.dlg_type.get() == "All" else self.dlg_type.get()
        lang = self.dlg_lang.get()
        self.dlg_tree.delete(*self.dlg_tree.get_children())
        for i, row in self.tt.find(self.dlg_q.get(), typ=typ)[:1000]:
            self.dlg_tree.insert("", "end", iid=str(i),
                                 values=(row[0], row[2] if len(row) > 2 else "",
                                         self.tt.get(i, lang)))

    def _dlg_pick(self, _e=None):
        sel = self.dlg_tree.selection()
        if not sel:
            return
        i = int(sel[0])
        self.dlg_edit.delete("1.0", "end")
        self.dlg_edit.insert("end", self.tt.get(i, self.dlg_lang.get()))

    def _dlg_save(self):
        sel = self.dlg_tree.selection()
        if not sel or not self.tt:
            return
        i = int(sel[0])
        try:
            self.safety.backup(self.game.text_csv)
            self.tt.set(i, self.dlg_lang.get(), self.dlg_edit.get("1.0", "end-1c"))
            self.tt.save()
            self._dlg_search()
            self._fill_dashboard()
            messagebox.showinfo("GothamForge", f"Saved line {self.tt.label(i)} [{self.dlg_lang.get()}].")
        except Exception as e:
            self.report(e)

    def _build_textures(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text="Textures")
        left = ttk.Frame(f)
        left.pack(side="left", fill="y")
        ttk.Label(left, text="Search texture:").pack(anchor="w")
        self.tex_q = tk.StringVar()
        e = ttk.Entry(left, textvariable=self.tex_q)
        e.pack(fill="x")
        e.bind("<KeyRelease>", lambda _e: self._fill_texture_list())
        self.tex_list = tk.Listbox(left, width=40, height=32, exportselection=False)
        self.tex_list.pack(fill="y", expand=True, pady=4)
        self.tex_list.bind("<<ListboxSelect>>", self._tex_pick)

        right = ttk.Frame(f)
        right.pack(side="left", fill="both", expand=True, padx=8)
        self.tex_info = ttk.Label(right, text="Select a texture", font=("Segoe UI", 11, "bold"))
        self.tex_info.pack(anchor="w")
        self.tex_preview = ttk.Label(right)
        self.tex_preview.pack(pady=10)
        btns = ttk.Frame(right)
        btns.pack(anchor="w")
        ttk.Button(btns, text="Export PNG...", command=self._tex_export_png).pack(side="left")
        ttk.Button(btns, text="Export DDS...", command=self._tex_export_dds).pack(side="left", padx=6)
        ttk.Button(btns, text="Import image (swap)...", command=self._tex_import).pack(side="left")
        ttk.Label(right, foreground="#888", text=(
            "Import accepts PNG/JPG/DDS and re-encodes to the original's DXT format\n"
            "and size, with mipmaps. The original is backed up automatically.")).pack(anchor="w", pady=8)
        self._fill_texture_list()

    def _fill_texture_list(self):
        flt = self.tex_q.get().lower()
        allt = self.game.find_textures()
        self._texs = [p for p in allt if flt in p.name.lower()][:4000]
        self.tex_list.delete(0, "end")
        for p in self._texs:
            self.tex_list.insert("end", p.name)

    def _tex_pick(self, _e=None):
        sel = self.tex_list.curselection()
        if not sel:
            return
        path = self._texs[sel[0]]
        self.current_tex = path
        try:
            info = tex.read_info(path)
            self.tex_info.config(text=f"{path.name}   {info['width']}x{info['height']}  {info['fourcc']}")
            if HAVE_PIL:
                img = tex.to_image(path)
                img.thumbnail((320, 320))
                self._preview_ref = ImageTk.PhotoImage(img)
                self.tex_preview.config(image=self._preview_ref)
        except Exception as e:
            self.report(e)

    def _tex_export_png(self):
        if not getattr(self, "current_tex", None):
            return
        out = filedialog.asksaveasfilename(defaultextension=".png",
                                           initialfile=self.current_tex.stem + ".png")
        if out:
            try:
                tex.to_png(self.current_tex, out)
                messagebox.showinfo("GothamForge", f"Exported PNG:\n{out}")
            except Exception as e:
                self.report(e)

    def _tex_export_dds(self):
        if not getattr(self, "current_tex", None):
            return
        out = filedialog.asksaveasfilename(defaultextension=".dds",
                                           initialfile=self.current_tex.stem + ".dds")
        if out:
            try:
                tex.to_dds(self.current_tex, out)
                messagebox.showinfo("GothamForge", f"Exported DDS:\n{out}")
            except Exception as e:
                self.report(e)

    def _tex_import(self):
        if not getattr(self, "current_tex", None):
            return
        src = filedialog.askopenfilename(title="Choose replacement image",
                                         filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.dds *.tga"),
                                                    ("All", "*.*")])
        if not src:
            return
        try:
            self.safety.backup(self.current_tex)
            if src.lower().endswith(".dds"):
                res = tex.import_dds_as_tex(src, self.current_tex)
            else:
                res = tex.encode_to_tex(src, self.current_tex, match=self.current_tex)
            self._tex_pick()
            self._fill_dashboard()
            messagebox.showinfo("GothamForge", f"Swapped {self.current_tex.name}\n{res}")
        except Exception as e:
            self.report(e)

    def _build_archives(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text="Archives")
        top = ttk.Frame(f)
        top.pack(fill="x")
        self.pak_path = tk.StringVar(value=str(self.game.icons_pak))
        ttk.Entry(top, textvariable=self.pak_path, width=70).pack(side="left", padx=4)
        ttk.Button(top, text="Browse...", command=self._pak_browse).pack(side="left")
        ttk.Button(top, text="List", command=self._pak_list).pack(side="left", padx=4)
        ttk.Button(top, text="Extract all...", command=self._pak_extract).pack(side="left")

        cols = ("idx", "name", "size")
        self.pak_tree = ttk.Treeview(f, columns=cols, show="headings", height=24)
        for c, w in zip(cols, (60, 520, 120)):
            self.pak_tree.heading(c, text=c.title())
            self.pak_tree.column(c, width=w)
        self.pak_tree.pack(fill="both", expand=True, pady=6)

    def _pak_browse(self):
        p = filedialog.askopenfilename(filetypes=[("PAK archives", "*.PAK *.pak"), ("All", "*.*")])
        if p:
            self.pak_path.set(p)

    def _pak_list(self):
        try:
            info = pak.list_entries(self.pak_path.get())
            self.pak_tree.delete(*self.pak_tree.get_children())
            for e in info["entries"]:
                self.pak_tree.insert("", "end", values=(e["index"], e["name"], e["size"]))
        except Exception as e:
            self.report(e)

    def _pak_extract(self):
        out = filedialog.askdirectory(title="Extract textures to...")
        if out:
            try:
                info = pak.extract_all(self.pak_path.get(), out)
                messagebox.showinfo("GothamForge", f"Extracted {info['found']} textures to:\n{out}")
            except Exception as e:
                self.report(e)

    def _build_audio(self):
        f = ttk.Frame(self.nb, padding=6)
        self.nb.add(f, text="Audio")
        inner = ttk.Notebook(f)
        inner.pack(fill="both", expand=True)
        self._build_audio_ogg(inner)
        self._build_audio_banks(inner)
        self._build_audio_samples(inner)

    def _build_audio_ogg(self, nb):
        f = ttk.Frame(nb, padding=6)
        nb.add(f, text="Music / OGG")
        left = ttk.Frame(f)
        left.pack(side="left", fill="y")
        ttk.Label(left, text="Search track:").pack(anchor="w")
        self.ogg_q = tk.StringVar()
        e = ttk.Entry(left, textvariable=self.ogg_q)
        e.pack(fill="x")
        e.bind("<KeyRelease>", lambda _e: self._fill_ogg())
        self.ogg_list = tk.Listbox(left, width=44, height=28, exportselection=False)
        self.ogg_list.pack(fill="y", expand=True, pady=4)
        self.ogg_list.bind("<<ListboxSelect>>", self._ogg_pick)
        right = ttk.Frame(f)
        right.pack(side="left", fill="both", expand=True, padx=8)
        self.ogg_info = ttk.Label(right, text="Select a track", font=("Segoe UI", 11, "bold"))
        self.ogg_info.pack(anchor="w")
        b = ttk.Frame(right)
        b.pack(anchor="w", pady=8)
        ttk.Button(b, text="▶ Play", command=self._ogg_play).pack(side="left")
        ttk.Button(b, text="■ Stop", command=playback.stop).pack(side="left", padx=(4, 12))
        ttk.Button(b, text="Export OGG...", command=self._ogg_export).pack(side="left")
        ttk.Button(b, text="Replace with my OGG...", command=self._ogg_replace).pack(side="left", padx=6)
        ttk.Label(right, foreground="#888", wraplength=400, justify="left", text=(
            "Streamed music / ambience / cutscene tracks. Replace drops your own .ogg "
            "in place (original backed up). Match the sample rate for best results.")).pack(anchor="w")
        self._oggs = []
        self._fill_ogg()

    def _fill_ogg(self):
        flt = self.ogg_q.get().lower()
        self._oggs = [p for p in audio.list_ogg(self.game) if flt in p.name.lower()]
        self.ogg_list.delete(0, "end")
        for p in self._oggs:
            self.ogg_list.insert("end", f"{p.parent.name}/{p.name}")

    def _ogg_pick(self, _e=None):
        s = self.ogg_list.curselection()
        if not s:
            return
        p = self._oggs[s[0]]
        self.current_ogg = p
        self.ogg_info.config(text=f"{p.name}   {p.stat().st_size // 1024} KB")

    def _ogg_export(self):
        if not getattr(self, "current_ogg", None):
            return
        out = filedialog.asksaveasfilename(defaultextension=".ogg", initialfile=self.current_ogg.name)
        if out:
            shutil.copyfile(self.current_ogg, out)
            messagebox.showinfo("GothamForge", f"Exported {out}")

    def _ogg_replace(self):
        if not getattr(self, "current_ogg", None):
            return
        src = filedialog.askopenfilename(filetypes=[("OGG audio", "*.ogg"), ("All", "*.*")])
        if not src:
            return
        try:
            self.safety.backup(self.current_ogg)
            shutil.copyfile(src, self.current_ogg)
            self._fill_dashboard()
            messagebox.showinfo("GothamForge", f"Replaced {self.current_ogg.name}.")
        except Exception as e:
            self.report(e)

    def _build_audio_banks(self, nb):
        f = ttk.Frame(nb, padding=6)
        nb.add(f, text="Sound Banks")
        top = ttk.Frame(f)
        top.pack(fill="x")
        ttk.Label(top, text="Bank:").pack(side="left")
        self.bank_sel = tk.StringVar()
        self.bank_cb = ttk.Combobox(top, textvariable=self.bank_sel, width=22, state="readonly")
        self.bank_cb["values"] = [b.name for b in audio.list_banks(self.game)]
        self.bank_cb.pack(side="left", padx=4)
        self.bank_cb.bind("<<ComboboxSelected>>", lambda _e: self._bank_load())
        ttk.Label(top, text="Search:").pack(side="left")
        self.bank_q = tk.StringVar()
        be = ttk.Entry(top, textvariable=self.bank_q, width=24)
        be.pack(side="left", padx=4)
        be.bind("<KeyRelease>", lambda _e: self._bank_fill())
        cols = ("name", "kind", "size")
        self.bank_tree = ttk.Treeview(f, columns=cols, show="headings", height=20)
        for c, w in zip(cols, (440, 70, 100)):
            self.bank_tree.heading(c, text=c.title())
            self.bank_tree.column(c, width=w)
        self.bank_tree.pack(fill="both", expand=True, pady=6)
        b = ttk.Frame(f)
        b.pack(fill="x")
        ttk.Button(b, text="▶ Play selected", command=self._bank_play).pack(side="left")
        ttk.Button(b, text="■ Stop", command=playback.stop).pack(side="left", padx=(4, 12))
        ttk.Button(b, text="Extract selected (WAV/CBX)...", command=self._bank_extract).pack(side="left")
        ttk.Button(b, text="Decode CBX -> WAV...", command=self._bank_decode).pack(side="left", padx=6)
        ttk.Label(f, foreground="#888", text=(
            "WAV entries extract directly; CBX entries can be decoded to WAV via the "
            "bundled CBXDecoder.")).pack(anchor="w")
        self._bank = None
        vals = list(self.bank_cb["values"])
        if vals:
            self.bank_sel.set("RESTSFX_PC.PAC" if "RESTSFX_PC.PAC" in vals else vals[0])
            self.after(60, self._bank_load)

    def _bank_load(self):
        try:
            self._bank = audio.Bank(self.game.root / "AUDIO" / self.bank_sel.get())
            self._bank_fill()
        except Exception as e:
            self.report(e)

    def _bank_fill(self):
        if not self._bank:
            return
        flt = self.bank_q.get().lower()
        self.bank_tree.delete(*self.bank_tree.get_children())
        for e in self._bank.entries:
            if flt in e["name"].lower():
                self.bank_tree.insert("", "end", iid=str(e["index"]),
                                      values=(e["name"], e["kind"].upper(), e["size"]))

    def _bank_entry(self):
        s = self.bank_tree.selection()
        if not s or not self._bank:
            return None
        return self._bank.entries[int(s[0])]

    def _bank_extract(self):
        e = self._bank_entry()
        if not e:
            return
        ext = {"wav": ".wav", "cbx": ".cbx"}.get(e["kind"], ".bin")
        out = filedialog.asksaveasfilename(defaultextension=ext, initialfile=Path(e["name"]).stem + ext)
        if out:
            try:
                self._bank.extract(e, out)
                messagebox.showinfo("GothamForge", f"Extracted {out}")
            except Exception as ex:
                self.report(ex)

    def _bank_decode(self):
        e = self._bank_entry()
        if not e:
            return
        dec = audio.find_cbxdecoder(self.game)
        if not dec:
            return messagebox.showerror("GothamForge", "CBXDecoder.exe not found in the game folder.")
        outdir = filedialog.askdirectory(title="Save decoded WAV to...")
        if not outdir:
            return
        try:
            out = audio.extract_and_decode(self._bank, e, outdir, dec)
            messagebox.showinfo("GothamForge", f"Saved WAV:\n{out}")
        except Exception as ex:
            self.report(ex)

    def _build_audio_samples(self, nb):
        f = ttk.Frame(nb, padding=6)
        nb.add(f, text="Sample Config")
        top = ttk.Frame(f)
        top.pack(fill="x")
        ttk.Label(top, text="Search sample:").pack(side="left")
        self.samp_q = tk.StringVar()
        e = ttk.Entry(top, textvariable=self.samp_q, width=30)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda _e: self._samp_fill())
        ttk.Button(top, text="Search", command=self._samp_fill).pack(side="left", padx=4)
        cols = ("name", "filename", "filetype")
        self.samp_tree = ttk.Treeview(f, columns=cols, show="headings", height=18)
        for c, w in zip(cols, (220, 430, 80)):
            self.samp_tree.heading(c, text=c.title())
            self.samp_tree.column(c, width=w)
        self.samp_tree.pack(fill="both", expand=True, pady=6)
        b = ttk.Frame(f)
        b.pack(fill="x")
        ttk.Button(b, text="Set FileType WAV", command=lambda: self._samp_setft("WAV")).pack(side="left")
        ttk.Button(b, text="Set FileType CBX", command=lambda: self._samp_setft("CBX")).pack(side="left", padx=6)
        ttk.Button(b, text="Replace with my WAV...", command=self._samp_replace).pack(side="left")
        ttk.Label(f, foreground="#888", wraplength=760, justify="left", text=(
            "To use your own sound for a CBX sample: pick it, 'Replace with my WAV' - the tool "
            "drops a 16-bit WAV into Audio\\Samples\\ and flips FileType to WAV so the game plays it.")).pack(anchor="w")
        self._scfg = None
        self.after(60, self._samp_lazyload)

    def _samp_lazyload(self):
        try:
            self._scfg = audio.SamplesCfg(self.game.root / "AUDIO" / "SAMPLES.CFG")
            self._samp_fill()
        except Exception as e:
            self.report(e)

    def _samp_fill(self):
        if not self._scfg:
            return
        flt = self.samp_q.get().lower()
        self.samp_tree.delete(*self.samp_tree.get_children())
        for s in self._scfg.samples():
            if flt in s["name"].lower() or flt in s["filename"].lower():
                self.samp_tree.insert("", "end", iid=s["name"],
                                      values=(s["name"], s["filename"], s["filetype"]))
                if len(self.samp_tree.get_children()) >= 1500:
                    break

    def _samp_setft(self, ft):
        s = self.samp_tree.selection()
        if not s or not self._scfg:
            return
        try:
            self.safety.backup(self._scfg.path)
            self._scfg.set_filetype(s[0], ft)
            self._scfg.save()
            self._samp_fill()
            self._fill_dashboard()
            messagebox.showinfo("GothamForge", f"{s[0]}: FileType -> {ft}")
        except Exception as e:
            self.report(e)

    def _samp_replace(self):
        s = self.samp_tree.selection()
        if not s or not self._scfg:
            return
        samp = self._scfg.find(s[0])
        src = filedialog.askopenfilename(title="Choose replacement WAV (16-bit PCM)",
                                         filetypes=[("WAV audio", "*.wav"), ("All", "*.*")])
        if not src:
            return
        try:
            dest = audio.loose_sample_path(self.game, samp["filename"], "wav")
            dest.parent.mkdir(parents=True, exist_ok=True)
            self.safety.backup(dest)
            shutil.copyfile(src, dest)
            self.safety.backup(self._scfg.path)
            self._scfg.set_filetype(s[0], "WAV")
            self._scfg.save()
            self._samp_fill()
            self._fill_dashboard()
            messagebox.showinfo("GothamForge",
                                f"Installed WAV for {s[0]}:\n{dest}\nand set FileType -> WAV.")
        except Exception as e:
            self.report(e)

    def _build_roster(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text="Roster")
        cols = ("name", "method", "cost/area", "customiser")
        self.ros_tree = ttk.Treeview(f, columns=cols, show="headings", height=20)
        for c, w in zip(cols, (220, 140, 130, 90)):
            self.ros_tree.heading(c, text=c.title())
            self.ros_tree.column(c, width=w)
        self.ros_tree.pack(fill="both", expand=True, pady=6)
        self.ros_tree.bind("<<TreeviewSelect>>", self._ros_pick)
        edit = ttk.LabelFrame(f, text="Edit unlock", padding=8)
        edit.pack(fill="x")
        ttk.Label(edit, text="Method:").pack(side="left")
        self.ros_method = tk.StringVar(value="buy_in_shop")
        ttk.Combobox(edit, textvariable=self.ros_method, width=14, state="readonly",
                     values=["story", "buy_in_shop", "area_complete"]).pack(side="left", padx=4)
        ttk.Label(edit, text="Cost:").pack(side="left")
        self.ros_cost = tk.StringVar()
        ttk.Entry(edit, textvariable=self.ros_cost, width=10).pack(side="left", padx=4)
        self.ros_cust = tk.BooleanVar()
        ttk.Checkbutton(edit, text="customiser_parts", variable=self.ros_cust).pack(side="left", padx=6)
        ttk.Button(edit, text="Apply", command=self._ros_apply).pack(side="left", padx=6)
        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=4)
        ttk.Button(bar, text="Make selected FREE", command=self._ros_free).pack(side="left")
        ttk.Button(bar, text="Make ALL shop chars free", command=self._ros_all_free).pack(side="left", padx=6)
        self._coll = None
        self.after(60, self._ros_load)

    def _ros_load(self):
        try:
            self._ensure_collection()
            self._ros_fill()
        except Exception as e:
            self.report(e)

    def _ros_fill(self):
        self.ros_tree.delete(*self.ros_tree.get_children())
        for e in self._coll.entries():
            ca = e["cost"] if e["cost"] is not None else (e["area"] or "")
            self.ros_tree.insert("", "end", iid=e["name"],
                                 values=(e["name"], e["method"], ca, "yes" if e["customiser"] else ""))

    def _ros_pick(self, _e=None):
        s = self.ros_tree.selection()
        if not s or not self._coll:
            return
        e = self._coll.find(s[0])
        if e:
            self.ros_method.set(e["method"])
            self.ros_cost.set(str(e["cost"] if e["cost"] is not None else ""))
            self.ros_cust.set(e["customiser"])

    def _ros_apply(self):
        s = self.ros_tree.selection()
        if not s or not self._coll:
            return
        try:
            self.safety.backup(self._coll.path)
            cost = int(self.ros_cost.get()) if self.ros_cost.get().strip().isdigit() else 0
            self._coll.set_unlock(s[0], self.ros_method.get(), cost=cost, customiser=self.ros_cust.get())
            self._coll.save()
            self._ros_fill()
            self._fill_dashboard()
            messagebox.showinfo("GothamForge", f"Updated {s[0]}.")
        except Exception as e:
            self.report(e)

    def _ros_free(self):
        s = self.ros_tree.selection()
        if not s or not self._coll:
            return
        try:
            self.safety.backup(self._coll.path)
            self._coll.make_free(s[0])
            self._coll.save()
            self._ros_fill()
            messagebox.showinfo("GothamForge", f"{s[0]} is now a free story unlock.")
        except Exception as e:
            self.report(e)

    def _ros_all_free(self):
        if not self._coll:
            return
        if not messagebox.askyesno("Unlock everything", "Make every shop character a free story unlock?"):
            return
        try:
            self.safety.backup(self._coll.path)
            for e in self._coll.entries():
                if e["method"] == "buy_in_shop":
                    self._coll.make_free(e["name"])
            self._coll.save()
            self._ros_fill()
            self._fill_dashboard()
            messagebox.showinfo("GothamForge", "All shop characters set to free.")
        except Exception as e:
            self.report(e)

    def _build_model(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text="Models")
        left = ttk.Frame(f)
        left.pack(side="left", fill="y")
        ttk.Label(left, text="Search model (.GHG):").pack(anchor="w")
        self.ghg_q = tk.StringVar()
        e = ttk.Entry(left, textvariable=self.ghg_q)
        e.pack(fill="x")
        e.bind("<KeyRelease>", lambda _e: self._fill_ghg())
        self.ghg_list = tk.Listbox(left, width=34, height=30, exportselection=False)
        self.ghg_list.pack(fill="y", expand=True, pady=4)
        self.ghg_list.bind("<<ListboxSelect>>", self._ghg_pick)
        mid = ttk.Frame(f)
        mid.pack(side="left", fill="both", expand=True, padx=8)
        self.ghg_info = tk.Text(mid, width=44, wrap="word")
        self.ghg_info.pack(fill="both", expand=True)
        rp = ttk.Frame(f)
        rp.pack(side="left", fill="y")
        ttk.Label(rp, foreground="#888", justify="center",
                  text="Shaded model - drag to rotate").pack()
        self.ghg_canvas = tk.Canvas(rp, width=340, height=340, background="#101014", highlightthickness=0)
        self.ghg_canvas.pack(pady=4)
        self.ghg_canvas.bind("<Button-1>", self._ghg_rotate_start)
        self.ghg_canvas.bind("<B1-Motion>", self._ghg_rotate)
        self.ghg_canvas.bind("<ButtonRelease-1>", self._ghg_rotate_end)
        self.ghg_mesh_lbl = ttk.Label(rp, foreground="#888", text="")
        self.ghg_mesh_lbl.pack()
        bb = ttk.Frame(rp)
        bb.pack(pady=6)
        ttk.Button(bb, text="Export .OBJ...", command=self._ghg_export_obj).pack(side="left")
        ttk.Button(bb, text="Export textures...", command=self._ghg_export_tex).pack(side="left", padx=4)
        self._ghg_pts = None
        self._ghg_faces = None
        self._cur_mesh = None
        self._yaw, self._pitch = 0.6, 0.4
        self._ghg_img = None
        self._cur_ghg = None
        self._mesh_exe = model.find_extractor(self.game)
        self._fill_ghg()

    def _fill_ghg(self):
        flt = self.ghg_q.get().lower()
        allg = sorted((p for p in self.game.root.rglob("*.GHG")), key=lambda p: p.name.lower())
        self._ghgs = [p for p in allg if flt in p.name.lower()][:3000]
        self.ghg_list.delete(0, "end")
        for p in self._ghgs:
            self.ghg_list.insert("end", p.name)

    def _ghg_pick(self, _e=None):
        s = self.ghg_list.curselection()
        if not s:
            return
        try:
            path = self._ghgs[s[0]]
            self._cur_ghg = model.GhgModel(path)
            gm = self._cur_ghg
            d = gm.summary()
            emb = gm.embedded_textures()
            t = self.ghg_info
            t.delete("1.0", "end")
            t.insert("end", f"{d['file']}\n", ("h",))
            t.insert("end", f"{d['bytes']:,} bytes   id {d['file_id']}   v{d['version']} {d['root']}\n")
            t.insert("end", f"built by {d['build_user']} on {d['build_date']}\n")
            if d["source_path"]:
                t.insert("end", f"source: {d['source_path']}\n")
            t.insert("end", f"\nVertex attributes: {', '.join(d['attributes'])}\n")
            t.insert("end", f"\nEmbedded textures ({len(emb)}):\n")
            for e2 in emb:
                t.insert("end", f"  - {e2['width']}x{e2['height']} {e2['fourcc']}\n")
            t.insert("end", f"\nMesh parts ({len(d['mesh_parts'])}):\n")
            for m in d["mesh_parts"][:40]:
                t.insert("end", f"  - {m}\n")
            t.insert("end", f"\nTexture refs ({len(d['texture_refs'])}):\n")
            for r in d["texture_refs"][:30]:
                t.insert("end", f"  - {r}\n")
            t.tag_config("h", font=("Segoe UI", 12, "bold"))
            self._cur_mesh = None
            self._ghg_faces = None
            if self._mesh_exe:
                nm = model.NxgMesh(path, self._mesh_exe)
                if len(nm.points):
                    self._cur_mesh = nm
                    self._ghg_pts = nm.points
                    self._ghg_faces = nm.faces
                    self.ghg_mesh_lbl.config(
                        text=f"{len(nm.points):,} verts - {len(nm.faces):,} faces (accurate)")
                else:
                    self._ghg_pts = gm.point_cloud()
                    self.ghg_mesh_lbl.config(text=f"{len(self._ghg_pts):,} pts (heuristic)")
            else:
                self._ghg_pts = gm.point_cloud()
                self.ghg_mesh_lbl.config(text=f"{len(self._ghg_pts):,} pts (heuristic; extractor not found)")
            self._yaw, self._pitch = 0.6, 0.4
            self._ghg_render_points()                 
            self.after(20, self._ghg_show)            
        except Exception as e:
            self.report(e)

    def _ghg_export_obj(self):
        if not getattr(self, "_cur_mesh", None) or not len(self._cur_mesh.faces):
            return messagebox.showinfo("GothamForge", "No reconstructed mesh to export "
                                       "(needs ExtractNxgMESH; some models don't decode).")
        out = filedialog.asksaveasfilename(defaultextension=".obj",
                                           initialfile=self._cur_ghg.path.stem + ".obj")
        if not out:
            return
        try:
            self._cur_mesh.to_obj(out)
            messagebox.showinfo("GothamForge", f"Exported mesh:\n{out}\n"
                                f"({len(self._cur_mesh.points):,} verts, {len(self._cur_mesh.faces):,} faces)")
        except Exception as e:
            self.report(e)

    def _ghg_export_tex(self):
        if not self._cur_ghg:
            return
        emb = self._cur_ghg.embedded_textures()
        if not emb:
            return messagebox.showinfo("GothamForge", "This model has no embedded textures "
                                       "(it references external .TEX files instead).")
        out = filedialog.askdirectory(title="Export model textures to...")
        if not out:
            return
        try:
            written = self._cur_ghg.export_textures(out, as_png=True)
            messagebox.showinfo("GothamForge", f"Exported {len(emb)} texture(s) "
                                f"({len(written)} files incl. PNG) to:\n{out}")
        except Exception as e:
            self.report(e)

    def _ghg_rotate_start(self, ev):
        self._drag = (ev.x, ev.y, self._yaw, self._pitch)

    def _ghg_rotate(self, ev):
        if not hasattr(self, "_drag"):
            return
        x0, y0, y, p = self._drag
        self._yaw = y + (ev.x - x0) * 0.01
        self._pitch = p + (ev.y - y0) * 0.01
        self._ghg_render_points()        

    def _ghg_rotate_end(self, _ev=None):
        self._ghg_render_solid()         

    def _ghg_show(self):
        if self._ghg_faces is not None and len(self._ghg_faces):
            self._ghg_render_solid()
        else:
            self._ghg_render_points()

    def _ghg_render_points(self):
        c = self.ghg_canvas
        c.delete("all")
        if self._ghg_pts is None or len(self._ghg_pts) == 0 or not HAVE_PIL:
            c.create_text(170, 170, text="(no preview)", fill="#666")
            return
        W = H = 340
        pts = self._ghg_pts - self._ghg_pts.mean(0)
        pts = pts / (float(np.abs(pts).max()) or 1.0)
        cy, sy = np.cos(self._yaw), np.sin(self._yaw)
        cp, sp = np.cos(self._pitch), np.sin(self._pitch)
        r = pts @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]).T @ \
            np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]]).T
        xs = ((r[:, 0] * 0.42 + 0.5) * W).astype(int)
        ys = ((-r[:, 1] * 0.42 + 0.5) * H).astype(int)
        img = np.empty((H, W, 3), np.uint8)
        img[:] = (16, 16, 20)
        ok = (xs >= 0) & (xs < W) & (ys >= 0) & (ys < H)
        dn = (r[:, 2] - r[:, 2].min()) / ((r[:, 2].max() - r[:, 2].min()) or 1)
        shade = (70 + 170 * dn).astype(np.uint8)
        img[ys[ok], xs[ok], 0] = shade[ok]
        img[ys[ok], xs[ok], 1] = shade[ok]
        img[ys[ok], xs[ok], 2] = 255
        self._ghg_img = ImageTk.PhotoImage(Image.fromarray(img, "RGB"))
        c.create_image(0, 0, anchor="nw", image=self._ghg_img)
        c.create_text(40, 12, text="rotating...", fill="#999")

    def _ghg_render_solid(self):
        c = self.ghg_canvas
        c.delete("all")
        if self._ghg_pts is None or len(self._ghg_pts) == 0 or not HAVE_PIL:
            c.create_text(170, 170, text="(no preview)", fill="#666")
            return
        faces = self._ghg_faces if self._ghg_faces is not None else np.zeros((0, 3), int)
        img = model.render_mesh(self._ghg_pts, faces, self._yaw, self._pitch, 340, 340)
        self._ghg_img = ImageTk.PhotoImage(Image.fromarray(img, "RGB"))
        c.create_image(0, 0, anchor="nw", image=self._ghg_img)

    def _ogg_play(self):
        if not getattr(self, "current_ogg", None):
            return
        try:
            playback.play(self.current_ogg, self._tmp)
        except Exception as e:
            self.report(e)

    def _bank_play(self):
        e = self._bank_entry()
        if not e:
            return
        try:
            dec = audio.find_cbxdecoder(self.game)
            wav = audio.extract_and_decode(self._bank, e, self._tmp, dec)
            playback.play(wav, self._tmp)
        except Exception as ex:
            self.report(ex)

    def _ensure_text_table(self):
        if getattr(self, "tt", None) is None:
            self.tt = dialogue.TextTable(self.game.text_csv)
        return self.tt

    def _ensure_collection(self):
        if getattr(self, "_coll", None) is None:
            self._coll = roster.Collection(self.game.chars_dir / "COLLECTION.TXT")
        return self._coll

    def _build_cheats(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text="Cheats")
        top = ttk.Frame(f)
        top.pack(fill="x")
        ttk.Label(top, text="Search:").pack(side="left")
        self.cc_q = tk.StringVar()
        e = ttk.Entry(top, textvariable=self.cc_q, width=26)
        e.pack(side="left", padx=4)
        e.bind("<KeyRelease>", lambda _e: self._cc_fill())
        self.cc_only_coded = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="only entries with a code", variable=self.cc_only_coded,
                        command=self._cc_fill).pack(side="left", padx=8)
        ttk.Label(top, foreground="#888",
                  text="Batcomputer unlock codes (in COLLECTION.TXT).").pack(side="left", padx=8)
        cols = ("name", "code", "unlock", "only")
        self.cc_tree = ttk.Treeview(f, columns=cols, show="headings", height=16)
        for c, w, t in zip(cols, (240, 120, 160, 80),
                           ("Character / vehicle", "Cheat code", "Unlock", "Code-only")):
            self.cc_tree.heading(c, text=t)
            self.cc_tree.column(c, width=w)
        self.cc_tree.pack(fill="both", expand=True, pady=6)
        self.cc_tree.bind("<<TreeviewSelect>>", self._cc_pick)
        edit = ttk.LabelFrame(f, text="Edit cheat code", padding=8)
        edit.pack(fill="x")
        ttk.Label(edit, text="Code:").pack(side="left")
        self.cc_code = tk.StringVar()
        ttk.Entry(edit, textvariable=self.cc_code, width=14).pack(side="left", padx=4)
        self.cc_only = tk.BooleanVar()
        ttk.Checkbutton(edit, text="unlockable only by code", variable=self.cc_only).pack(side="left", padx=8)
        ttk.Button(edit, text="Apply", command=self._cc_apply).pack(side="left", padx=6)
        ttk.Button(edit, text="Remove code", command=self._cc_remove).pack(side="left")
        self.after(60, self._cc_load)

    def _cc_load(self):
        try:
            self._ensure_collection()
            self._cc_fill()
        except Exception as e:
            self.report(e)

    def _cc_fill(self):
        if not getattr(self, "_coll", None):
            return
        flt = self.cc_q.get().lower()
        self.cc_tree.delete(*self.cc_tree.get_children())
        for e in self._coll.entries():
            if self.cc_only_coded.get() and not e["cheat_code"]:
                continue
            if flt and flt not in e["name"].lower() and flt not in (e["cheat_code"] or "").lower():
                continue
            unlock = f"buy {e['cost']}" if e["method"] == "buy_in_shop" else (e["method"] or "")
            self.cc_tree.insert("", "end", iid=e["name"],
                                values=(e["name"], e["cheat_code"] or "", unlock,
                                        "yes" if e["cheat_code_only"] else ""))

    def _cc_pick(self, _e=None):
        s = self.cc_tree.selection()
        if not s or not self._coll:
            return
        e = self._coll.find(s[0])
        if e:
            self.cc_code.set(e["cheat_code"] or "")
            self.cc_only.set(e["cheat_code_only"])

    def _cc_apply(self):
        s = self.cc_tree.selection()
        if not s or not self._coll:
            return
        try:
            self.safety.backup(self._coll.path)
            self._coll.set_cheat_code(s[0], self.cc_code.get().strip())
            self._coll.set_cheat_code_only(s[0], self.cc_only.get())
            self._coll.save()
            self._cc_fill()
            self._fill_dashboard()
            messagebox.showinfo("GothamForge", f"Updated cheat code for {s[0]}.")
        except Exception as e:
            self.report(e)

    def _cc_remove(self):
        s = self.cc_tree.selection()
        if not s or not self._coll:
            return
        try:
            self.safety.backup(self._coll.path)
            self._coll.set_cheat_code(s[0], None)
            self._coll.set_cheat_code_only(s[0], False)
            self._coll.save()
            self._cc_fill()
            self.cc_code.set("")
            messagebox.showinfo("GothamForge", f"Removed cheat code from {s[0]}.")
        except Exception as e:
            self.report(e)

    def _build_colors(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text="Colors")
        left = ttk.Frame(f)
        left.pack(side="left", fill="y")
        ttk.Label(left, text="Character (.CD):").pack(anchor="w")
        self.col_q = tk.StringVar()
        e = ttk.Entry(left, textvariable=self.col_q)
        e.pack(fill="x")
        e.bind("<KeyRelease>", lambda _e: self._col_fill_chars())
        self.col_char_list = tk.Listbox(left, width=24, height=30, exportselection=False)
        self.col_char_list.pack(fill="y", expand=True, pady=4)
        self.col_char_list.bind("<<ListboxSelect>>", self._col_pick_char)

        inner = ttk.Notebook(f)
        inner.pack(side="left", fill="both", expand=True, padx=8)

        ctab = ttk.Frame(inner, padding=6)
        inner.add(ctab, text="Colours")
        mid = ttk.Frame(ctab)
        mid.pack(side="left", fill="both", expand=True)
        ttk.Label(mid, text="Parts / materials (pick one to recolour):").pack(anchor="w")
        cols = ("idx", "type", "name")
        self.col_mat_tree = ttk.Treeview(mid, columns=cols, show="headings", height=22)
        for c, w, t in zip(cols, (40, 80, 320), ("#", "Type", "Current material")):
            self.col_mat_tree.heading(c, text=t)
            self.col_mat_tree.column(c, width=w)
        self.col_mat_tree.pack(fill="both", expand=True)
        self.col_mat_tree.bind("<<TreeviewSelect>>", self._col_pick_mat)
        sw = ttk.Frame(mid)
        sw.pack(anchor="w", pady=4)
        ttk.Label(sw, text="current colour:").pack(side="left")
        self.col_swatch_mat = tk.Canvas(sw, width=60, height=22, highlightthickness=1, highlightbackground="#888")
        self.col_swatch_mat.pack(side="left", padx=6)
        right = ttk.Frame(ctab)
        right.pack(side="left", fill="y", padx=6)
        ttk.Label(right, text="LEGO colours:").pack(anchor="w")
        self.col_pal_list = tk.Listbox(right, width=22, height=20, exportselection=False)
        self.col_pal_list.pack(pady=4)
        self.col_pal_list.bind("<<ListboxSelect>>", self._col_pick_colour)
        self.col_swatch_new = tk.Canvas(right, width=150, height=26, highlightthickness=1, highlightbackground="#888")
        self.col_swatch_new.pack(pady=2)
        ttk.Button(right, text="Apply to selected part", command=self._col_apply).pack(pady=6)

        vis = ttk.Frame(inner, padding=6)
        inner.add(vis, text="Visibility / parts")
        self.vis_status = ttk.Label(vis, text="Select a minifig character", font=("Segoe UI", 10, "bold"))
        self.vis_status.pack(anchor="w")
        pre = ttk.Frame(vis)
        pre.pack(anchor="w", pady=4)
        ttk.Label(pre, text="Preset:").pack(side="left")
        for label, val in cddef.LAYER_PRESETS.items():
            ttk.Button(pre, text=label, command=lambda v=val: self._vis_preset(v)).pack(side="left", padx=2)
        self.vis_vars = {1: {}, 2: {}, 3: {}}
        for title, bidx, bits in [("Byte 1 - body (head/torso/arms/hands/hips/neck)", 1, cddef.LAYER_BYTE1),
                                  ("Byte 2 - legs / cape / addons", 2, cddef.LAYER_BYTE2),
                                  ("Byte 3 - hat / hair / glasses / attachments", 3, cddef.LAYER_BYTE3)]:
            lf = ttk.LabelFrame(vis, text=title, padding=4)
            lf.pack(fill="x", pady=3)
            for i, (name, mask) in enumerate(bits):
                v = tk.BooleanVar()
                self.vis_vars[bidx][mask] = v
                ttk.Checkbutton(lf, text=name, variable=v).grid(row=i // 4, column=i % 4, sticky="w", padx=4)
        ttk.Button(vis, text="Apply visibility", command=self._vis_apply).pack(anchor="e", pady=6)
        ttk.Label(vis, foreground="#888", wraplength=440, justify="left",
                  text="Toggles which minifig parts render (edits the .CD layer bytes; main + "
                       "cutscene copies are kept in sync). Backed up automatically.").pack(anchor="w")

        face = ttk.Frame(inner, padding=6)
        inner.add(face, text="Face / Head")
        fle = ttk.Frame(face)
        fle.pack(side="left", fill="y")
        ttk.Label(fle, text="Head slot:").pack(anchor="w")
        self.face_slot = ttk.Combobox(fle, width=30, state="readonly")
        self.face_slot.pack(anchor="w", pady=2)
        self.face_slot.bind("<<ComboboxSelected>>", lambda _e: self._face_show_current())
        self.face_cur_lbl = ttk.Label(fle, text="", foreground="#888")
        self.face_cur_lbl.pack(anchor="w")
        self.face_cur_prev = ttk.Label(fle)
        self.face_cur_prev.pack(pady=4)
        ttk.Label(fle, text="Search heads:").pack(anchor="w")
        self.face_q = tk.StringVar()
        fe = ttk.Entry(fle, textvariable=self.face_q)
        fe.pack(fill="x")
        fe.bind("<KeyRelease>", lambda _e: self._face_fill_list())
        self.face_list = tk.Listbox(fle, width=30, height=12, exportselection=False)
        self.face_list.pack(fill="y", expand=True, pady=2)
        self.face_list.bind("<<ListboxSelect>>", self._face_preview_new)
        fri = ttk.Frame(face)
        fri.pack(side="left", fill="both", expand=True, padx=10)
        ttk.Label(fri, text="New head preview:").pack(anchor="w")
        self.face_new_prev = ttk.Label(fri)
        self.face_new_prev.pack(pady=6)
        ttk.Button(fri, text="Apply head to slot", command=self._face_apply).pack(anchor="w", pady=6)
        ttk.Label(fri, foreground="#888", wraplength=260, justify="left",
                  text="Swaps which face/head texture this character uses (edits the .CD). "
                       "Tip: hair/hat come from the Visibility byte 3.").pack(anchor="w")
        self._heads = cddef.head_catalogue(self.game)

        self._colours = cddef.LegoColours(self.game)
        for n in self._colours.names():
            self.col_pal_list.insert("end", n)
        self._cd = None
        self.after(80, self._col_lazylist)

    def _col_lazylist(self):
        self._col_all = sorted(self.game.chars_dir.rglob("*.CD"), key=lambda p: p.stem.lower())
        self._col_fill_chars()

    def _col_fill_chars(self):
        flt = self.col_q.get().lower()
        self._col_chars = [p for p in getattr(self, "_col_all", []) if flt in p.stem.lower()]
        self.col_char_list.delete(0, "end")
        for p in self._col_chars:
            self.col_char_list.insert("end", p.stem)

    def _col_pick_char(self, _e=None):
        s = self.col_char_list.curselection()
        if not s:
            return
        try:
            self._cd = cddef.CdFile(self._col_chars[s[0]])
            self._col_fill_mats()
            self._vis_fill()
            self._face_fill()
        except Exception as e:
            self.report(e)

    def _head_thumb(self, cd_name, size=140):
        if not HAVE_PIL:
            return None
        p = self._heads.get(cd_name.upper())
        if not p:
            return None
        try:
            im = tex.to_image(p)
            im.thumbnail((size, size))
            return ImageTk.PhotoImage(im)
        except Exception:
            return None

    def _face_fill(self):
        self._face_slots = self._cd.head_materials() if self._cd else []
        self.face_slot["values"] = [f"#{m['index']}  {m['name']}" for m in self._face_slots]
        if self._face_slots:
            self.face_slot.current(0)
        else:
            self.face_slot.set("")
        self._face_fill_list()
        self._face_show_current()

    def _face_fill_list(self):
        flt = self.face_q.get().upper()
        self._face_names = [n for n in sorted(self._heads) if flt in n]
        self.face_list.delete(0, "end")
        for n in self._face_names:
            self.face_list.insert("end", n)

    def _face_show_current(self):
        i = self.face_slot.current()
        if not getattr(self, "_face_slots", None) or i < 0 or i >= len(self._face_slots):
            self.face_cur_lbl.config(text="(no head slot on this character)")
            self.face_cur_prev.config(image="")
            self._face_cur_ref = None
            return
        m = self._face_slots[i]
        self.face_cur_lbl.config(text="current: " + m["name"])
        self._face_cur_ref = self._head_thumb(m["name"])
        self.face_cur_prev.config(image=self._face_cur_ref or "")

    def _face_preview_new(self, _e=None):
        s = self.face_list.curselection()
        if not s:
            return
        self._face_new_ref = self._head_thumb(self._face_names[s[0]], 180)
        self.face_new_prev.config(image=self._face_new_ref or "")

    def _face_apply(self):
        if not self._cd:
            return
        si = self.face_slot.current()
        ls = self.face_list.curselection()
        if si < 0 or not getattr(self, "_face_slots", None) or not ls:
            return messagebox.showinfo("GothamForge", "Pick a head slot (left) and a head (list) first.")
        mat = self._face_slots[si]
        head = self._face_names[ls[0]]
        try:
            self.safety.backup(self._cd.path)
            if not self._cd.set_material(mat["index"], head):
                return messagebox.showerror("GothamForge", "Couldn't swap head (safety check failed).")
            self._cd.save()
            self._col_fill_mats()
            self._face_fill()
            self._fill_dashboard()
            messagebox.showinfo("GothamForge", f"Set head slot #{mat['index']} -> {head}.")
        except Exception as e:
            self.report(e)

    def _vis_fill(self):
        L = self._cd.layers() if self._cd else None
        if not L:
            self.vis_status.config(text="(this character has no editable minifig layers)")
            for bidx in (1, 2, 3):
                for v in self.vis_vars[bidx].values():
                    v.set(False)
            return
        self.vis_status.config(
            text=f"byte1=0x{L['byte1']:02X}   byte2=0x{L['byte2']:02X}   byte3=0x{L['byte3']:02X}")
        for bidx, key in ((1, "byte1"), (2, "byte2"), (3, "byte3")):
            for mask, v in self.vis_vars[bidx].items():
                v.set(bool(L[key] & mask))

    def _vis_preset(self, val):
        for mask, v in self.vis_vars[1].items():
            v.set(bool(val & mask))

    def _vis_apply(self):
        if not self._cd:
            return
        if self._cd.layers() is None:
            return messagebox.showinfo("GothamForge", "This character has no editable minifig layers.")
        b = {bidx: sum(m for m, v in self.vis_vars[bidx].items() if v.get()) for bidx in (1, 2, 3)}
        try:
            self.safety.backup(self._cd.path)
            if not self._cd.set_layers(b[1], b[2], b[3]):
                return messagebox.showerror("GothamForge", "Could not write the layer bytes.")
            self._cd.save()
            self._vis_fill()
            self._fill_dashboard()
            messagebox.showinfo("GothamForge",
                                f"Set visibility -> byte1=0x{b[1]:02X} byte2=0x{b[2]:02X} byte3=0x{b[3]:02X}.")
        except Exception as e:
            self.report(e)

    def _col_fill_mats(self):
        self.col_mat_tree.delete(*self.col_mat_tree.get_children())
        for m in self._cd.materials():
            self.col_mat_tree.insert("", "end", iid=str(m["index"]),
                                     values=(m["index"], m["kind"], m["name"]))

    def _swatch(self, canvas, rgb, w, h):
        canvas.delete("all")
        if rgb:
            canvas.create_rectangle(0, 0, w, h, fill="#%02x%02x%02x" % tuple(rgb), outline="")

    def _col_pick_mat(self, _e=None):
        s = self.col_mat_tree.selection()
        if not s or not self._cd:
            return
        m = self._cd.materials()[int(s[0])]
        rgb = self._colours.rgb(m["name"]) if m["kind"] == "colour" else None
        self._swatch(self.col_swatch_mat, rgb, 60, 22)

    def _col_pick_colour(self, _e=None):
        s = self.col_pal_list.curselection()
        if not s:
            return
        self._swatch(self.col_swatch_new, self._colours.rgb(self.col_pal_list.get(s[0])), 150, 26)

    def _col_apply(self):
        ms = self.col_mat_tree.selection()
        cs = self.col_pal_list.curselection()
        if not ms or not cs or not self._cd:
            return messagebox.showinfo("GothamForge", "Pick a part (middle) and a colour (right) first.")
        idx = int(ms[0])
        colour = self.col_pal_list.get(cs[0])
        try:
            self.safety.backup(self._cd.path)
            if not self._cd.set_colour(idx, colour):
                return messagebox.showerror("GothamForge", "Couldn't edit that material (safety check failed).")
            self._cd.save()
            self._col_fill_mats()
            self._fill_dashboard()
            messagebox.showinfo("GothamForge", f"Set part #{idx} -> {colour}.")
        except Exception as e:
            self.report(e)

    def _build_streaks(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text="Streaks")
        left = ttk.Frame(f)
        left.pack(side="left", fill="y")
        ttk.Label(left, text="Characters with streaks:").pack(anchor="w")
        self.streak_q = tk.StringVar()
        e = ttk.Entry(left, textvariable=self.streak_q)
        e.pack(fill="x")
        e.bind("<KeyRelease>", lambda _e: self._streak_fill_list())
        self.streak_list = tk.Listbox(left, width=30, height=30, exportselection=False)
        self.streak_list.pack(fill="y", expand=True, pady=4)
        self.streak_list.bind("<<ListboxSelect>>", self._streak_pick)
        right = ttk.Frame(f)
        right.pack(side="left", fill="both", expand=True, padx=8)
        self.streak_title = ttk.Label(right, text="Select a character", font=("Segoe UI", 12, "bold"))
        self.streak_title.pack(anchor="w")
        named = ttk.Frame(right)
        named.pack(fill="x", pady=4)
        ttk.Label(named, text="Named streak:").pack(side="left")
        self.streak_name = tk.StringVar()
        ttk.Combobox(named, textvariable=self.streak_name, width=14,
                     values=streaks.KNOWN_STREAK_NAMES).pack(side="left", padx=4)
        self.streak_rows_frame = ttk.LabelFrame(
            right, text="FlyingStreak trails - click a swatch to pick a colour", padding=6)
        self.streak_rows_frame.pack(fill="both", expand=True, pady=4)
        ttk.Button(right, text="Save streaks", command=self._streak_save).pack(anchor="e", pady=6)
        self._streak_chars = []
        self._streak_widgets = []
        self.after(80, self._streak_lazylist)

    def _streak_lazylist(self):
        self._streak_all = streaks.find_streak_chars(self.game)
        self._streak_fill_list()

    def _streak_fill_list(self):
        flt = self.streak_q.get().lower()
        self._streak_chars = [p for p in getattr(self, "_streak_all", []) if flt in p.stem.lower()]
        self.streak_list.delete(0, "end")
        for p in self._streak_chars:
            self.streak_list.insert("end", p.stem)

    @staticmethod
    def _hex(rgb):
        return "#%02x%02x%02x" % (int(rgb[0]) & 255, int(rgb[1]) & 255, int(rgb[2]) & 255)

    def _streak_pick(self, _e=None):
        s = self.streak_list.curselection()
        if not s:
            return
        path = self._streak_chars[s[0]]
        self._streak_path = path
        sfile = streaks.StreakFile(path)
        self.streak_title.config(text=path.stem)
        n = sfile.named()
        self.streak_name.set(n["name"] if n else "")
        for w in self.streak_rows_frame.winfo_children():
            w.destroy()
        self._streak_widgets = []
        fly = sfile.flying()
        if not fly:
            ttk.Label(self.streak_rows_frame, foreground="#888",
                      text="(no explicit FlyingStreak trails - only a named streak)").pack(anchor="w")
        for fs in fly:
            self._add_streak_row(fs)

    def _add_streak_row(self, fs):
        row = ttk.Frame(self.streak_rows_frame)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=f"#{fs['idx']} loc{fs['loc']}", width=10).pack(side="left")
        rgb = [fs["r"], fs["g"], fs["b"]]
        avar = tk.StringVar(value=str(fs["a"]))
        wvar = tk.StringVar(value=str(fs["width"]))
        swatch = tk.Button(row, width=4, bg=self._hex(rgb), relief="groove")

        def pick():
            c = colorchooser.askcolor(color=self._hex(rgb), title="Streak colour")
            if c and c[0]:
                rgb[0], rgb[1], rgb[2] = (int(v) for v in c[0])
                swatch.config(bg=self._hex(rgb))
        swatch.config(command=pick)
        swatch.pack(side="left", padx=4)
        ttk.Label(row, text="A:").pack(side="left")
        ttk.Entry(row, textvariable=avar, width=5).pack(side="left")
        ttk.Label(row, text="Width:").pack(side="left", padx=(8, 0))
        ttk.Entry(row, textvariable=wvar, width=7).pack(side="left", padx=2)
        self._streak_widgets.append({"line": fs["line"], "rgb": rgb, "a": avar, "w": wvar})

    def _streak_save(self):
        if not getattr(self, "_streak_path", None):
            return
        try:
            self.safety.backup(self._streak_path)
            sfile = streaks.StreakFile(self._streak_path)
            for w in self._streak_widgets:
                aw = w["a"].get().strip()
                a = int(aw) if aw.lstrip("-").isdigit() else None
                sfile.set_flying(w["line"], w["rgb"][0], w["rgb"][1], w["rgb"][2], a=a, width=w["w"].get().strip())
            if self.streak_name.get().strip():
                sfile.set_named(self.streak_name.get().strip())
            sfile.save()
            self._fill_dashboard()
            messagebox.showinfo("GothamForge", f"Saved streaks for {self._streak_path.stem}.")
        except Exception as e:
            self.report(e)

    def _build_backups(self):
        f = ttk.Frame(self.nb, padding=8)
        self.nb.add(f, text="Backups")
        ttk.Label(f, text="Files you've modified (original safely stored):").pack(anchor="w")
        self.bk_list = tk.Listbox(f, height=26)
        self.bk_list.pack(fill="both", expand=True, pady=6)
        bar = ttk.Frame(f)
        bar.pack(fill="x")
        ttk.Button(bar, text="Restore selected", command=self._bk_restore).pack(side="left")
        ttk.Button(bar, text="Restore ALL", command=self.restore_all).pack(side="left", padx=6)
        ttk.Button(bar, text="Refresh", command=self._fill_backups).pack(side="left")
        self._fill_backups()

    def _fill_backups(self):
        self.bk_list.delete(0, "end")
        for rel in sorted(self.safety.list()):
            self.bk_list.insert("end", rel)

    def _bk_restore(self):
        sel = self.bk_list.curselection()
        if not sel:
            return
        rel = self.bk_list.get(sel[0])
        try:
            self.safety.restore(rel)
            self._fill_backups()
            self._fill_dashboard()
            messagebox.showinfo("GothamForge", f"Restored {rel}")
        except Exception as e:
            self.report(e)


def main():
    app = App()
    if app.winfo_exists():
        app.mainloop()


if __name__ == "__main__":
    main()
