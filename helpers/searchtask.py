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
        self.stopevent = threading.Event()
        self.was_stopped = False

    def run(self):
        def search(searchpattern, searchfolder, recurse):
            if self.stopped():
                return

            # print(f"searchfolder: {searchfolder}")
            self.progressqueue.put(searchfolder)
            files = glob.glob(join(searchfolder, searchpattern))
            files.sort()
            self.resultsqueue.put(files)
            if recurse:
                try:
                    for subfolder in [join(searchfolder, f) for f
                                      in listdir(searchfolder)
                                      if isdir(join(searchfolder, f))]:
                        if self.stopped():
                            break
                        search(searchpattern, subfolder, recurse)
                except PermissionError:
                    pass

        search(self.searchpattern, self.searchfolder, self.recurse)

    def stop(self):
        self.stopevent.set()

    def stopped(self):
        return self.stopevent.is_set()
