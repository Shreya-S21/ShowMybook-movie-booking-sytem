# ============================================================
# frontend.py — BookMyShow-style Tkinter UI
# With: per-field live validation, phone number booking,
#       SMS confirmation simulation
# ============================================================

import re
import tkinter as tk
from tkinter import ttk, messagebox
import backend

# ── PALETTE ─────────────────────────────────────────────────
BG        = "#0a0a0f"
BG2       = "#12121a"
BG3       = "#1a1a26"
BG4       = "#22223a"
ACCENT    = "#e31837"
ACCENT2   = "#ff6b35"
GOLD      = "#f5c518"
TEXT      = "#ffffff"
TEXT2     = "#b0b3c1"
TEXT3     = "#6b6f85"
SUCCESS   = "#21c55d"
WARN      = "#f59e0b"
INFO      = "#3b82f6"
CARD_BDR  = "#2a2a3f"
ERR_BG    = "#2d0a0a"
ERR_FG    = "#f87171"
OK_FG     = "#4ade80"

C_AVAIL   = "#21c55d"
C_MINE    = "#f59e0b"
C_LOCKED  = "#374151"
C_BOOKED  = "#3b1219"
C_SCREEN  = "#1e2040"

FH1 = ("Georgia", 22, "bold")
FH2 = ("Georgia", 16, "bold")
FH3 = ("Georgia", 13, "bold")
FB  = ("Segoe UI", 10, "bold")
FM  = ("Segoe UI", 10)
FS  = ("Segoe UI", 9)
FXS = ("Segoe UI", 8)
FMONO = ("Courier New", 9)

SEAT_SIZE = 34
SEAT_GAP  = 4
AISLE_GAP = 20


# ── HELPERS ──────────────────────────────────────────────────

def centre(win, w, h):
    win.update_idletasks()
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")


def style_win(win, title, w, h, resizable=False):
    win.title(title)
    win.configure(bg=BG)
    win.resizable(resizable, resizable)
    centre(win, w, h)


def _darken(hex_col, amt=25):
    try:
        r = max(0, int(hex_col[1:3], 16) - amt)
        g = max(0, int(hex_col[3:5], 16) - amt)
        b = max(0, int(hex_col[5:7], 16) - amt)
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_col


def _lighten(hex_col, amt=20):
    try:
        r = min(255, int(hex_col[1:3], 16) + amt)
        g = min(255, int(hex_col[3:5], 16) + amt)
        b = min(255, int(hex_col[5:7], 16) + amt)
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_col


def btn(parent, text, cmd, bg=ACCENT, fg="#fff", w=16, **kw):
    b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                  activebackground=_darken(bg), activeforeground=fg,
                  relief="flat", font=FB, cursor="hand2",
                  width=w, pady=7, **kw)
    b.bind("<Enter>", lambda e: b.config(bg=_darken(bg)))
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b


def ghost_btn(parent, text, cmd, w=16, **kw):
    b = tk.Button(parent, text=text, command=cmd,
                  bg=BG3, fg=TEXT2,
                  activebackground=BG4, activeforeground=TEXT,
                  relief="flat", font=FB, cursor="hand2",
                  width=w, pady=7, **kw)
    b.bind("<Enter>", lambda e: b.config(bg=BG4, fg=TEXT))
    b.bind("<Leave>", lambda e: b.config(bg=BG3, fg=TEXT2))
    return b


def lbl(parent, text, font=FM, fg=TEXT, bg=None, **kw):
    return tk.Label(parent, text=text, font=font, fg=fg,
                    bg=bg if bg is not None else BG, **kw)


def sep(parent, bg=CARD_BDR, pady=8):
    tk.Frame(parent, bg=bg, height=1).pack(fill="x", pady=pady)


def ent(parent, show=None, w=28, bg=BG3):
    return tk.Entry(parent, show=show, width=w, bg=bg, fg=TEXT,
                    insertbackground=TEXT2, relief="flat", font=FM, bd=6,
                    highlightthickness=1, highlightbackground=CARD_BDR,
                    highlightcolor=ACCENT)


def badge(parent, text, bg=ACCENT, fg="#fff"):
    tk.Label(parent, text=text, font=FXS, bg=bg, fg=fg,
             padx=7, pady=2, relief="flat").pack(side="left", padx=2)


def style_tree(tv, cols, heads, widths):
    s = ttk.Style()
    s.theme_use("clam")
    s.configure("D.Treeview",
                background=BG2, foreground=TEXT,
                fieldbackground=BG2, rowheight=28, font=FS,
                borderwidth=0)
    s.configure("D.Treeview.Heading",
                background=BG3, foreground=GOLD,
                font=("Segoe UI", 9, "bold"), relief="flat")
    s.map("D.Treeview",
          background=[("selected", ACCENT)],
          foreground=[("selected", "#fff")])
    tv["style"] = "D.Treeview"
    tv["columns"] = cols
    tv["show"] = "headings"
    for c, h, w in zip(cols, heads, widths):
        tv.heading(c, text=h)
        tv.column(c, width=w, anchor="center")


# ── TOPBAR helper ────────────────────────────────────────────

def topbar(win, title_text, subtitle=None, right_widgets_fn=None):
    bar = tk.Frame(win, bg=BG2, pady=0)
    bar.pack(fill="x")
    tk.Frame(bar, bg=ACCENT, height=3).pack(fill="x")
    inner = tk.Frame(bar, bg=BG2, padx=20, pady=12)
    inner.pack(fill="x")
    left = tk.Frame(inner, bg=BG2)
    left.pack(side="left")
    lbl(left, title_text, font=FH3, fg=TEXT, bg=BG2).pack(anchor="w")
    if subtitle:
        lbl(left, subtitle, font=FXS, fg=TEXT3, bg=BG2).pack(anchor="w")
    if right_widgets_fn:
        right = tk.Frame(inner, bg=BG2)
        right.pack(side="right")
        right_widgets_fn(right)
    return bar


# ── VALIDATED ENTRY WIDGET ────────────────────────────────────

