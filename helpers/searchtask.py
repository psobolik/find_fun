import threading
from os.path import join, isdir
from os import listdir
import glob


class SearchTask(threading.Thread):
    def __init__(self,
                 _progressqueue,
                 _resultsqueue,
                 _searchpattern,
                 _searchfolder,
                 _recurse):
        threading.Thread.__init__(self)
        self.progressqueue = _progressqueue
        self.resultsqueue = _resultsqueue
        self.searchpattern = _searchpattern
        self.searchfolder = _searchfolder
        self.recurse = _recurse

    def run(self):
        def search(searchpattern, searchfolder, recurse):
            # print(f"searchfolder: {searchfolder}")
            self.progressqueue.put(searchfolder)
            files = glob.glob(join(searchfolder, searchpattern))
            self.resultsqueue.put(files)
            if recurse:
                try:
                    for subfolder in [join(searchfolder, f) for f
                                      in listdir(searchfolder)
                                      if isdir(join(searchfolder, f))]:
                        search(searchpattern, subfolder, recurse)
                except PermissionError:
                    pass
        search(self.searchpattern, self.searchfolder, self.recurse)
