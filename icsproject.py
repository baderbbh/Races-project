import os
import mysql.connector
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# ---------- DB CONFIG ----------
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "16424521",
    "database": "RACING",
    "autocommit": False
}

def getDb():
    return mysql.connector.connect(**DB_CONFIG)

# Thin wrapper to run a statement with parameters and optionally fetch rows
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

# ---------- GUI ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Horse Racing DB")
        self.geometry("980x640")

        nb = ttk.Notebook(self)
        self.adminTab = AdminTab(nb)
        self.guestTab = GuestTab(nb)
        nb.add(self.adminTab, text="Admin")
        nb.add(self.guestTab, text="Guest")
        nb.pack(fill="both", expand=True)

# ---------- Admin Tab ----------
class AdminTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        # Buttons (Admin features)
        grid = ttk.Frame(self)
        grid.pack(side="top", fill="x", padx=12, pady=12)

        ttk.Button(grid, text="Add New Race (+ results)", command=self.addRace).grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Button(grid, text="Delete Owner (and related)", command=self.deleteOwner).grid(row=0, column=1, padx=6, pady=6, sticky="w")
        ttk.Button(grid, text="Move Horse to Another Stable", command=self.moveHorse).grid(row=0, column=2, padx=6, pady=6, sticky="w")
        ttk.Button(grid, text="Approve New Trainer", command=self.approveTrainer).grid(row=0, column=3, padx=6, pady=6, sticky="w")

        # Result / log area
        self.log = tk.Text(self, height=18)
        self.log.pack(fill="both", expand=True, padx=12, pady=12)

    def addRace(self):
        """
        Requirement: Add a new race *with results*.
        Prompts for Race fields + a compact results entry.
        """
        try:
            raceId = simpledialog.askstring("Race", "raceId:")
            if not raceId: return
            raceName = simpledialog.askstring("Race", "raceName:")
            trackName = simpledialog.askstring("Race", "trackName:")
            raceDate = simpledialog.askstring("Race", "raceDate (YYYY-MM-DD):")
            raceTime = simpledialog.askstring("Race", "raceTime (HH:MM):")


            resultsWindow = tk.Toplevel(self)
            resultsWindow.title("Race Results")
            tk.Label(resultsWindow, text="Enter results (one per line): horseId,results,prize").pack(padx=8, pady=8)
            txt = tk.Text(resultsWindow, width=60, height=12)
            txt.pack(padx=8, pady=8)

            def onOk():
                lines = txt.get("1.0", "end").strip().splitlines()
                parsed = []
                for line in lines:
                    if not line.strip():
                        continue
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) != 3:
                        messagebox.showerror("Error", f"Bad line: {line}\nUse horseId,results,prize")
                        return
                    horseId, results, prizeStr = parts
                    try:
                        prize = float(prizeStr)
                    except:
                        messagebox.showerror("Error", f"Prize must be numeric: {line}")
                        return
                    parsed.append((raceId, horseId, results, prize))

                # Transaction: insert Race then RaceResults rows
                conn = getDb()
                try:
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO Race (raceId, raceName, trackName, raceDate, raceTime) VALUES (%s,%s,%s,%s,%s)",
                        (raceId, raceName, trackName, raceDate, raceTime)
                    )
                    cur.executemany(
                        "INSERT INTO RaceResults (raceId, horseId, results, prize) VALUES (%s,%s,%s,%s)",
                        parsed
                    )
                    # Toggle this commit for permanent vs. temporary:
                    # conn.commit()
                    self.log.insert("end", f"[OK] Added race {raceId} and {len(parsed)} results (NOT COMMITTED).\n")
                except Exception as e:
                    conn.rollback()
                    messagebox.showerror("DB Error", str(e))
                finally:
                    conn.close()
                    resultsWindow.destroy()

            ttk.Button(resultsWindow, text="Save (no commit)", command=onOk).pack(pady=8)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def deleteOwner(self):
        """
        Requirement: Delete an owner and ALL related info.
        We’ll *prefer* calling a stored procedure (see section 3).
        If the stored proc isn't created, we fallback to manual deletes.
        """
        ownerId = simpledialog.askstring("Delete Owner", "ownerId:")
        if not ownerId: return

        conn = getDb()
        try:
            cur = conn.cursor()
            try:
                # Try stored proc first
                cur.callproc("sp_delete_owner", [ownerId])
                # conn.commit()
                self.log.insert("end", f"[OK] sp_delete_owner('{ownerId}') executed (NOT COMMITTED).\n")
            except Exception:
                # Fallback (manual): delete from Owns then Owner
                cur.execute("DELETE FROM Owns WHERE ownerId = %s", (ownerId,))
                cur.execute("DELETE FROM Owner WHERE ownerId = %s", (ownerId,))
                # conn.commit()
                self.log.insert("end", f"[OK] Deleted owner '{ownerId}' and related Owns (NOT COMMITTED).\n")
        except Exception as e:
            conn.rollback()
            messagebox.showerror("DB Error", str(e))
        finally:
            conn.close()

    def moveHorse(self):
        """
        Requirement: Given horseId, move to another stable.
        """
        horseId = simpledialog.askstring("Move Horse", "horseId:")
        if not horseId: return
        newStableId = simpledialog.askstring("Move Horse", "new stableId:")
        if not newStableId: return

        conn = getDb()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE Horse SET stableId = %s WHERE horseId = %s", (newStableId, horseId))
            # conn.commit()
            self.log.insert("end", f"[OK] Horse '{horseId}' moved to '{newStableId}' (NOT COMMITTED).\n")
        except Exception as e:
            conn.rollback()
            messagebox.showerror("DB Error", str(e))
        finally:
            conn.close()

    def approveTrainer(self):
        """
        Requirement: Approve a new trainer to join a stable.
        Simplest flow: insert a new Trainer row (approved) tied to a stable.
        """
        trainerId = simpledialog.askstring("Approve Trainer", "trainerId:")
        if not trainerId: return
        lname = simpledialog.askstring("Approve Trainer", "last name:")
        fname = simpledialog.askstring("Approve Trainer", "first name:")
        stableId = simpledialog.askstring("Approve Trainer", "stableId to join:")
        if not all([lname, fname, stableId]):
            return

        conn = getDb()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO Trainer (trainerId, lname, fname, stableId) VALUES (%s,%s,%s,%s)",
                (trainerId, lname, fname, stableId)
            )
            # conn.commit()
            self.log.insert("end", f"[OK] Trainer '{trainerId}' approved for stable '{stableId}' (NOT COMMITTED).\n")
        except Exception as e:
            conn.rollback()
            messagebox.showerror("DB Error", str(e))
        finally:
            conn.close()