class ValidatedEntry:
    """
    An Entry widget paired with an inline error/hint label.
    Call .validate(fn) to attach a validator that runs on focus-out.
    Call .get() / .get_value() to retrieve the current text.
    Call .mark_error(msg) / .mark_ok() to set state externally.
    """

    def __init__(self, parent, hint="", show=None, bg=BG3):
        self._frame = tk.Frame(parent, bg=BG2)
        self._entry = tk.Entry(
            self._frame, show=show, bg=bg, fg=TEXT,
            insertbackground=TEXT2, relief="flat", font=FM, bd=6,
            highlightthickness=1, highlightbackground=CARD_BDR,
            highlightcolor=ACCENT)
        self._entry.pack(fill="x")
        self._msg_lbl = tk.Label(
            self._frame, text="", font=FXS, fg=ERR_FG,
            bg=BG2, anchor="w", justify="left")
        self._msg_lbl.pack(fill="x", pady=(1, 0))
        self._validator = None
        self._entry.bind("<FocusOut>", self._on_focus_out)

    def pack(self, **kw):
        self._frame.pack(**kw)

    def _on_focus_out(self, _=None):
        if self._validator:
            ok, msg = self._validator(self._entry.get())
            if not ok:
                self.mark_error(msg)
            else:
                self.mark_ok()

    def attach_validator(self, fn):
        """fn(raw_str) -> (bool, str)  — same signature as backend validators."""
        self._validator = fn

    def mark_error(self, msg):
        self._entry.config(highlightbackground=ACCENT, highlightcolor=ACCENT,
                           highlightthickness=1)
        # Show only first line of multi-line error to save space
        first_line = msg.split("\n")[0]
        self._msg_lbl.config(text=f"✗ {first_line}", fg=ERR_FG)

    def mark_ok(self):
        self._entry.config(highlightbackground=SUCCESS, highlightcolor=SUCCESS,
                           highlightthickness=1)
        self._msg_lbl.config(text="✓ Looks good", fg=OK_FG)

    def clear_state(self):
        self._entry.config(highlightbackground=CARD_BDR, highlightthickness=1)
        self._msg_lbl.config(text="")

    def get(self):
        return self._entry.get()

    def insert(self, idx, val):
        self._entry.insert(idx, val)

    def delete(self, a, b):
        self._entry.delete(a, b)
        self.clear_state()

    def run_validation(self):
        """Force-run the validator and return (ok, msg)."""
        if self._validator:
            ok, msg = self._validator(self._entry.get())
            if not ok:
                self.mark_error(msg)
            else:
                self.mark_ok()
            return ok, msg
        return True, ""


# ═══════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════

class LoginWindow:
    def __init__(self, root):
        self.root = root
        style_win(root, "ShowMyBook — Login", 460, 580)
        self._build()

    def _build(self):
        hero = tk.Frame(self.root, bg=ACCENT, height=8)
        hero.pack(fill="x")

        tk.Frame(self.root, bg=BG, height=30).pack(fill="x")

        logo_f = tk.Frame(self.root, bg=BG)
        logo_f.pack()
        lbl(logo_f, "show", font=("Georgia", 28, "bold"), fg=TEXT).pack(side="left")
        lbl(logo_f, "my", font=("Georgia", 28, "bold"), fg=ACCENT).pack(side="left")
        lbl(logo_f, "book", font=("Georgia", 28, "bold"), fg=TEXT).pack(side="left")

        lbl(self.root, "Movies ", font=FXS, fg=TEXT3).pack(pady=(4, 28))

        card = tk.Frame(self.root, bg=BG2, padx=40, pady=32,
                        highlightthickness=1, highlightbackground=CARD_BDR)
        card.pack(padx=44, fill="x")

        lbl(card, "Sign In", font=FH2, fg=TEXT, bg=BG2).pack(anchor="w", pady=(0, 4))
        lbl(card, "Enter your credentials to continue",
            font=FXS, fg=TEXT3, bg=BG2).pack(anchor="w", pady=(0, 18))

        lbl(card, "Username", font=FS, fg=TEXT3, bg=BG2).pack(anchor="w")
        self.uent = ent(card, bg=BG3)
        self.uent.pack(fill="x", pady=(3, 14))

        lbl(card, "Password", font=FS, fg=TEXT3, bg=BG2).pack(anchor="w")
        self.pent = ent(card, show="●", bg=BG3)
        self.pent.pack(fill="x", pady=(3, 22))

        btn(card, "SIGN IN", self._login, w=34).pack(fill="x", pady=(0, 10))
        ghost_btn(card, "Register New Account", self._register, w=34).pack(fill="x")

        lbl(self.root, "admin / admin123   ·   user1 / user123",
            font=FXS, fg=TEXT3).pack(pady=(16, 0))
        self.root.bind("<Return>", lambda e: self._login())

    def _login(self):
        u, p = self.uent.get().strip(), self.pent.get().strip()
        if not u or not p:
            messagebox.showwarning("Missing Fields", "Please enter username and password.")
            return
        user = backend.login_user(u, p)
        if user:
            self.root.destroy()
            nr = tk.Tk()
            if user["role"] == "admin":
                AdminDashboard(nr)
            else:
                UserDashboard(nr, dict(user))
            nr.mainloop()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")

    def _register(self):
        RegisterWindow(self.root)


# ═══════════════════════════════════════════════════════════
# REGISTER
# ═══════════════════════════════════════════════════════════

class RegisterWindow:
    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        style_win(self.win, "Create Account", 400, 360)
        tk.Frame(self.win, bg=ACCENT, height=4).pack(fill="x")
        lbl(self.win, "Create Account", font=FH2, fg=TEXT).pack(pady=(20, 2))
        lbl(self.win, "Join ShowMyBook", font=FXS, fg=TEXT3).pack(pady=(0, 18))

        card = tk.Frame(self.win, bg=BG2, padx=36, pady=28,
                        highlightthickness=1, highlightbackground=CARD_BDR)
        card.pack(padx=30, fill="x")

        lbl(card, "Username", font=FS, fg=TEXT3, bg=BG2).pack(anchor="w")
        self.u = ent(card)
        self.u.pack(fill="x", pady=(3, 12))

        lbl(card, "Password", font=FS, fg=TEXT3, bg=BG2).pack(anchor="w")
        self.p = ent(card, show="●")
        self.p.pack(fill="x", pady=(3, 20))

        btn(card, "Register", self._do, w=30).pack(fill="x")

    def _do(self):
        ok, msg = backend.register_user(self.u.get(), self.p.get())
        if ok:
            messagebox.showinfo("Success", msg)
            self.win.destroy()
        else:
            messagebox.showerror("Error", msg)


