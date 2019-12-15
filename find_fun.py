import grp
import time
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font as tkfont
from tkinter import messagebox
from PIL import Image, ImageTk
from pwd import getpwuid
from tkinter import filedialog
from os import getcwd, stat
import stat as stat_u
from os.path import expanduser, basename, dirname, isdir, join
import queue
from helpers import searchtask, byte_format
import platform


class ProgramInfo:
    copyright = "Copyright © 2019 Paul Sobolik"
    version = "0.1"
    name = "Find Fun"


class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_rowconfigure(0, weight=1)

        self.master.bind("<Return>", self._do_search)

        self.recurse = tk.BooleanVar()
        self.search_pattern = tk.StringVar(value="*")
        self.search_folder = tk.StringVar(value=getcwd())
        self.status_text = tk.StringVar(value=ProgramInfo.copyright)
        self.count_text = tk.StringVar()

        self.search_stopped = False
        self.search_task = None
        self.results_queue = queue.Queue()
        self.progress_queue = queue.Queue()

        self._create_widgets()
        self._create_menu()
        self._set_up_icons()

    def _create_menu(self):
        def generate_event(event):
            focused = self.master.focus_get()
            if focused:
                focused.event_generate(event)

        def create_edit_menu():
            edit_menu = tk.Menu(menubar, tearoff=0)

            edit_menu.add_command(label="Cut",
                                  accelerator="Meta+X",
                                  command=lambda: generate_event("<<Cut>>"))
            edit_menu.add_command(label="Copy",
                                  accelerator="Meta+C",
                                  command=lambda: generate_event("<<Copy>>"))
            edit_menu.add_command(label="Paste",
                                  accelerator="Meta+V",
                                  command=lambda: generate_event("<<Paste>>"))
            if not mac:
                edit_menu.add_separator()
                edit_menu.add_command(label="Exit", command=root.quit)
            return edit_menu

        def create_help_menu():
            help_menu = tk.Menu(menubar, tearoff=0)
            if not mac:
                help_menu.add_command(label="About",
                                      command=show_about)
            return help_menu

        menubar = tk.Menu(root)
        mac = platform.system() == "Darwin"
        menubar.add_cascade(label="Edit", menu=create_edit_menu())
        menubar.add_cascade(label="Help", menu=create_help_menu())
        self.master.config(menu=menubar)

    def _set_up_icons(self):
        def set_up_icon(png):
            img = Image.open(png)
            return ImageTk.PhotoImage(img)

        self.doc_icon = set_up_icon('./icon/document.png')
        self.folder_icon = set_up_icon('./icon/folder.png')

    def _create_widgets(self):
        frame = ttk.Frame(padding="10")
        frame.grid(sticky=tk.NSEW)
        frame.grid_columnconfigure(1, weight=1)

        # Search pattern text box
        row = 0
        ttk.Label(frame, text="Look for").grid(row=row, column=0, sticky=tk.E)
        search_pattern_entry = ttk.Entry(frame,
                                         textvariable=self.search_pattern)
        search_pattern_entry.grid(row=row, column=1, sticky=tk.EW)

        # Start button
        self.start_button = ttk.Button(frame, text="Start",
                                       command=self._do_search)
        self.start_button.grid(row=row, column=2, sticky=tk.W)

        # Search folder text box
        row += 1
        ttk.Label(frame, text="Look in").grid(row=row, column=0, sticky=tk.E)
        ttk.Entry(frame, textvariable=self.search_folder).grid(row=row,
                                                               column=1,
                                                               sticky=tk.EW)

        # Select search folder button
        ttk.Button(frame, text="...",
                   command=self._get_search_folder).grid(row=row,
                                                         column=2,
                                                         sticky=tk.W)

        # Search subdirectories check box
        row += 1
        ttk.Label(frame, text="Search subdirectories?").grid(row=row,
                                                             column=0,
                                                             sticky=tk.E)
        ttk.Checkbutton(frame, onvalue=True,
                        offvalue=False,
                        variable=self.recurse).grid(row=row, column=1,
                                                    sticky=tk.W)

        # Results tree
        row += 1
        frame.grid_rowconfigure(row, weight=1)
        self._set_up_tree(frame, row, 0, 3)

        # Status bar
        row += 1
        tk.Label(textvariable=self.status_text).grid(row=row, column=0,
                                                     columnspan=3, sticky=tk.W)

        search_pattern_entry.focus_set()

    def _set_up_tree(self, frame, row, column, column_span):
        def set_up_context_menu(master):
            master.context_menu = tk.Menu(master, tearoff=0)
            master.context_menu.add_command(label="Copy Path",
                                            command=self._copy_path)

        headings = ['Name', 'Location']

        container = ttk.Frame(frame)
        container.grid(row=row, column=column, columnspan=column_span,
                       sticky=tk.NSEW)

        self.tree = ttk.Treeview(columns=headings, padding=0)
        set_up_context_menu(self.tree)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        if platform.system() == "Darwin":
            self.tree.bind("<Button-2>", self._on_tree_context_menu)
        else:
            self.tree.bind("<Button-3>", self._on_tree_context_menu)

        for col in headings:
            self.tree.heading(col, text=col.title(),
                              command=lambda c=col: sort_tree(
                                  self.tree, c, 0))
        self.tree.column(headings[0], stretch=False)
        self.tree.column("#0", stretch=False,
                         width=tkfont.Font().measure("X" * 4))

        vsb = ttk.Scrollbar(orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(column=0, row=0, sticky='nsew', in_=container)

        vsb.grid(column=1, row=0, sticky='ns', in_=container)

        label = ttk.Label(textvariable=self.count_text)
        label.grid(column=0, row=1, sticky='ew', in_=container)

        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

    def _get_search_folder(self):
        initial_dir = self.search_folder.get() or getcwd()
        search_folder = filedialog.askdirectory(
            initialdir=initial_dir, parent=self.master,
            mustexist=True)
        if search_folder:
            self.search_folder.set(search_folder)

    def _get_match_count(self):
        matches = len(self.tree.get_children())
        suffix = "" if matches == 1 else "es"
        return f'{matches:,} match{suffix}'

    def _process_progress_queue(self):
        if not self.progress_queue.empty():
            status = self.progress_queue.get()
            self._set_status(status)

            self.master.after(100, self._process_progress_queue)

    def _process_results_queue(self):
        if not self.results_queue.empty():
            files = self.results_queue.get()
            # print(f"files: {len(files)}")
            for file in files:
                image = self.folder_icon if isdir(file) \
                    else self.doc_icon
                values = (basename(file), dirname(file))
                self.tree.insert('', 'end', values=values, open=False,
                                 image=image)
            self.count_text.set(self._get_match_count())

            self.master.after(100, self._process_results_queue)
        else:
            self.start_button.configure(text="Start")
            self._set_status("Stopped" if self.search_stopped else "Done")

    # noinspection PyUnusedLocal
    def _do_search(self, event=None):
        def is_searching():
            return not self.progress_queue.empty() \
                   and not self.results_queue.empty()

        if is_searching():
            self.search_stopped = True
            self._stop_search()
        else:
            self.search_stopped = False
            self._start_search()

    def _stop_search(self):
        if self.search_task and self.search_task.is_alive():
            self.search_task.stop()
            self.search_task.join(1000)
        with self.results_queue.mutex:
            self.results_queue.queue.clear()
        with self.progress_queue.mutex:
            self.progress_queue.queue.clear()

    def _start_search(self):
        self.start_button.configure(text="Stop")
        self.tree.delete(*self.tree.get_children())
        search_pattern = self.search_pattern.get() or "*"
        search_folder = expanduser(self.search_folder.get()) or getcwd()
        self.search_task = searchtask.SearchTask(self.progress_queue,
                                                 self.results_queue,
                                                 search_pattern,
                                                 search_folder,
                                                 self.recurse.get())
        self.search_task.start()
        self.master.after(100, self._process_progress_queue)
        self.master.after(100, self._process_results_queue)

    def _set_status(self, status_text):
        text_length = tkfont.Font().measure(status_text)
        max_width = self.master.winfo_width() - tkfont.Font().measure("XX")
        if text_length > max_width:
            while tkfont.Font().measure("..." + status_text) > max_width:
                status_text = status_text[1:]
            status_text = "..." + status_text
        self.status_text.set(status_text)

    def _get_selected_file(self):
        sel = self.tree.selection()
        if len(sel) == 1:
            file_set = self.tree.set(sel)
            return join(file_set[self.tree.heading(1)["text"]],
                        file_set[self.tree.heading(0)["text"]])

    # noinspection PyUnusedLocal
    def _on_tree_select(self, event=None):
        file = self._get_selected_file()
        if file is None:
            self._set_status("")
            return
        s = stat(file)
        status = (
            f"{stat_u.filemode(s.st_mode)} "
            f"{s.st_nlink:>4} "
            f"{getpwuid(s.st_uid).pw_name:>9} "
            f"{grp.getgrgid(s.st_gid).gr_name:>9} "
            f"{byte_format.format_bytes(s.st_size, binary=True)} "
            f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(s.st_mtime))} "
            f"{basename(file) + ('/' if stat_u.S_ISDIR(s.st_mode) else '')}"
        )
        self._set_status(status)

    def _on_tree_context_menu(self, event):
        # No context menu if more than one item is selected
        if len(self.tree.selection()) == 1:
            try:
                self.tree.context_menu.tk_popup(event.x_root, event.y_root, 0)
            finally:
                self.tree.context_menu.grab_release()

    def _copy_path(self):
        file = self._get_selected_file()
        if file is not None:
            self.master.clipboard_clear()
            self.master.clipboard_append(file)


def sort_tree(tree, col, descending):
    """sort tree contents when a column header is clicked on"""
    # grab values to sort
    data = [(tree.set(child, col), child) for child in tree.get_children('')]
    # if the data to be sorted is numeric change to float
    # data =  change_numeric(data)
    # now sort the data in place
    data.sort(reverse=descending)
    for ix, item in enumerate(data):
        tree.move(item[1], '', ix)
    # switch the heading so it will sort in the opposite direction
    tree.heading(col, command=lambda c=col: sort_tree(tree, col,
                                                      int(not descending)))


def show_about():
    messagebox.showinfo("About",
                        f"{ProgramInfo.name}\r"
                        f"Version {ProgramInfo.version}\r\r"
                        f"{ProgramInfo.copyright}")


root = tk.Tk()
app = Application(master=root)
app.master.title(ProgramInfo.name)
app.mainloop()
