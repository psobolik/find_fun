import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font as tkfont
from PIL import Image, ImageTk
from tkinter import filedialog
from os import getcwd
from os.path import expanduser, basename, dirname, isdir
import queue
from helpers import searchtask


class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.master.bind("<Return>", self._do_search)
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_rowconfigure(0, weight=1)

        self.recurse = tk.BooleanVar()
        self.search_pattern = tk.StringVar()
        self.search_folder = tk.StringVar()
        self.status_text = tk.StringVar()
        self.status_text.set("Copyright © 2019 Paul Sobolik")
        self._create_widgets()
        self._set_up_icons()

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
        self.statusbar = tk.Label(textvariable=self.status_text)
        self.statusbar.grid(row=row, column=0, columnspan=3, sticky=tk.W)

        search_pattern_entry.focus_set()

    def _set_up_tree(self, frame, row, column, column_span):
        headings = ['Name', 'Location']

        container = ttk.Frame(frame)
        container.grid(row=row, column=column, columnspan=column_span,
                       sticky=tk.NSEW)

        self.tree = ttk.Treeview(columns=headings, padding=0)
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

        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

    def _get_search_folder(self):
        initial_dir = self.search_folder or getcwd()
        search_folder = filedialog.askdirectory(
            initialdir=initial_dir, parent=self.master,
            mustexist=True)
        if search_folder:
            self.search_folder.set(search_folder)

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

            self.master.after(100, self._process_results_queue)
        else:
            matches = len(self.tree.get_children())
            suffix = "" if matches == 1 else "es"
            self._set_status(f'{matches:,} match{suffix}')

    def _do_search(self):
        self.tree.delete(*self.tree.get_children())
        search_pattern = self.search_pattern.get() or "*"
        search_folder = expanduser(self.search_folder.get()) or getcwd()
        self.results_queue = queue.Queue()
        self.progress_queue = queue.Queue()
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


root = tk.Tk()
app = Application(master=root)
app.master.title("Find Fun")
app.mainloop()
