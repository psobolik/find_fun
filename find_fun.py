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
from os.path import expanduser, basename, dirname, join
import queue
import re

from Found import Found
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
        self.master.grid_rowconfigure(1, weight=1)

        self.master.bind("<Return>", self._do_search)

        self._init_variables()
        self._create_widgets()
        self._create_menu()
        self._set_up_icons()

    def _init_variables(self):
        self.search_stopped = False
        self.search_task = None
        self.results_queue = queue.Queue()
        self.progress_queue = queue.Queue()

        self.recurse = tk.BooleanVar()
        self.search_pattern = tk.StringVar(value="*")
        self.grep_pattern = tk.StringVar()
        self.match_case = tk.BooleanVar()
        self.match_word = tk.BooleanVar()
        self.search_folder = tk.StringVar(value=getcwd())
        self.status_text = tk.StringVar(value=ProgramInfo.copyright)
        self.file_folder_match_count_text = tk.StringVar()
        self.line_match_count_text = tk.StringVar()
        self.start_button_text = tk.StringVar(value="Start")

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
        self._create_criteria_widgets(0)
        self._create_results_widgets(1)
        self._create_status_bar(2)

    def _create_status_bar(self, row):
        ttk.Separator(orient=tk.HORIZONTAL).grid(row=row, column=0)
        ttk.Label(textvariable=self.status_text, padding=4,
                  relief=tk.FLAT).grid(row=row+1, column=0,
                                       sticky=tk.EW)

    def _create_results_widgets(self, parent_row):
        results_frame = ttk.Frame(padding=10)
        results_frame.grid(row=parent_row, column=0, sticky=tk.NSEW)
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_columnconfigure(1, weight=1)
        results_frame.grid_rowconfigure(0, weight=1)

        self._set_up_tree(results_frame, row=0, column=0)
        self._set_up_hits_tree(results_frame, row=0, column=1)

    def _create_criteria_widgets(self, parent_row):
        frame = ttk.Frame(padding=10)
        frame.grid(row=parent_row, sticky=tk.NSEW)
        frame.grid_columnconfigure(1, weight=1)

        # File search pattern text box
        row = 0
        ttk.Label(frame, text="Match files/folders:").grid(row=row, column=0,
                                                           sticky=tk.E)
        search_pattern_entry = ttk.Entry(frame,
                                         textvariable=self.search_pattern)
        search_pattern_entry.grid(row=row, column=1, sticky=tk.EW)

        # Start button
        ttk.Button(frame, textvariable=self.start_button_text, takefocus=0,
                   command=self._do_search).grid(row=row,
                                                 column=2,
                                                 sticky=tk.W)

        # Grep pattern text box
        row += 1
        ttk.Label(frame, text="Look for pattern:").grid(row=row, column=0,
                                                        sticky=tk.E)
        ttk.Entry(frame, textvariable=self.grep_pattern).grid(row=row,
                                                              column=1,
                                                              sticky=tk.EW)
        row += 1
        ck_frame = ttk.Frame(frame)
        ck_frame.grid(row=row, column=1, sticky=tk.W)
        ttk.Checkbutton(ck_frame, text="Match case?",
                        variable=self.match_case).grid(row=0, column=0)
        ttk.Checkbutton(ck_frame, text="Match whole words?",
                        variable=self.match_word).grid(row=0, column=1)

        # Search folder text box
        row += 1
        ttk.Label(frame, text="Look in folder:").grid(row=row, column=0,
                                                      sticky=tk.E)
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
        ttk.Checkbutton(frame, text="Search subdirectories?",
                        onvalue=True, offvalue=False,
                        variable=self.recurse).grid(row=row, column=1,
                                                    sticky=tk.W)

        search_pattern_entry.focus_set()

    def _set_up_tree(self, frame, row, column):
        headings = ['Name', 'Location']

        container = ttk.Frame(frame)
        container.grid(row=row, column=column, sticky=tk.NSEW)

        self.tree = ttk.Treeview(columns=headings, padding=0)
        self.tree.context_menu = tk.Menu(self.tree, tearoff=0)
        self.tree.context_menu.add_command(label="Copy Path",
                                           command=self._copy_path)
        # set_up_context_menu(self.tree)

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
        self.tree.grid(column=0, row=0, sticky=tk.NSEW, in_=container)

        vsb.grid(column=1, row=0, sticky=tk.NS, in_=container)

        ttk.Label(textvariable=self.file_folder_match_count_text) \
            .grid(column=0, row=1, sticky=tk.EW, in_=container)

        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

    def _set_up_hits_tree(self, frame, row, column):
        self.hits_tree_columns = ['line_no', 'line']

        container = ttk.Frame(frame)
        container.grid(row=row, column=column, sticky=tk.NSEW)

        self.hits_tree = ttk.Treeview(columns=self.hits_tree_columns,
                                      padding=0)
        for column in self.hits_tree_columns:
            self.hits_tree.heading(column)

        self.hits_tree.column(self.hits_tree_columns[0], width=10)
        self.hits_tree.column(self.hits_tree_columns[1], width=400)
        self.hits_tree.column("#0", stretch=False, width=0)

        vsb = ttk.Scrollbar(orient="vertical",
                            command=self.hits_tree.yview)
        hsb = ttk.Scrollbar(orient="horizontal",
                            command=self.hits_tree.xview)
        self.hits_tree.configure(yscrollcommand=vsb.set,
                                 xscrollcommand=hsb.set)
        self.hits_tree.grid(column=0, row=0, sticky=tk.NSEW, in_=container)

        vsb.grid(column=1, row=0, sticky=tk.NS, in_=container)
        hsb.grid(column=0, row=1, sticky=tk.EW, in_=container)

        ttk.Label(textvariable=self.line_match_count_text) \
            .grid(column=0, row=2, sticky=tk.EW, in_=container)

        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

    def _get_search_folder(self):
        initial_dir = self.search_folder.get() or getcwd()
        search_folder = filedialog.askdirectory(
            initialdir=initial_dir, parent=self.master,
            mustexist=True)
        if search_folder:
            self.search_folder.set(search_folder)

    def _get_hit_count(self):
        matches = len(self.hits_tree.get_children())
        suffix = "" if matches == 1 else "s"
        return f"{matches:,} line{suffix}"

    def _get_match_count(self):
        matches = len(self.tree.get_children())
        suffix = "" if matches == 1 else "s"
        return f'{matches:,} file{suffix}/folder{suffix}'

    def _process_progress_queue(self):
        if not self.progress_queue.empty():
            status = self.progress_queue.get()
            self._set_status(status)

            self.master.after(100, self._process_progress_queue)

    def _process_results_queue(self):
        if not self.results_queue.empty():
            results = self.results_queue.get()
            for found_item in results:
                image = self.folder_icon if found_item.is_folder \
                    else self.doc_icon
                values = (basename(found_item.path), dirname(found_item.path))
                self.tree.insert('', 'end', values=values, open=False,
                                 image=image,
                                 tags=found_item.lines)
            self.file_folder_match_count_text.set(self._get_match_count())

            self.master.after(100, self._process_results_queue)
        else:
            # self.start_button.configure(text="Start")
            self.start_button_text.set("Start")
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

    def _clear_tree(self):
        self.tree.delete(*self.tree.get_children())

    def _clear_hits(self):
        self.hits_tree.delete(*self.hits_tree.get_children())
        self.hits_tree.column(self.hits_tree_columns[0], width=10)
        self.hits_tree.column(self.hits_tree_columns[1], width=400)
        self._set_status("")
        self.line_match_count_text.set("")

    def _start_search(self):
        self.start_button_text.set("Stop")
        # self.start_button.configure(text="Stop")
        self._clear_tree()
        self._clear_hits()

        search_pattern = self.search_pattern.get() or "*"
        search_folder = expanduser(self.search_folder.get()) or getcwd()
        self.search_task = searchtask.SearchTask(self.progress_queue,
                                                 self.results_queue,
                                                 search_pattern,
                                                 search_folder,
                                                 self.grep_pattern.get(),
                                                 self.match_case.get(),
                                                 self.match_word.get(),
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

    def _get_selected_item(self):
        sel = self.tree.selection()
        if len(sel) == 1:
            item = self.tree.item(sel)
            return Found(join(item['values'][1], item['values'][0]),
                         lines=item['tags'])

    # noinspection PyUnusedLocal
    def _on_tree_select(self, event=None):
        self._clear_hits()

        item = self._get_selected_item()
        if item is None:
            return
        regex = re.compile(r"^(\d*) {(.*)\n}")
        for line in item.lines:
            self.hits_tree.insert('', 'end', values=line, open=False)

            # adjust column width if necessary to fit each value
            match = regex.match(line)
            if match:
                match_count = len(match.groups())
                if match_count > 0:
                    width = tkfont.Font().measure(f"{match[1]}X")
                    col = self.hits_tree_columns[0]
                    if self.hits_tree.column(col, width=None) < width:
                        self.hits_tree.column(col, width=width)

                if match_count > 1:
                    width = tkfont.Font().measure(f"{match[2]}X")
                    col = self.hits_tree_columns[1]
                    if self.hits_tree.column(col, width=None) < width:
                        self.hits_tree.column(col, width=width)
        self.line_match_count_text.set(self._get_hit_count())

        s = stat(item.path)
        name = basename(item.path) + ('/' if stat_u.S_ISDIR(s.st_mode) else '')
        status = (
            f"{stat_u.filemode(s.st_mode)} "
            f"{s.st_nlink:>4} "
            f"{getpwuid(s.st_uid).pw_name:>9} "
            f"{grp.getgrgid(s.st_gid).gr_name:>9} "
            f"{byte_format.format_bytes(s.st_size, binary=True)} "
            f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(s.st_mtime))} "
            f"{name}"
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
        item = self._get_selected_item()
        if item is not None:
            self.master.clipboard_clear()
            self.master.clipboard_append(item.path)


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
