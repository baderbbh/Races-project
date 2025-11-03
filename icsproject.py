import mysql.connector
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import datetime

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "06062003",
    "database": "RACING",
    "autocommit": False
}

def getDb():
    return mysql.connector.connect(**DB_CONFIG)

def runQuery(sql, params=None, fetch=False, many=False):
    conn = getDb()
    try:
        cur = conn.cursor()
        if many:
            cur.executemany(sql, params or [])
        else:
            cur.execute(sql, params or ())
        rows = cur.fetchall() if fetch else None
        return rows, conn
    except Exception as e:
        conn.rollback()
        raise e

def setup_trigger():
    conn = getDb()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS old_info (
                horseId      VARCHAR(15) NOT NULL,
                horseName    VARCHAR(15) NOT NULL,
                age          INT,
                gender       CHAR(1),
                registration INT NOT NULL,
                stableId     VARCHAR(30) NOT NULL,
                deleted_at   DATETIME,
                PRIMARY KEY (horseId, deleted_at)
            )
        """)
        cur.execute("""
            SELECT TRIGGER_NAME
            FROM information_schema.TRIGGERS
            WHERE TRIGGER_SCHEMA = %s AND TRIGGER_NAME = 'trg_horse_delete'
        """, (DB_CONFIG["database"],))
        exists = cur.fetchone()
        if not exists:
            cur.execute("""
                CREATE TRIGGER trg_horse_delete
                BEFORE DELETE ON Horse
                FOR EACH ROW
                BEGIN
                    INSERT INTO old_info (horseId, horseName, age, gender, registration, stableId, deleted_at)
                    VALUES (OLD.horseId, OLD.horseName, OLD.age, OLD.gender, OLD.registration, OLD.stableId, NOW());
                END
            """)
            conn.commit()
    except Exception as e:
        conn.rollback()
        print("trigger error:", e)
    finally:
        conn.close()

def setup_stored_procedure():
    conn = getDb()
    try:
        cur = conn.cursor()
        cur.execute("""
        CREATE PROCEDURE sp_delete_owner(IN p_ownerId VARCHAR(15))
        BEGIN
            DELETE FROM Owns WHERE ownerId = p_ownerId;
            DELETE FROM Owner WHERE ownerId = p_ownerId;
        END
        """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("procedure error:", e)
    finally:
        conn.close()

class AdminView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="Content.TFrame")
        top = ttk.Frame(self, style="Content.TFrame")
        top.pack(side="top", fill="x", padx=12, pady=12)
        self.btn_add = ttk.Button(top, text="Add Race", command=self.addRace)
        self.btn_add.grid(row=0, column=0, padx=6, pady=6, sticky="w")
        self.btn_del = ttk.Button(top, text="Delete Owner", command=self.deleteOwner)
        self.btn_del.grid(row=0, column=1, padx=6, pady=6, sticky="w")
        self.btn_move = ttk.Button(top, text="Move Horse", command=self.moveHorse)
        self.btn_trainer = ttk.Button(top, text="Approve Trainer", command=self.approveTrainer)
        self.btn_move.grid(row=0, column=2, padx=6, pady=6, sticky="w")
        self.btn_trainer.grid(row=0, column=3, padx=6, pady=6, sticky="w")
        self.log = tk.Text(self, bg="#0f172a", fg="#e2e8f0", insertbackground="#e2e8f0", borderwidth=0, font=("Segoe UI", 10))
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def addRace(self):
        raceId = simpledialog.askstring("Race", "raceId:")
        if not raceId: return
        raceName = simpledialog.askstring("Race", "raceName:")
        trackName = simpledialog.askstring("Race", "trackName:")
        raceDate = simpledialog.askstring("Race", "raceDate (YYYY-MM-DD):")
        raceTime = simpledialog.askstring("Race", "raceTime (HH:MM):")
        try:
            datetime.datetime.strptime(raceDate, "%Y-%m-%d")
            datetime.datetime.strptime(raceTime, "%H:%M")
        except:
            messagebox.showerror("Error", "Invalid date/time format.")
            return
        rows, conn_t = runQuery("SELECT trackName FROM Track WHERE trackName = %s", (trackName,), fetch=True)
        conn_t.close()
        if not rows:
            messagebox.showerror("Error", f"Track '{trackName}' does not exist.")
            return
        win = tk.Toplevel(self)
        win.title("Race Results")
        win.configure(bg="#0f172a")
        tk.Label(win, text="horseId,results,prize per line", bg="#0f172a", fg="#e2e8f0").pack(padx=8, pady=8)
        txt = tk.Text(win, width=60, height=14, bg="#020617", fg="#e2e8f0", insertbackground="white", borderwidth=0)
        txt.pack(padx=8, pady=8)
        def save_results():
            lines = txt.get("1.0", "end").strip().splitlines()
            parsed = []
            horseIds = []
            for line in lines:
                if not line.strip():
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) != 3:
                    messagebox.showerror("Error", f"Bad line: {line}")
                    return
                hid, res, pstr = parts
                try:
                    prize = float(pstr)
                except:
                    messagebox.showerror("Error", f"Prize not number: {line}")
                    return
                parsed.append((raceId, hid, res, prize))
                horseIds.append(hid)
            if horseIds:
                placeholders = ",".join(["%s"] * len(horseIds))
                sql_check = f"SELECT horseId FROM Horse WHERE horseId IN ({placeholders})"
                rows, conn_h = runQuery(sql_check, tuple(horseIds), fetch=True)
                conn_h.close()
                existing = {r[0] for r in rows}
                missing = [h for h in horseIds if h not in existing]
                if missing:
                    messagebox.showerror("Error", "Missing horse(s): " + ", ".join(missing))
                    return
            conn = getDb()
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO Race (raceId, raceName, trackName, raceDate, raceTime) VALUES (%s,%s,%s,%s,%s)",
                    (raceId, raceName, trackName, raceDate, raceTime)
                )
                if parsed:
                    cur.executemany(
                        "INSERT INTO RaceResults (raceId, horseId, results, prize) VALUES (%s,%s,%s,%s)",
                        parsed
                    )
                conn.commit()
                self.log.insert("end", f"[OK] Added race {raceId} ({len(parsed)} results)\n")
            except Exception as e:
                conn.rollback()
                messagebox.showerror("DB Error", str(e))
            finally:
                conn.close()
                win.destroy()
        ttk.Button(win, text="Save", command=save_results).pack(pady=8)

    def deleteOwner(self):
        ownerId = simpledialog.askstring("Delete Owner", "ownerId:")
        if not ownerId: return
        conn = getDb()
        try:
            cur = conn.cursor()
            try:
                cur.callproc("sp_delete_owner", [ownerId])
                conn.commit()
                self.log.insert("end", f"[OK] sp_delete_owner('{ownerId}') executed\n")
            except:
                cur.execute("DELETE FROM Owns WHERE ownerId = %s", (ownerId,))
                owns_deleted = cur.rowcount
                cur.execute("DELETE FROM Owner WHERE ownerId = %s", (ownerId,))
                owner_deleted = cur.rowcount
                conn.commit()
                if owner_deleted == 0:
                    self.log.insert("end", f"[WARN] owner '{ownerId}' not found\n")
                else:
                    self.log.insert("end", f"[OK] deleted owner '{ownerId}', {owns_deleted} owns\n")
        except Exception as e:
            conn.rollback()
            messagebox.showerror("DB Error", str(e))
        finally:
            conn.close()

    def moveHorse(self):
        horseId = simpledialog.askstring("Move Horse", "horseId:")
        if not horseId: return
        newStable = simpledialog.askstring("Move Horse", "new stableId:")
        if not newStable: return
        conn = getDb()
        try:
            cur = conn.cursor()
            cur.execute("SELECT horseId FROM Horse WHERE horseId = %s", (horseId,))
            if not cur.fetchone():
                messagebox.showerror("Error", "Horse not found")
                conn.close()
                return
            cur.execute("SELECT stableId FROM Stable WHERE stableId = %s", (newStable,))
            if not cur.fetchone():
                messagebox.showerror("Error", "Stable not found")
                conn.close()
                return
            cur.execute("UPDATE Horse SET stableId = %s WHERE horseId = %s", (newStable, horseId))
            conn.commit()
            self.log.insert("end", f"[OK] horse {horseId} → {newStable}\n")
        except Exception as e:
            conn.rollback()
            messagebox.showerror("DB Error", str(e))
        finally:
            conn.close()

    def approveTrainer(self):
        trainerId = simpledialog.askstring("Approve Trainer", "trainerId:")
        if not trainerId: return
        lname = simpledialog.askstring("Approve Trainer", "last name:")
        fname = simpledialog.askstring("Approve Trainer", "first name:")
        stableId = simpledialog.askstring("Approve Trainer", "stableId:")
        if not all([lname, fname, stableId]):
            return
        conn = getDb()
        try:
            cur = conn.cursor()
            cur.execute("SELECT stableId FROM Stable WHERE stableId = %s", (stableId,))
            if not cur.fetchone():
                messagebox.showerror("Error", "Stable not found")
                conn.close()
                return
            cur.execute("SELECT trainerId FROM Trainer WHERE trainerId = %s", (trainerId,))
            exists = cur.fetchone()
            if exists:
                cur.execute(
                    "UPDATE Trainer SET lname = %s, fname = %s, stableId = %s WHERE trainerId = %s",
                    (lname, fname, stableId, trainerId)
                )
                msg = f"[OK] trainer {trainerId} updated\n"
            else:
                cur.execute(
                    "INSERT INTO Trainer (trainerId, lname, fname, stableId) VALUES (%s,%s,%s,%s)",
                    (trainerId, lname, fname, stableId)
                )
                msg = f"[OK] trainer {trainerId} approved\n"
            conn.commit()
            self.log.insert("end", msg)
        except Exception as e:
            conn.rollback()
            messagebox.showerror("DB Error", str(e))
        finally:
            conn.close()

class GuestView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="Content.TFrame")
        bar = ttk.Frame(self, style="Content.TFrame")
        bar.pack(side="top", fill="x", padx=12, pady=12)
        ttk.Label(bar, text="Owner last name:").grid(row=0, column=0, sticky="w")
        self.ownerLnameVar = tk.StringVar()
        ttk.Entry(bar, textvariable=self.ownerLnameVar, width=20).grid(row=0, column=1, padx=6)
        ttk.Button(bar, text="Horses by owner", command=self.queryHorsesByOwner).grid(row=0, column=2, padx=6)
        ttk.Button(bar, text="Trainers with winners", command=self.queryTrainersWithWinners).grid(row=1, column=0, pady=6, sticky="w")
        ttk.Button(bar, text="Trainer total winnings", command=self.queryTrainerTotals).grid(row=1, column=1, pady=6, sticky="w")
        ttk.Button(bar, text="Track stats", command=self.queryTrackStats).grid(row=1, column=2, pady=6, sticky="w")
        self.tree = ttk.Treeview(self, columns=[], show="headings", height=22)
        self.tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def setTable(self, headers, rows):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = headers
        for h in headers:
            self.tree.heading(h, text=h)
            self.tree.column(h, width=150, stretch=True)
        if rows:
            for r in rows:
                self.tree.insert("", "end", values=r)
        else:
            self.tree.insert("", "end", values=["No data found"] + [""] * (len(headers) - 1))

    def queryHorsesByOwner(self):
        lname = self.ownerLnameVar.get().strip()
        if not lname:
            messagebox.showinfo("Info", "Enter last name.")
            return
        sql = """
        SELECT h.horseName, h.age, t.fname, t.lname
        FROM Owner o
        JOIN Owns ow ON ow.ownerId = o.ownerId
        JOIN Horse h ON h.horseId = ow.horseId
        JOIN Trainer t ON t.stableId = h.stableId
        WHERE o.lname = %s
        ORDER BY h.horseName, t.lname, t.fname
        """
        try:
            rows, conn = runQuery(sql, (lname,), fetch=True)
            conn.close()
            self.setTable(["Horse", "Age", "Trainer First", "Trainer Last"], rows)
        except Exception as e:
            messagebox.showerror("DB Error", str(e))

    def queryTrainersWithWinners(self):
        sql = """
        SELECT t.fname, t.lname, h.horseName, r.raceName, r.trackName, r.raceDate, r.raceTime
        FROM Trainer t
        JOIN Horse h ON h.stableId = t.stableId
        JOIN RaceResults rr ON rr.horseId = h.horseId AND rr.results = 'first'
        JOIN Race r ON r.raceId = rr.raceId
        ORDER BY t.lname, t.fname, r.raceDate, r.raceTime
        """
        try:
            rows, conn = runQuery(sql, fetch=True)
            conn.close()
            self.setTable(["Trainer First", "Trainer Last", "Horse", "Race", "Track", "Date", "Time"], rows)
        except Exception as e:
            messagebox.showerror("DB Error", str(e))

    def queryTrainerTotals(self):
        sql = """
        SELECT t.fname, t.lname, COALESCE(SUM(rr.prize), 0) AS totalPrize
        FROM Trainer t
        LEFT JOIN Horse h ON h.stableId = t.stableId
        LEFT JOIN RaceResults rr ON rr.horseId = h.horseId
        GROUP BY t.trainerId, t.fname, t.lname
        ORDER BY totalPrize DESC, t.lname, t.fname
        """
        try:
            rows, conn = runQuery(sql, fetch=True)
            conn.close()
            self.setTable(["Trainer First", "Trainer Last", "Total Prize"], rows)
        except Exception as e:
            messagebox.showerror("DB Error", str(e))

    def queryTrackStats(self):
        sql = """
        SELECT r.trackName,
               COUNT(DISTINCT r.raceId) AS raceCount,
               COUNT(rr.horseId) AS totalParticipants
        FROM Race r
        LEFT JOIN RaceResults rr ON rr.raceId = r.raceId
        GROUP BY r.trackName
        ORDER BY r.trackName
        """
        try:
            rows, conn = runQuery(sql, fetch=True)
            conn.close()
            self.setTable(["Track", "Race Count", "Total Participants"], rows)
        except Exception as e:
            messagebox.showerror("DB Error", str(e))

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Horse Racing DB")
        self.geometry("1050x650")
        self.configure(bg="#0f172a")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Sidebar.TFrame", background="#020617")
        style.configure("Content.TFrame", background="#0f172a")
        style.configure("TLabel", background="#0f172a", foreground="#e2e8f0")
        style.configure("SideButton.TButton", background="#020617", foreground="#e2e8f0", padding=8)
        style.map("SideButton.TButton", background=[("active", "#1d4ed8")])
        container = ttk.Frame(self, style="Content.TFrame")
        container.pack(fill="both", expand=True)
        self.sidebar = ttk.Frame(container, width=180, style="Sidebar.TFrame")
        self.sidebar.pack(side="left", fill="y")
        self.content = ttk.Frame(container, style="Content.TFrame")
        self.content.pack(side="right", fill="both", expand=True)
        self.adminView = AdminView(self.content)
        self.guestView = GuestView(self.content)
        self.current_view = None
        ttk.Label(self.sidebar, text="Menu", font=("Segoe UI", 13, "bold"), background="#020617", foreground="#e2e8f0").pack(pady=16)
        ttk.Button(self.sidebar, text="Admin", style="SideButton.TButton", command=self.show_admin).pack(fill="x", padx=12, pady=4)
        ttk.Button(self.sidebar, text="Guest", style="SideButton.TButton", command=self.show_guest).pack(fill="x", padx=12, pady=4)
        self.show_admin()

    def show_admin(self):
        if self.current_view:
            self.current_view.pack_forget()
        self.adminView.pack(fill="both", expand=True)
        self.current_view = self.adminView

    def show_guest(self):
        if self.current_view:
            self.current_view.pack_forget()
        self.guestView.pack(fill="both", expand=True)
        self.current_view = self.guestView

if __name__ == "__main__":
    setup_trigger()
    setup_stored_procedure()
    MainApp().mainloop()
