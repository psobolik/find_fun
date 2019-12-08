import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font as tkFont
from PIL import Image, ImageTk
from tkinter import filedialog
from os.path import join, expanduser, basename, dirname, isdir
import glob

# /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/tkinter


class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        master.config(padx=10, pady=10)
        self.master = master
        self.master.grid_columnconfigure(1, weight=1)
        self.master.bind("<Return>", self._start_search)
        self._create_widgets(master)
        self._set_up_icons()

    def _set_up_icons(self):
        def set_up_icon(png):
            img = Image.open(png)
            return ImageTk.PhotoImage(img)

        self.doc_icon = set_up_icon('./icon/document.png')
        self.folder_icon = set_up_icon('./icon/folder.png')

    def _create_widgets(self, master):
        # Look for
        row = 0
        tk.Label(text="Look for").grid(row=row, column=0, sticky=tk.E)
        self.look_for_entry = tk.Entry()
        self.look_for_entry.grid(row=row, column=1, sticky=tk.EW)

        # Look in
        row += 1
        tk.Label(text="Look in").grid(row=row, column=0, sticky=tk.E)
        self.look_in_entry = tk.Entry()
        self.look_in_entry.grid(row=row, column=1, sticky=tk.EW)
        self.look_in_btn = tk.Button(text="...",
                                     command=self._get_look_in_folder)
        self.look_in_btn.grid(row=row, column=2)

        # Search subdirectories?
        row += 1
        tk.Label(text="Search subdirectories?").grid(row=row, column=0,
                                                     sticky=tk.E)
        self.search_subdirectories_check = tk.Checkbutton()
        self.search_subdirectories_check.grid(row=row, column=1, sticky=tk.W)

        # Results
        row += 1
        self.master.grid_rowconfigure(row, weight=1)
        self._set_up_tree(row, 0, 3)
        # self.result_list = tk.Listbox(master, relief="groove")
        # self.result_list.grid(row=row, column=0, columnspan=3,
        #                        sticky="news", pady=10)

        # Start button
        row += 1
        self.start = tk.Button(master, text="Start",
                               padx="10",
                               command=self._start_search)
        self.start.grid(row=row, column=0, columnspan=3)

        self.look_for_entry.focus_set()

    def _set_up_tree(self, row, column, columnspan):
        headings = ['Name', 'Location']

        container = ttk.Frame()
        container.grid(row=row, column=column, columnspan=columnspan,
                       sticky="nsew")

        self.tree = ttk.Treeview(columns=headings, padding=0)
        for col in headings:
            self.tree.heading(col, text=col.title(),
                              command=lambda c=col: sort_tree(self.tree, c, 0))
        self.tree.column("#0", width=tkFont.Font().measure("XXXX"))

        vsb = ttk.Scrollbar(orient="vertical",
                            command=self.tree.yview)
        hsb = ttk.Scrollbar(orient="horizontal",
                            command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set,
                            xscrollcommand=hsb.set)
        self.tree.grid(column=0, row=0, sticky='nsew', in_=container)

        vsb.grid(column=1, row=0, sticky='ns', in_=container)
        hsb.grid(column=0, row=1, sticky='ew', in_=container)

        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

    def _set_tree_items(self, item_list):
        self.tree.delete(*self.tree.get_children())
        for item in item_list:
            image = self.folder_icon if isdir(item) else self.doc_icon
            values = (basename(item), dirname(item))
            self.tree.insert('', 'end', values=values, open=False,
                             image=image)

    def _get_look_in_folder(self):
        self.look_in_entry.delete(0, tk.END)
        self.look_in_entry.insert(0, filedialog.askdirectory(
            mustexist="false"))

    def _start_search(self, event=None):
        look_for = self.look_for_entry.get() or "*"
        look_in = expanduser(self.look_in_entry.get())

        files = glob.glob(join(look_in, look_for))
        files.sort()
        self._set_tree_items(files)
        # file_list = [(basename(f), dirname(f)) for f in files]

        # self._set_tree_items(file_list)
        # files = [f for f in listdir(look_in) if isfile(join(look_in, f))]
        # for file in files:
        #     self.result_list.insert(self.result_list.size(), file)


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