# ---------- Guest Tab ----------
class GuestTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        # Controls
        control = ttk.Frame(self)
        control.pack(side="top", fill="x", padx=12, pady=8)

        # 1) Browse horses (name/age) + trainer names by owner last name
        ttk.Label(control, text="Owner Last Name:").grid(row=0, column=0, sticky="w")
        self.ownerLnameVar = tk.StringVar()
        ttk.Entry(control, textvariable=self.ownerLnameVar, width=18).grid(row=0, column=1, padx=6)
        ttk.Button(control, text="Search Horses by Owner", command=self.queryHorsesByOwner).grid(row=0, column=2, padx=6)

        # 2) Trainers who trained winners (first place) — with columns for trainer, horse, race
        ttk.Button(control, text="Trainers With Winners", command=self.queryTrainersWithWinners).grid(row=1, column=0, pady=6, sticky="w")

        # 3) Trainers & total winnings (sorted)
        ttk.Button(control, text="Trainer Total Winnings", command=self.queryTrainerTotals).grid(row=1, column=1, pady=6, sticky="w")

        # 4) Tracks + count(races) + total participants (horses)
        ttk.Button(control, text="Track Stats", command=self.queryTrackStats).grid(row=1, column=2, pady=6, sticky="w")

        # Results table
        self.tree = ttk.Treeview(self, columns=[], show="headings", height=22)
        self.tree.pack(fill="both", expand=True, padx=12, pady=8)

    def setTable(self, headers, rows):
        # clear
        self.tree.delete(*self.tree.get_children())
        for c in self.tree["columns"]:
            self.tree.heading(c, text="")
        self.tree["columns"] = headers
        for h in headers:
            self.tree.heading(h, text=h)
            self.tree.column(h, width=160, stretch=True)
        for r in rows:
            self.tree.insert("", "end", values=r)

    def queryHorsesByOwner(self):
        """
        Names & ages of horses + names of their trainer for horses owned by people with given last name.
        Note: Schema has no direct trainer->horse mapping; we assume a horse’s trainer works at the same stable.
        """
        lname = self.ownerLnameVar.get().strip()
        if not lname:
            messagebox.showinfo("Info", "Enter an owner last name.")
            return

        sql = """
        SELECT h.horseName, h.age, t.fname AS trainerFirst, t.lname AS trainerLast
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
        """
        Trainers who have trained first-place winners.
        Show trainer details + winning horse + winning race.
        """
        sql = """
        SELECT t.fname AS trainerFirst, t.lname AS trainerLast,
               h.horseName, r.raceName, r.trackName, r.raceDate, r.raceTime
        FROM Trainer t
        JOIN Horse h ON h.stableId = t.stableId
        JOIN RaceResults rr ON rr.horseId = h.horseId AND rr.results = 'first'
        JOIN Race r ON r.raceId = rr.raceId
        ORDER BY t.lname, t.fname, r.raceDate, r.raceTime
        """
        try:
            rows, conn = runQuery(sql, fetch=True)
            conn.close()
            self.setTable(
                ["Trainer First", "Trainer Last", "Horse", "Race", "Track", "Date", "Time"],
                rows
            )
        except Exception as e:
            messagebox.showerror("DB Error", str(e))

    def queryTrainerTotals(self):
        """
        Trainer + total prize money of horses (at their stable) — sorted by winnings desc.
        """
        sql = """
        SELECT t.fname AS trainerFirst, t.lname AS trainerLast, COALESCE(SUM(rr.prize), 0) AS totalPrize
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
        """
        Track + count of races + total number of horses participating (across all races on that track).
        """
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

if __name__ == "__main__":
    App().mainloop()