# ═══════════════════════════════════════════════════════════
# ADMIN DASHBOARD
# ═══════════════════════════════════════════════════════════

# Field definitions: (display_label, dict_key, hint, validator_fn)
MOVIE_FIELDS = [
    ("Movie Name",       "name",     "e.g. Pushpa 2: The Rule",               None),
    ("Release Date",     "date",     "DD-MM-YYYY  (e.g. 05-12-2024)",         backend.validate_release_date),
    ("Director",         "director", "Letters & spaces only (e.g. Sukumar)",  backend.validate_director_name),
    ("Cast",             "cast",     "e.g. Allu Arjun, Rashmika Mandanna",    backend.validate_cast),
    ("Duration (mins)",  "duration", "Whole number of minutes (e.g. 175)",    backend.validate_duration),
    ("Rating / Censor",  "rating",   "U / A / U/A / UA / S  (e.g. U/A 16+)", backend.validate_rating),
    ("Ticket Price (₹)", "price",    "Numbers only (e.g. 250)",               backend.validate_price),
    ("Rows",             "rows",     "1–26  (e.g. 8  →  rows A–H)",           None),
    ("Columns",          "cols",     "1–30  (e.g. 10  →  seats 1–10)",        None),
]


class AdminDashboard:
    def __init__(self, root):
        self.root = root
        self._sel_id = None
        style_win(root, "ShowMyBook — Admin Panel", 1100, 720, resizable=True)
        self._build()
        self._reload()

    def _build(self):
        def _right(f):
            btn(f, "All Bookings", self._all_bookings, bg=INFO, w=14).pack(side="left", padx=4)
            btn(f, "Logout", self._logout, bg=BG4, w=10).pack(side="left", padx=4)

        topbar(self.root, "  ADMIN PANEL", "Manage movies, seats & bookings", _right)

        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True)

        left = tk.Frame(main, bg=BG2, width=380)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        self._build_form(left)

        right = tk.Frame(main, bg=BG)
        right.pack(side="right", fill="both", expand=True)
        self._build_list(right)

    def _build_form(self, p):
        hdr = tk.Frame(p, bg=BG3, padx=18, pady=12)
        hdr.pack(fill="x")
        lbl(hdr, "Movie Details", font=FH3, fg=TEXT, bg=BG3).pack(side="left")

        canvas = tk.Canvas(p, bg=BG2, highlightthickness=0)
        sb = ttk.Scrollbar(p, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        inner = tk.Frame(canvas, bg=BG2, padx=18, pady=10)
        cwin = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(
            cwin, width=e.width))

        self.vent = {}   # ValidatedEntry widgets keyed by field key

        for lbl_text, key, hint, validator in MOVIE_FIELDS:
            row_f = tk.Frame(inner, bg=BG2)
            row_f.pack(fill="x", pady=(0, 8))

            lbl(row_f, lbl_text, font=("Segoe UI", 9, "bold"), fg=TEXT2, bg=BG2).pack(anchor="w")
            lbl(row_f, hint, font=FXS, fg=TEXT3, bg=BG2).pack(anchor="w", pady=(1, 2))

            ve = ValidatedEntry(row_f, bg=BG3)
            ve.pack(fill="x")
            if validator:
                ve.attach_validator(validator)
            self.vent[key] = ve

        sep(inner, pady=6)

        bf = tk.Frame(inner, bg=BG2)
        bf.pack(fill="x", pady=(4, 8))
        btn(bf, "Add Movie", self._add, w=14).grid(row=0, column=0, padx=3, pady=3)
        btn(bf, "Update", self._update, bg="#166534", w=11).grid(row=0, column=1, padx=3, pady=3)
        btn(bf, "Delete", self._delete, bg="#7f1d1d", w=11).grid(row=1, column=0, padx=3, pady=3)
        ghost_btn(bf, "Clear Form", self._clear, w=11).grid(row=1, column=1, padx=3, pady=3)

    def _build_list(self, p):
        sf = tk.Frame(p, bg=BG, pady=10, padx=14)
        sf.pack(fill="x")
        lbl(sf, "Search movies:", font=FS, fg=TEXT3).pack(side="left", padx=(0, 8))
        self.sv = tk.StringVar()
        self.sv.trace("w", lambda *a: self._search())
        tk.Entry(sf, textvariable=self.sv, bg=BG3, fg=TEXT,
                 insertbackground=TEXT2, relief="flat", font=FM,
                 bd=5, width=30,
                 highlightthickness=1, highlightbackground=CARD_BDR,
                 highlightcolor=ACCENT).pack(side="left")

        fr = tk.Frame(p, bg=BG)
        fr.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        cols  = ("id", "name", "date", "director", "cast", "dur", "rating", "price", "avail", "total")
        heads = ("ID", "Movie", "Release", "Director", "Cast", "Dur(m)", "Rating", "Price", "Avail", "Total")
        ws    = (35, 150, 90, 110, 140, 65, 65, 65, 55, 55)

        sy = ttk.Scrollbar(fr, orient="vertical")
        sx = ttk.Scrollbar(fr, orient="horizontal")
        self.tree = ttk.Treeview(fr, yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.config(command=self.tree.yview)
        sx.config(command=self.tree.xview)
        style_tree(self.tree, cols, heads, ws)
        self.tree.pack(side="left", fill="both", expand=True)
        sy.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_sel)

    def _reload(self, movies=None):
        for r in self.tree.get_children():
            self.tree.delete(r)
        if movies is None:
            movies = backend.get_all_movies()
        for m in movies:
            total, booked, avail = backend.get_movie_stats(m["movie_id"])
            self.tree.insert("", "end", values=(
                m["movie_id"], m["movie_name"], m["release_date"],
                m["director"], m["cast"], m["duration"], m["rating"],
                f"₹{m['ticket_price']:.0f}", avail, total))

    def _search(self):
        kw = self.sv.get().strip()
        self._reload(backend.search_movies(kw) if kw else None)

    def _on_sel(self, _):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])["values"]
        m = backend.get_movie_by_id(vals[0])
        if not m:
            return
        self._clear()
        mapping = [
            ("name",     m["movie_name"]),
            ("date",     m["release_date"]),
            ("director", m["director"]),
            ("cast",     m["cast"]),
            ("duration", m["duration"]),
            ("rating",   m["rating"]),
            ("price",    m["ticket_price"]),
            ("rows",     m["rows"]),
            ("cols",     m["cols"]),
        ]
        for k, v in mapping:
            self.vent[k].insert(0, v)
        self._sel_id = m["movie_id"]

    def _get_raw(self):
        return {k: ve.get().strip() for k, ve in self.vent.items()}

    def _run_all_validations(self):
        """Trigger focus-out validation on every field and collect any errors."""
        all_ok = True
        for key, ve in self.vent.items():
            ok, msg = ve.run_validation()
            if not ok:
                all_ok = False
        return all_ok

    def _clear(self):
        for ve in self.vent.values():
            ve.delete(0, "end")
        self._sel_id = None

    def _add(self):
        self._run_all_validations()
        d = self._get_raw()
        ok, msg = backend.add_movie(
            d["name"], d["date"], d["director"], d["cast"],
            d["duration"], d["rating"], d["price"],
            d["rows"] or "8", d["cols"] or "10")
        if ok:
            messagebox.showinfo("Movie Added", msg)
            self._clear()
            self._reload()
        else:
            messagebox.showerror("Validation Error", msg)

    def _update(self):
        if not self._sel_id:
            messagebox.showwarning("No Selection", "Select a movie from the list first.")
            return
        self._run_all_validations()
        d = self._get_raw()
        ok, msg = backend.update_movie(
            self._sel_id, d["name"], d["date"], d["director"], d["cast"],
            d["duration"], d["rating"], d["price"],
            d["rows"] or "8", d["cols"] or "10")
        if ok:
            messagebox.showinfo("Updated", msg)
            self._reload()
        else:
            messagebox.showerror("Validation Error", msg)

    def _delete(self):
        if not self._sel_id:
            messagebox.showwarning("No Selection", "Select a movie from the list first.")
            return
        if messagebox.askyesno("Confirm Delete",
                               "Delete this movie and all its seats/bookings?\nThis cannot be undone."):
            ok, msg = backend.delete_movie(self._sel_id)
            if ok:
                messagebox.showinfo("Deleted", msg)
                self._clear()
                self._reload()
            else:
                messagebox.showerror("Error", msg)

    def _all_bookings(self):
        AllBookingsWin(self.root)

    def _logout(self):
        self.root.destroy()
        nr = tk.Tk()
        LoginWindow(nr)
        nr.mainloop()


