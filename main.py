# main.py
import tkinter as tk
from tkinter import ttk
from ui.main_window import MapScriptGeneratorApp

if __name__ == "__main__":
    root = tk.Tk()
    root.title("CoD2 MP Map Script Generator")
    root.geometry("1100x780")
    root.resizable(True, True)

    app = MapScriptGeneratorApp(root)
    root.mainloop()