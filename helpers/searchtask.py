import threading
from os.path import join, isdir
from os import listdir
import glob
import re

from Found import Found


class SearchTask(threading.Thread):
    def __init__(self,
                 _progress_queue,
                 _results_queue,
                 _search_pattern,
                 _search_folder,
                 _grep_pattern,
                 _match_case,
                 _recurse):
        threading.Thread.__init__(self)
        self.progress_queue = _progress_queue
        self.results_queue = _results_queue
        self.search_pattern = _search_pattern
        self.search_folder = _search_folder
        self.recurse = _recurse
        self.stop_event = threading.Event()

        self.regex = re.compile(_grep_pattern, 0 if _match_case else re.I) \
            if _grep_pattern else None

        self.was_stopped = False

    def _do_grep(self, paths):
        if self.regex:
            found = []
            for path in paths:
                # ignore directories
                if not isdir(path):
                    found_item = Found(path)
                    with open(path) as fd:
                        try:
                            line_no = 1
                            for line in fd:
                                if self.regex.search(line):
                                    found_item.lines.append((line_no, line))
                                line_no += 1
                        except UnicodeDecodeError:
                            pass
                    if found_item.lines:
                        found.append(found_item)
            return found

    def _do_search(self, search_folder):
        if self.stopped():
            return

        self.progress_queue.put(search_folder)
        paths = glob.glob(join(search_folder, self.search_pattern))
        paths.sort()
        result = self._do_grep(paths) \
            if self.regex \
            else [Found(path, isdir(path)) for path in paths]
        self.results_queue.put(result)
        if self.recurse:
            try:
                for sub_folder in [join(search_folder, f) for f
                                   in listdir(search_folder)
                                   if isdir(join(search_folder, f))]:
                    if self.stopped():
                        break
                    self._do_search(sub_folder)
            except PermissionError:
                pass

    def run(self):
        self._do_search(self.search_folder)

    def stop(self):
        self.stop_event.set()

    def stopped(self):
        return self.stop_event.is_set()