# ═══════════════════════════════════════════════════════════
# ALL BOOKINGS (admin)
# ═══════════════════════════════════════════════════════════

class AllBookingsWin:
    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        style_win(self.win, "All Bookings", 980, 500)
        tk.Frame(self.win, bg=ACCENT, height=4).pack(fill="x")
        lbl(self.win, "All Bookings", font=FH2, fg=TEXT).pack(pady=(14, 2))
        lbl(self.win, "Complete booking history", font=FXS, fg=TEXT3).pack(pady=(0, 10))

        fr = tk.Frame(self.win, bg=BG)
        fr.pack(fill="both", expand=True, padx=14, pady=8)
        cols  = ("bid", "user", "movie", "seats", "labels", "amount", "phone", "date")
        heads = ("Booking ID", "User", "Movie", "Seats", "Seat Nos.", "Amount", "Phone", "Date")
        ws    = (80, 100, 190, 55, 190, 80, 110, 95)
        sy = ttk.Scrollbar(fr, orient="vertical")
        tv = ttk.Treeview(fr, yscrollcommand=sy.set)
        sy.config(command=tv.yview)
        style_tree(tv, cols, heads, ws)
        tv.pack(side="left", fill="both", expand=True)
        sy.pack(side="right", fill="y")
        for b in backend.get_all_bookings():
            tv.insert("", "end", values=(
                b["booking_id"], b["username"], b["movie_name"],
                b["seats"], b["seat_labels"],
                f"₹{b['total_amount']:.0f}",
                b["phone_number"], b["booking_date"]))


# ═══════════════════════════════════════════════════════════
# USER DASHBOARD
# ═══════════════════════════════════════════════════════════

