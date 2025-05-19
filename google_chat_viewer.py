import json
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox, simpledialog, StringVar
from datetime import datetime, timedelta
import os
from collections import Counter
import configparser
import hashlib
import webbrowser

SETTINGS_FILE = "viewer_settings.ini"
THEME_OPTIONS = [
    "flatly", "minty", "pulse", "sandstone", "united", "yeti",
    "darkly", "cyborg", "solar", "superhero", "morph", "vapor",
    "dark-amber", "dark-cyan", "dark-blue"
]

def parse_korean_utc(date_str):
    try:
        date_str = date_str.replace("오전", "AM").replace("오후", "PM").replace("초 UTC", "")
        parts = date_str.strip().split()
        if len(parts) >= 2:
            date_part = parts[0]
            month_part = parts[1]
            day_part = parts[2]
            time_part = " ".join(parts[4:])
            cleaned = f"{date_part}-{month_part}-{day_part} {time_part}"
            cleaned = cleaned.replace("년-", "-").replace("월-", "-").replace("일", "")
            dt = datetime.strptime(cleaned, "%Y-%m-%d %p %I시 %M분 %S")
            return dt
    except Exception:
        return None

class ChatViewerKST:
    def __init__(self, root):
        self.root = root
        self.root.title("Google Chat Viewer (KST)")
        self.root.geometry("1100x720")

        self.settings = configparser.ConfigParser()
        self.settings.optionxform = str
        self.tab_titles = {}
        self.filepaths = []
        self.tree_tabs = {}
        self.theme_var = StringVar()

        self.load_settings()

        # UI Layout
        ribbon = ttk.Frame(self.root, padding=5)
        ribbon.pack(fill=X)
        ttk.Button(ribbon, text="Open JSON", command=self.load_json_files, bootstyle="primary-outline").pack(side=LEFT, padx=5)
        ttk.Button(ribbon, text="Rename Tab", command=self.rename_tab, bootstyle="warning-outline").pack(side=LEFT, padx=5)
        ttk.Button(ribbon, text="Close Tab", command=self.close_tab, bootstyle="danger-outline").pack(side=LEFT, padx=5)
        theme_combo = ttk.Combobox(ribbon, textvariable=self.theme_var, values=THEME_OPTIONS, width=12, bootstyle="info")
        if self.settings.has_option("Viewer", "theme"):
            self.theme_var.set(self.settings.get("Viewer", "theme"))
        theme_combo.pack(side=RIGHT, padx=(5, 10))
        theme_combo.bind("<<ComboboxSelected>>", self.change_theme)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.bind("<<NotebookTabChanged>>", self.highlight_selected_tab)
        self.notebook.pack(fill=BOTH, expand=True)

        self.search_frame = ttk.Frame(self.root)
        self.search_frame.pack(fill=X)
        ttk.Label(self.search_frame, text="🔍 Search:").pack(side=LEFT, padx=5)
        self.search_entry = ttk.Entry(self.search_frame)
        self.search_entry.pack(side=LEFT, fill=X, expand=True)
        self.search_entry.bind("<Return>", self.apply_search)

        if self.filepaths:
            for path in self.filepaths:
                if os.path.exists(path):
                    self.load_file(path)

    

    def change_theme(self, event=None):
        theme = self.theme_var.get()
        self.root.style.theme_use(theme)
        self.settings.set("Viewer", "theme", theme)
        self.save_settings()

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                self.settings.read(SETTINGS_FILE)
            except configparser.DuplicateOptionError:
                os.remove(SETTINGS_FILE)
                return
            if self.settings.has_option("Viewer", "theme"):
                theme = self.settings.get("Viewer", "theme")
                self.root.style.theme_use(theme)
                self.theme_var.set(theme)
            
            if self.settings.has_option("Viewer", "recent_files"):
                self.filepaths = self.settings.get("Viewer", "recent_files").split("||")
            if self.settings.has_section("TabNames") and self.settings.has_section("PathMap"):
                tabnames = dict(self.settings.items("TabNames"))
                pathmap = dict(self.settings.items("PathMap"))
                for key, title in tabnames.items():
                    path = pathmap.get(key)
                    if path:
                        self.tab_titles[path] = title

    def path_hash(self, path):
        return hashlib.sha1(path.encode("utf-8")).hexdigest()

    def save_settings(self):
        config = configparser.ConfigParser()
        config.optionxform = str
        config.add_section("Viewer")
        config.set("Viewer", "theme", self.theme_var.get())
        config.set("Viewer", "recent_files", "||".join(self.filepaths))
        config.add_section("TabNames")
        config.add_section("PathMap")
        for path, title in self.tab_titles.items():
            key = self.path_hash(path)
            config.set("TabNames", key, title)
            config.set("PathMap", key, path)
        with open(SETTINGS_FILE, "w") as f:
            config.write(f)

    def load_json_files(self):
        files = filedialog.askopenfilenames(filetypes=[("JSON Files", "*.json")])
        for f in files:
            self.load_file(f)
        self.filepaths.extend([f for f in files if f not in self.filepaths])
        self.save_settings()

    def load_file(self, filepath):
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            messages = data.get("messages", [])
            participants = self.extract_participants(messages)
            title = self.tab_titles.get(filepath, " and ".join(participants) or os.path.basename(filepath))
            self.tab_titles[filepath] = title
            self.add_tab(title, messages, os.path.dirname(filepath))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def extract_participants(self, messages):
        names = [msg.get("creator", {}).get("name", "") for msg in messages if msg.get("creator")]
        return [n for n, _ in Counter(names).most_common(2)]

    def add_tab(self, title, messages, base_path):
        frame = ttk.Frame(self.notebook)
        tree = ttk.Treeview(frame, columns=("time", "name", "email", "text", "file"), show="headings", height=25)
        for col, txt, width in zip(tree["columns"], ["Time", "Name", "Email", "Text", "File"], [140, 140, 200, 400, 180]):
            tree.heading(col, text=txt)
            tree.column(col, width=width, anchor="w", stretch=False)
        yscroll = ttk.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        xscroll = ttk.Scrollbar(frame, orient=HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        yscroll.pack(side=RIGHT, fill=Y)
        xscroll.pack(side=BOTTOM, fill=X)
        tree.bind("<Double-1>", lambda e: self.on_double_click(e, tree, base_path))
        self.notebook.add(frame, text=title)
        self.tree_tabs[title] = {"tree": tree, "messages": messages, "base": base_path}
        self.populate_tree(title)

    def on_double_click(self, event, tree, base_path):
        selected = tree.focus()
        if not selected:
            return
        values = tree.item(selected, "values")
        col = tree.identify_column(event.x)
        if col == "#4":
            top = ttk.Toplevel(self.root)
            top.title("Full Message")
            txt = ttk.Text(top, wrap="word")
            txt.insert("1.0", values[3])
            txt.config(state="disabled")
            txt.pack(fill=BOTH, expand=True)
        elif col == "#5" and values[4]:
            fpath = os.path.join(base_path, values[4])
            if os.path.exists(fpath):
                webbrowser.open(fpath)
            else:
                messagebox.showwarning("Missing", f"File not found:\n{fpath}")

    def populate_tree(self, tab, search=""):
        data = self.tree_tabs.get(tab, {})
        tree = data.get("tree")
        msgs = data.get("messages", [])
        tree.delete(*tree.get_children())
        for msg in msgs:
            raw = msg.get("created_date", "")
            utc = parse_korean_utc(raw)
            kst = utc + timedelta(hours=9) if utc else None
            time_str = kst.strftime("%Y-%m-%d %H:%M") if kst else raw
            name = msg.get("creator", {}).get("name", "")
            email = msg.get("creator", {}).get("email", "")
            text = msg.get("text", "").strip()
            files = msg.get("attached_files", [])
            fname = files[0].get("export_name") if files else ""
            if any(search.lower() in field.lower() for field in [name, email, text, fname]):
                tree.insert("", "end", values=(time_str, name, email, text, fname))

    def apply_search(self, event=None):
        current = self.notebook.select()
        title = self.notebook.tab(current, "text")
        self.populate_tree(title, self.search_entry.get())

    def rename_tab(self):
        current = self.notebook.select()
        old = self.notebook.tab(current, "text").removeprefix("★ ")
        new = simpledialog.askstring("Rename Tab", f"Rename '{old}' to:")
        if new:
            self.notebook.tab(current, text="★ " + new if self.notebook.select() == current else new)
            self.tree_tabs[new] = self.tree_tabs.pop(old)
            for path in self.tab_titles:
                if self.tab_titles[path] == old:
                    self.tab_titles[path] = new
                    break
            self.save_settings()

    def highlight_selected_tab(self, event=None):
        current = self.notebook.select()
        for tab_id in self.notebook.tabs():
            title = self.notebook.tab(tab_id, "text")
            if title.startswith("★ "):
                self.notebook.tab(tab_id, text=title[2:])
        if current:
            current_text = self.notebook.tab(current, "text")
            if not current_text.startswith("★ "):
                self.notebook.tab(current, text="★ " + current_text)

    def close_tab(self):
        current = self.notebook.select()
        title = self.notebook.tab(current, "text").removeprefix("★ ")
        self.notebook.forget(current)
        if title in self.tree_tabs:
            base_path = self.tree_tabs[title]["base"]
            filepath = None
            for path, saved_title in self.tab_titles.items():
                if saved_title == title and os.path.dirname(path) == base_path:
                    filepath = path
                    break
            if filepath:
                if filepath in self.filepaths:
                    self.filepaths.remove(filepath)
                if filepath in self.tab_titles:
                    del self.tab_titles[filepath]
            del self.tree_tabs[title]
        self.save_settings()

if __name__ == "__main__":
    app = ttk.Window(themename="flatly")
    ChatViewerKST(app)
    app.mainloop()
