# ============================================================
# main.py - Entry point for the Movie Booking System
#
# REQUIREMENTS:
#   - Python 3.8+ (no external libraries needed)
#   - tkinter  (built-in with Python)
#   - sqlite3  (built-in with Python)
#
# HOW TO RUN:
#   python main.py
#
# DEFAULT CREDENTIALS:
#   Admin  →  username: admin   | password: admin123
#   User   →  username: user1   | password: user123
# ============================================================

import tkinter as tk
import backend
import frontend


def main():
    # Step 1: Set up the database (creates movie.db and tables if needed)
    backend.initialize_database()

    # Step 2: Launch the login window
    root = tk.Tk()
    frontend.LoginWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()