class UserDashboard:
    def __init__(self, root, user):
        self.root = root
        self.user = user
        style_win(root, f"BookMyShow — {user['username']}", 1060, 680, resizable=True)
        self._build()
        self._load_movies()

    def _build(self):
        def _right(f):
            lbl(f, f"Hi, {self.user['username']}", font=FS, fg=TEXT2, bg=BG2).pack(side="left", padx=8)
            btn(f, "Logout", self._logout, bg=BG4, w=8).pack(side="left", padx=4)

        topbar(self.root, "  bookMyShow", "Movies • Events • Sports • Plays", _right)

        tab_bar = tk.Frame(self.root, bg=BG3)
        tab_bar.pack(fill="x")
        self._tbtn = []
        tabs = [("Movies", "Browse & discover"), ("Book Ticket", "By movie ID"),
                ("Cancel", "Cancel booking"), ("My Bookings", "History")]
        for i, (name, _) in enumerate(tabs):
            b = tk.Button(tab_bar, text=name, font=FB,
                          bg=BG3, fg=TEXT3, relief="flat",
                          cursor="hand2", pady=10, padx=22,
                          command=lambda i=i: self._tab(i))
            b.pack(side="left")
            self._tbtn.append(b)

        self.content = tk.Frame(self.root, bg=BG)
        self.content.pack(fill="both", expand=True)

        self.pages = {}
        self._build_browse()
        self._build_book()
        self._build_cancel()
        self._build_mybookings()
        self._tab(0)

    def _tab(self, idx):
        for i, b in enumerate(self._tbtn):
            if i == idx:
                b.config(bg=BG2, fg=TEXT, relief="flat")
                tk.Frame(b, bg=ACCENT, height=3).place(relx=0, rely=1.0, relwidth=1, anchor="sw")
            else:
                b.config(bg=BG3, fg=TEXT3, relief="flat")
        for i, pg in self.pages.items():
            if i == idx:
                pg.pack(fill="both", expand=True)
            else:
                pg.pack_forget()
        if idx == 3:
            self._refresh_mybookings()

    # ── BROWSE ───────────────────────────────

    def _build_browse(self):
        pg = tk.Frame(self.content, bg=BG)
        self.pages[0] = pg

        bar = tk.Frame(pg, bg=BG2, pady=10, padx=16)
        bar.pack(fill="x")
        lbl(bar, "Search:", font=FS, fg=TEXT3, bg=BG2).pack(side="left")
        self.bsv = tk.StringVar()
        self.bsv.trace("w", lambda *a: self._search())
        tk.Entry(bar, textvariable=self.bsv, bg=BG3, fg=TEXT,
                 insertbackground=TEXT2, relief="flat", font=FM,
                 bd=5, width=30,
                 highlightthickness=1, highlightbackground=CARD_BDR,
                 highlightcolor=ACCENT).pack(side="left", padx=8)
        btn(bar, "Select Seats", self._open_seat_picker_from_browse,
            w=14).pack(side="right", padx=4)

        fr = tk.Frame(pg, bg=BG)
        fr.pack(fill="both", expand=True, padx=14, pady=(6, 12))

        cols  = ("id", "name", "date", "director", "cast", "dur", "rating", "price", "avail")
        heads = ("ID", "Movie", "Release", "Director", "Cast", "Dur(m)", "Rating", "Price", "Avail")
        ws    = (40, 170, 90, 120, 165, 65, 65, 75, 80)

        sy = ttk.Scrollbar(fr, orient="vertical")
        sx = ttk.Scrollbar(fr, orient="horizontal")
        self.btree = ttk.Treeview(fr, yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.config(command=self.btree.yview)
        sx.config(command=self.btree.xview)
        style_tree(self.btree, cols, heads, ws)
        self.btree.pack(side="left", fill="both", expand=True)
        sy.pack(side="right", fill="y")

        lbl(pg, "Select a movie row above, then click  'Select Seats'  to pick your seats",
            font=FXS, fg=TEXT3).pack(pady=(0, 6))

    def _load_movies(self, movies=None):
        for r in self.btree.get_children():
            self.btree.delete(r)
        if movies is None:
            movies = backend.get_all_movies()
        for m in movies:
            total, booked, avail = backend.get_movie_stats(m["movie_id"])
            self.btree.insert("", "end", iid=str(m["movie_id"]), values=(
                m["movie_id"], m["movie_name"], m["release_date"],
                m["director"], m["cast"], m["duration"], m["rating"],
                f"₹{m['ticket_price']:.0f}", avail))

    def _search(self):
        kw = self.bsv.get().strip()
        self._load_movies(backend.search_movies(kw) if kw else None)

    def _open_seat_picker_from_browse(self):
        sel = self.btree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please click on a movie first.")
            return
        SeatPickerWindow(self.root, self.user, int(sel[0]), on_done=self._load_movies)

    # ── BOOK ─────────────────────────────────

    def _build_book(self):
        pg = tk.Frame(self.content, bg=BG)
        self.pages[1] = pg
        card = tk.Frame(pg, bg=BG2, padx=44, pady=36,
                        highlightthickness=1, highlightbackground=CARD_BDR)
        card.place(relx=0.5, rely=0.5, anchor="center")
        lbl(card, "Book by Movie ID", font=FH2, fg=TEXT, bg=BG2).pack(pady=(0, 4))
        lbl(card, "Enter the movie ID from the Movies tab", font=FXS, fg=TEXT3, bg=BG2).pack(pady=(0, 18))
        lbl(card, "Movie ID", font=FS, fg=TEXT3, bg=BG2).pack(anchor="w")
        self.mid_ent = ent(card, w=32)
        self.mid_ent.pack(fill="x", pady=(3, 20))
        btn(card, "Open Seat Picker", self._open_seat_picker_manual, w=30).pack(fill="x")

    def _open_seat_picker_manual(self):
        mid_str = self.mid_ent.get().strip()
        if not mid_str:
            messagebox.showwarning("Missing", "Enter a Movie ID.")
            return
        try:
            mid = int(mid_str)
        except ValueError:
            messagebox.showerror("Invalid", "Movie ID must be a number.")
            return
        if not backend.get_movie_by_id(mid):
            messagebox.showerror("Not Found", "No movie with that ID.")
            return
        SeatPickerWindow(self.root, self.user, mid, on_done=self._load_movies)

    # ── CANCEL ───────────────────────────────

    def _build_cancel(self):
        pg = tk.Frame(self.content, bg=BG)
        self.pages[2] = pg
        card = tk.Frame(pg, bg=BG2, padx=44, pady=36,
                        highlightthickness=1, highlightbackground=CARD_BDR)
        card.place(relx=0.5, rely=0.5, anchor="center")
        lbl(card, "Cancel a Booking", font=FH2, fg=TEXT, bg=BG2).pack(pady=(0, 4))
        lbl(card, "Seats will be released back for others", font=FXS, fg=TEXT3, bg=BG2).pack(pady=(0, 18))
        lbl(card, "Booking ID", font=FS, fg=TEXT3, bg=BG2).pack(anchor="w")
        self.cent = ent(card, w=32)
        self.cent.pack(fill="x", pady=(3, 20))
        btn(card, "Cancel Booking", self._cancel, bg="#7f1d1d", w=28).pack(fill="x")

    def _cancel(self):
        bid = self.cent.get().strip()
        if not bid:
            messagebox.showwarning("Missing", "Enter a Booking ID.")
            return
        try:
            bid = int(bid)
        except ValueError:
            messagebox.showerror("Invalid", "Booking ID must be a number.")
            return
        if messagebox.askyesno("Confirm Cancel", f"Cancel booking #{bid}?\nSeats will be released."):
            ok, msg = backend.cancel_booking(bid)
            if ok:
                messagebox.showinfo("Cancelled", msg)
                self.cent.delete(0, "end")
                self._load_movies()
            else:
                messagebox.showerror("Error", msg)

    # ── MY BOOKINGS ──────────────────────────

    def _build_mybookings(self):
        pg = tk.Frame(self.content, bg=BG)
        self.pages[3] = pg
        lbl(pg, "My Bookings", font=FH2, fg=TEXT).pack(pady=(14, 2))
        lbl(pg, "Your complete booking history", font=FXS, fg=TEXT3).pack()

        fr = tk.Frame(pg, bg=BG)
        fr.pack(fill="both", expand=True, padx=14, pady=(10, 0))
        cols  = ("bid", "movie", "seats", "labels", "amount", "phone", "date")
        heads = ("Booking ID", "Movie", "# Seats", "Seat Numbers", "Amount", "Phone", "Date")
        ws    = (80, 210, 65, 230, 90, 110, 100)
        sy = ttk.Scrollbar(fr, orient="vertical")
        self.mtree = ttk.Treeview(fr, yscrollcommand=sy.set)
        sy.config(command=self.mtree.yview)
        style_tree(self.mtree, cols, heads, ws)
        self.mtree.pack(side="left", fill="both", expand=True)
        sy.pack(side="right", fill="y")
        self.tot_lbl = lbl(pg, "", font=FM, fg=SUCCESS)
        self.tot_lbl.pack(pady=(8, 4))

    def _refresh_mybookings(self):
        for r in self.mtree.get_children():
            self.mtree.delete(r)
        bookings = backend.get_user_bookings(self.user["user_id"])
        total = 0
        for b in bookings:
            self.mtree.insert("", "end", values=(
                b["booking_id"], b["movie_name"], b["seats"],
                b["seat_labels"], f"₹{b['total_amount']:.0f}",
                b["phone_number"], b["booking_date"]))
            total += b["total_amount"]
        if bookings:
            self.tot_lbl.config(
                text=f"Total Spent: ₹{total:.0f}  over {len(bookings)} booking(s)")
        else:
            self.tot_lbl.config(text="No bookings yet.")

    def _logout(self):
        self.root.destroy()
        nr = tk.Tk()
        LoginWindow(nr)
        nr.mainloop()


# ═══════════════════════════════════════════════════════════
# PHONE NUMBER DIALOG  — shown before final booking confirm
# ═══════════════════════════════════════════════════════════

class PhoneDialog:
    """
    Modal dialog that collects and validates a 10-digit phone number.
    Sets self.phone to the validated number, or None if cancelled.
    """

    def __init__(self, parent, movie_name, seat_labels, total, price):
        self.phone = None
        self.win = tk.Toplevel(parent)
        self.win.title("Contact Details")
        self.win.configure(bg=BG)
        self.win.resizable(False, False)
        self.win.grab_set()   # modal
        centre(self.win, 440, 460)

        tk.Frame(self.win, bg=ACCENT, height=5).pack(fill="x")

        # Header
        lbl(self.win, "Almost There!", font=FH2, fg=TEXT).pack(pady=(22, 2))
        lbl(self.win, "We'll send your confirmation to this number",
            font=FXS, fg=TEXT3).pack(pady=(0, 14))

        # Booking summary card
        summary = tk.Frame(self.win, bg=BG3, padx=22, pady=14,
                           highlightthickness=1, highlightbackground=CARD_BDR)
        summary.pack(padx=30, fill="x")
        seats_str = ", ".join(seat_labels)
        for k, v in [("Movie", movie_name),
                     ("Seats", seats_str),
                     ("Total", f"₹{total:.2f}")]:
            row = tk.Frame(summary, bg=BG3)
            row.pack(fill="x", pady=3)
            lbl(row, k, font=FXS, fg=TEXT3, bg=BG3, width=8, anchor="w").pack(side="left")
            lbl(row, v, font=("Segoe UI", 10, "bold"), fg=TEXT, bg=BG3).pack(side="left", padx=6)

        # Phone entry
        pf = tk.Frame(self.win, bg=BG, padx=30)
        pf.pack(fill="x", pady=(18, 0))

        lbl(pf, "Mobile Number", font=("Segoe UI", 9, "bold"), fg=TEXT2).pack(anchor="w")
        lbl(pf, "10 digits, starting with 6–9  (e.g. 9876543210)",
            font=FXS, fg=TEXT3).pack(anchor="w", pady=(1, 4))

        # Prefix label + entry side by side
        row = tk.Frame(pf, bg=BG)
        row.pack(fill="x")
        lbl(row, "+91", font=("Segoe UI", 11, "bold"), fg=GOLD, bg=BG4,
            padx=10, pady=8).pack(side="left")
        self._phone_var = tk.StringVar()
        self._phone_var.trace("w", self._on_type)
        self._phone_entry = tk.Entry(
            row, textvariable=self._phone_var,
            bg=BG3, fg=TEXT, insertbackground=TEXT2,
            relief="flat", font=("Segoe UI", 13), bd=6,
            highlightthickness=1, highlightbackground=CARD_BDR,
            highlightcolor=ACCENT, width=18)
        self._phone_entry.pack(side="left", fill="x", expand=True)

        self._err_lbl = tk.Label(pf, text="", font=FXS, fg=ERR_FG,
                                 bg=BG, anchor="w", justify="left")
        self._err_lbl.pack(anchor="w", pady=(4, 0))

        self._char_lbl = tk.Label(pf, text="0 / 10 digits",
                                  font=FXS, fg=TEXT3, bg=BG, anchor="e")
        self._char_lbl.pack(fill="x")

        # Buttons
        bf = tk.Frame(self.win, bg=BG, padx=30, pady=16)
        bf.pack(fill="x")
        btn(bf, "Confirm & Book", self._confirm, w=20).pack(side="right", padx=(6, 0))
        ghost_btn(bf, "Cancel", self.win.destroy, w=12).pack(side="right")

        self.win.bind("<Return>", lambda e: self._confirm())
        self._phone_entry.focus_set()

    def _on_type(self, *_):
        raw = self._phone_var.get()
        # Strip non-digits silently
        digits_only = re.sub(r"\D", "", raw)
        if digits_only != raw:
            self._phone_var.set(digits_only)
            self._phone_entry.icursor(len(digits_only))
        n = len(digits_only)
        self._char_lbl.config(text=f"{n} / 10 digits",
                               fg=OK_FG if n == 10 else TEXT3)
        # Live feedback
        if n > 0:
            ok, msg = backend.validate_phone_number(digits_only)
            if ok:
                self._phone_entry.config(highlightbackground=SUCCESS)
                self._err_lbl.config(text="✓ Valid number", fg=OK_FG)
            elif n == 10:
                self._phone_entry.config(highlightbackground=ACCENT)
                self._err_lbl.config(text=f"✗ {msg.split(chr(10))[0]}", fg=ERR_FG)
            else:
                self._phone_entry.config(highlightbackground=CARD_BDR)
                self._err_lbl.config(text="")

    def _confirm(self):
        phone = self._phone_var.get().strip()
        ok, result = backend.validate_phone_number(phone)
        if not ok:
            self._phone_entry.config(highlightbackground=ACCENT)
            self._err_lbl.config(text=f"✗ {result}", fg=ERR_FG)
            return
        self.phone = result
        self.win.destroy()


# ═══════════════════════════════════════════════════════════
# SEAT PICKER
# ═══════════════════════════════════════════════════════════

class SeatPickerWindow:
    def __init__(self, parent, user, movie_id, on_done=None):
        self.parent   = parent
        self.user     = user
        self.movie_id = movie_id
        self.on_done  = on_done
        self.selected = set()
        self._running = True

        movie = backend.get_movie_by_id(movie_id)
        self.movie = movie
        self.rows  = movie["rows"]
        self.cols  = movie["cols"]
        self.price = movie["ticket_price"]

        self.win = tk.Toplevel(parent)
        self.win.title(f"Select Seats — {movie['movie_name']}")
        self.win.configure(bg=BG)
        self.win.resizable(True, True)
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._refresh_seats()
        self._poll()

    def _build_ui(self):
        movie = self.movie
        tk.Frame(self.win, bg=ACCENT, height=5).pack(fill="x")

        top = tk.Frame(self.win, bg=BG2, pady=12)
        top.pack(fill="x", padx=0)
        lbl(top, movie["movie_name"], font=FH3, fg=TEXT, bg=BG2).pack()
        info = (f"{movie['duration']} mins  ·  {movie['rating']}  "
                f"·  ₹{movie['ticket_price']:.0f} per seat")
        lbl(top, info, font=FXS, fg=TEXT3, bg=BG2).pack()
        lbl(top, f"Director: {movie['director']}   Cast: {movie['cast']}",
            font=FXS, fg=TEXT3, bg=BG2).pack()

        sep(self.win, bg=CARD_BDR, pady=0)

        leg = tk.Frame(self.win, bg=BG, pady=8)
        leg.pack()
        for col, txt in [(C_AVAIL, "Available"), (C_MINE, "Your Pick"),
                         (C_LOCKED, "Held by Other"), (C_BOOKED, "Booked")]:
            dot = tk.Frame(leg, bg=col, width=16, height=16,
                           highlightthickness=1, highlightbackground=_darken(col))
            dot.pack(side="left", padx=(12, 4))
            lbl(leg, txt, font=FXS, fg=TEXT2).pack(side="left", padx=(0, 12))

        scr = tk.Frame(self.win, bg=BG, pady=4)
        scr.pack()
        screen_w = self.cols * (SEAT_SIZE + SEAT_GAP) + 80
        tk.Frame(scr, bg=C_SCREEN, height=16, width=min(screen_w, 860)).pack()
        lbl(scr, "◀  S C R E E N  ▶", font=("Segoe UI", 8, "bold"), fg=TEXT3).pack()

        canvas_w = self.cols * (SEAT_SIZE + SEAT_GAP) + 90
        canvas_h = min(480, self.rows * (SEAT_SIZE + SEAT_GAP) + 50)
        wrap = tk.Frame(self.win, bg=BG)
        wrap.pack(padx=20, pady=4)
        hscroll = tk.Scrollbar(wrap, orient="horizontal", bg=BG3)
        vscroll = tk.Scrollbar(wrap, orient="vertical", bg=BG3)
        self.canvas = tk.Canvas(wrap, bg=BG, highlightthickness=0,
                                width=min(canvas_w, 860), height=canvas_h,
                                xscrollcommand=hscroll.set,
                                yscrollcommand=vscroll.set)
        hscroll.config(command=self.canvas.xview)
        vscroll.config(command=self.canvas.yview)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vscroll.grid(row=0, column=1, sticky="ns")
        hscroll.grid(row=1, column=0, sticky="ew")
        self.seat_frame = tk.Frame(self.canvas, bg=BG)
        self.canvas_win = self.canvas.create_window((0, 0), window=self.seat_frame, anchor="nw")
        self.seat_frame.bind("<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        bot = tk.Frame(self.win, bg=BG2, pady=12)
        bot.pack(fill="x")
        self.sel_lbl = lbl(bot, "No seats selected", font=FM, fg=TEXT3, bg=BG2)
        self.sel_lbl.pack(side="left", padx=20)
        self.amt_lbl = lbl(bot, "", font=("Georgia", 14, "bold"), fg=GOLD, bg=BG2)
        self.amt_lbl.pack(side="left", padx=8)
        self.timer_lbl = lbl(bot, "", font=FXS, fg=WARN, bg=BG2)
        self.timer_lbl.pack(side="left", padx=12)
        ghost_btn(bot, "Cancel", self._on_close, w=10).pack(side="right", padx=12)
        btn(bot, "Confirm Booking", self._confirm, w=18).pack(side="right", padx=6)
        self.seat_btns = {}

    def _refresh_seats(self):
        seat_map = backend.get_seat_map(self.movie_id, self.user["user_id"])
        rows_dict = {}
        for s in seat_map:
            rows_dict.setdefault(s["label"][0], []).append(s)
        for w in self.seat_frame.winfo_children():
            w.destroy()
        self.seat_btns.clear()
        ROW_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for ri, row_letter in enumerate(ROW_LETTERS[:self.rows]):
            seats_in_row = rows_dict.get(row_letter, [])
            seats_in_row.sort(key=lambda s: int(s["label"][1:]))
            row_frame = tk.Frame(self.seat_frame, bg=BG)
            row_frame.pack(anchor="w", pady=SEAT_GAP // 2)
            lbl(row_frame, row_letter, font=("Courier New", 10, "bold"),
                fg=TEXT3, bg=BG, width=2).pack(side="left", padx=(4, 8))
            for s in seats_in_row:
                lbl_text = s["label"]
                status   = s["status"]
                col_num  = int(lbl_text[1:])
                if col_num > 1 and (col_num - 1) % 3 == 0:
                    tk.Frame(row_frame, bg=BG, width=AISLE_GAP).pack(side="left")
                if status == "booked":
                    bg_col, state, cursor = C_BOOKED, "disabled", "arrow"
                elif status == "locked_by_other":
                    bg_col, state, cursor = C_LOCKED, "disabled", "arrow"
                elif status == "locked_by_me":
                    bg_col, state, cursor = C_MINE, "normal", "hand2"
                else:
                    bg_col, state, cursor = C_AVAIL, "normal", "hand2"
                seat_btn = tk.Button(
                    row_frame, text=str(col_num),
                    width=2, height=1,
                    bg=bg_col, fg=BG,
                    activebackground=_darken(bg_col),
                    relief="flat", font=("Segoe UI", 8, "bold"),
                    cursor=cursor, state=state,
                    command=lambda l=lbl_text, st=status: self._toggle_seat(l, st))
                seat_btn.pack(side="left", padx=SEAT_GAP // 2)
                self.seat_btns[lbl_text] = (seat_btn, status)
            lbl(row_frame, row_letter, font=("Courier New", 10, "bold"),
                fg=TEXT3, bg=BG, width=2).pack(side="left", padx=(8, 2))
        self._update_status_bar()

    def _toggle_seat(self, seat_label, current_status):
        if current_status == "locked_by_me":
            # Deselect: remove this seat, re-lock only the remaining ones
            self.selected.discard(seat_label)
            # Release all current locks, then re-acquire for remaining seats
            backend.release_locks(self.movie_id, self.user["user_id"])
            if self.selected:
                ok, msg = backend.lock_seats(
                    self.movie_id, list(self.selected), self.user["user_id"])
                if not ok:
                    messagebox.showerror("Lock Error", msg)
                    self.selected.clear()
            self._refresh_seats()
            return
        # Select: add this seat and lock all selected seats together
        self.selected.add(seat_label)
        ok, msg = backend.lock_seats(
            self.movie_id, list(self.selected), self.user["user_id"])
        if not ok:
            self.selected.discard(seat_label)
            messagebox.showerror("Seat Unavailable", msg)
        self._refresh_seats()

    def _update_status_bar(self):
        n = len(self.selected)
        if n == 0:
            self.sel_lbl.config(text="No seats selected", fg=TEXT3)
            self.amt_lbl.config(text="")
        else:
            labels_str = ", ".join(sorted(self.selected, key=lambda x: (x[0], int(x[1:]))))
            self.sel_lbl.config(text=f"Selected ({n}): {labels_str}", fg=TEXT)
            self.amt_lbl.config(text=f"₹{self.price * n:.0f}")

    def _poll(self):
        if not self._running:
            return
        self._refresh_seats()
        if self.selected:
            self.timer_lbl.config(text="Seat hold refreshes every 4s — confirm to book!")
        else:
            self.timer_lbl.config(text="")
        self.win.after(4000, self._poll)

    def _confirm(self):
        if not self.selected:
            messagebox.showwarning("No Seats", "Select at least one seat.")
            return

        sorted_labels = sorted(self.selected, key=lambda x: (x[0], int(x[1:])))
        total = self.price * len(sorted_labels)

        # ── Step 1: collect & validate phone number ──────────
        dlg = PhoneDialog(self.win, self.movie["movie_name"], sorted_labels, total, self.price)
        self.win.wait_window(dlg.win)
        if dlg.phone is None:
            return   # user cancelled the phone dialog

        phone = dlg.phone

        # ── Step 2: final confirmation ────────────────────────
        msg = (f"Confirm booking?\n\n"
               f"Movie:  {self.movie['movie_name']}\n"
               f"Seats:  {', '.join(sorted_labels)}\n"
               f"Total:  ₹{total:.0f}\n"
               f"SMS to: +91 {phone}")
        if not messagebox.askyesno("Confirm Booking", msg):
            return

        # ── Step 3: persist booking ───────────────────────────
        ok, bid_or_msg, amount = backend.confirm_booking(
            self.user["user_id"], self.movie_id, sorted_labels, phone)

        if ok:
            # ── Step 4: send SMS confirmation ─────────────────
            backend.send_sms_confirmation(
                phone, bid_or_msg, self.movie["movie_name"], sorted_labels, amount)

            self._running = False
            self.win.destroy()
            if self.on_done:
                self.on_done()
            BookingConfirmedWin(
                None, bid_or_msg, self.movie["movie_name"],
                sorted_labels, amount, phone)
        else:
            messagebox.showerror("Booking Failed", bid_or_msg)
            self._refresh_seats()

    def _on_close(self):
        self._running = False
        backend.release_locks(self.movie_id, self.user["user_id"])
        self.win.destroy()
        if self.on_done:
            self.on_done()


# ═══════════════════════════════════════════════════════════
# BOOKING CONFIRMED POPUP
# ═══════════════════════════════════════════════════════════

class BookingConfirmedWin:
    def __init__(self, parent, bid, movie_name, seat_labels, total, phone=""):
        self.win = tk.Tk() if parent is None else tk.Toplevel(parent)
        style_win(self.win, "Booking Confirmed!", 460, 440)
        tk.Frame(self.win, bg=SUCCESS, height=6).pack(fill="x")

        lbl(self.win, "BOOKING CONFIRMED", font=("Georgia", 16, "bold"), fg=SUCCESS).pack(pady=(22, 2))
        lbl(self.win, "Your tickets are booked!", font=FXS, fg=TEXT3).pack(pady=(0, 16))

        card = tk.Frame(self.win, bg=BG2, padx=32, pady=20,
                        highlightthickness=1, highlightbackground=CARD_BDR)
        card.pack(padx=30, fill="x", pady=4)

        seats_str = ", ".join(seat_labels)
        rows_data = [
            ("Booking ID", f"#{bid}"),
            ("Movie",      movie_name),
            ("Seats",      seats_str),
            ("Total Paid", f"₹{total:.2f}"),
        ]
        if phone:
            rows_data.append(("SMS Sent To", f"+91 {phone}"))

        for k, v in rows_data:
            row = tk.Frame(card, bg=BG2)
            row.pack(fill="x", pady=4)
            lbl(row, k, font=FXS, fg=TEXT3, bg=BG2, width=12, anchor="w").pack(side="left")
            lbl(row, v, font=("Segoe UI", 10, "bold"), fg=TEXT, bg=BG2).pack(side="left", padx=8)

        if phone:
            sms_note = tk.Frame(self.win, bg=BG3, padx=20, pady=8)
            sms_note.pack(padx=30, fill="x", pady=(4, 0))
            lbl(sms_note, f"📱  Confirmation SMS sent to +91 {phone}",
                font=FXS, fg=SUCCESS, bg=BG3).pack()

        tk.Frame(self.win, bg=CARD_BDR, height=1).pack(fill="x", padx=30, pady=12)
        btn(self.win, "Done", self.win.destroy, w=22).pack()

        if parent is None:
            self.win.mainloop()


# ═══════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    backend.initialize_database()
    root = tk.Tk()
    LoginWindow(root)
    root.mainloop()