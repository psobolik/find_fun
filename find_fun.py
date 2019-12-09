import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font as tkFont
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

        self.recurse = tk.BooleanVar()
        self.search_pattern = tk.StringVar()
        self.search_folder = tk.StringVar()
        self.status_text = tk.StringVar()

        parent = tk.Frame(self.master, padx=10, pady=10)
        parent.grid()

        self._create_widgets(parent)
        self._set_up_icons()

    def _set_up_icons(self):
        def set_up_icon(png):
            img = Image.open(png)
            return ImageTk.PhotoImage(img)

        self.doc_icon = set_up_icon('./icon/document.png')
        self.folder_icon = set_up_icon('./icon/folder.png')

    def _create_widgets(self, parent):
        # Look for text box
        row = 0
        tk.Label(parent, text="Look for").grid(row=row, column=0, sticky=tk.E)
        self.search_pattern_entry = tk.Entry(
            parent, textvariable=self.search_pattern)
        self.search_pattern_entry.grid(row=row, column=1, sticky=tk.EW)

        # Start button
        self.start_button = tk.Button(parent, text="Start",
                                      padx="10",
                                      command=self._do_search)
        self.start_button.grid(row=row, column=2, sticky=tk.W)

        # Look in text box
        row += 1
        tk.Label(parent, text="Look in").grid(row=row, column=0, sticky=tk.E)
        self.search_folder_entry = tk.Entry(
            parent, textvariable=self.search_folder)
        self.search_folder_entry.grid(row=row, column=1, sticky=tk.EW)

        # Select folder button
        self.search_folder_button = tk.Button(parent, text="...",
                                              command=self._get_search_folder)
        self.search_folder_button.grid(row=row, column=2, sticky=tk.W)

        # Search subdirectories check box
        row += 1
        tk.Label(parent, text="Search subdirectories?").grid(row=row, column=0,
                                                             sticky=tk.E)
        self.recurse_check = tk.Checkbutton(parent, onvalue=True,
                                            offvalue=False,
                                            variable=self.recurse)
        self.recurse_check.grid(row=row, column=1, sticky=tk.W)

        # Results tree
        row += 1
        self.master.grid_rowconfigure(row, weight=1)
        self._set_up_tree(parent, row, 0, 3)

        # Status bar
        row += 1
        self.statusbar = tk.Label(textvariable=self.status_text)
        self.statusbar.grid(row=row, column=0, columnspan=3, sticky=tk.W)

        self.search_pattern_entry.focus_set()

    def _set_up_tree(self, parent, row, column, columnspan):
        headings = ['Name', 'Location']

        container = ttk.Frame(parent)
        container.grid(row=row, column=column, columnspan=columnspan,
                       sticky="nsew")

        self.tree = ttk.Treeview(columns=headings, padding=0)
        for col in headings:
            self.tree.heading(col, text=col.title(),
                              command=lambda c=col: sort_tree(
                                  self.tree, c, 0))
        self.tree.column(headings[0], stretch=False)
        self.tree.column("#0", stretch=False,
                         width=tkFont.Font().measure("X" * 4))

        vsb = ttk.Scrollbar(orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(column=0, row=0, sticky='nsew', in_=container)

        vsb.grid(column=1, row=0, sticky='ns', in_=container)

        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

    def _get_search_folder(self):
        initialdir = self.search_folder or getcwd()
        search_folder = filedialog.askdirectory(
            initialdir=initialdir, parent=self.master,
            mustexist=True)
        if search_folder:
            self.search_folder.set(search_folder)

    def _process_progress_queue(self):
        if not self.progressqueue.empty():
            status = self.progressqueue.get()
            self._set_status(status)

            self.master.after(100, self._process_progress_queue)

    def _process_results_queue(self):
        if not self.resultsqueue.empty():
            files = self.resultsqueue.get()
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
            self._set_status(f"{matches:,} match{suffix}")

    def _do_search(self, event=None):
        self.tree.delete(*self.tree.get_children())
        search_pattern = self.search_pattern.get() or "*"
        search_folder = expanduser(self.search_folder.get()) or getcwd()
        self.resultsqueue = queue.Queue()
        self.progressqueue = queue.Queue()
        self.searchtask = searchtask.SearchTask(self.progressqueue,
                                                self.resultsqueue,
                                                search_pattern,
                                                search_folder,
                                                self.recurse.get())
        self.searchtask.start()
        self.master.after(100, self._process_progress_queue)
        self.master.after(100, self._process_results_queue)

    def _set_status(self, statustext):
        textlen = tkFont.Font().measure(statustext)
        maxwidth = self.master.winfo_width() - tkFont.Font().measure("XX")
        if textlen > maxwidth:
            while tkFont.Font().measure("..." + statustext) > maxwidth:
                statustext = statustext[1:]
            statustext = "..." + statustext
        self.status_text.set(statustext)


def sort_tree(tree, col, descending):
    """sort tree contents when a column header is clicked on"""
    # grab values to sort
    data = [(tree.set(child, col), child)
            for child in tree.get_children('')]
    # if the data to be sorted is numeric change to float
    # data =  change_numeric(data)
    # now sort the data in place
    data.sort(reverse=descending)
    for ix, item in enumerate(data):
        tree.move(item[1], '', ix)
    # switch the heading so it will sort in the opposite direction
    tree.heading(col, command=lambda col=col: sort_tree(tree, col,
                                                        int(not descending)))


root = tk.Tk()
app = Application(master=root)
app.master.title("Find Fun")
app.mainloop()
