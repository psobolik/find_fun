import threading
from os.path import join, isdir
from os import listdir
import glob
import re

from Found import Found


class SearchTask(threading.Thread):
    def __init__(self,
                 progress_queue,
                 results_queue,
                 search_pattern,
                 search_folder,
                 grep_pattern,
                 match_case,
                 match_word,
                 recurse):
        threading.Thread.__init__(self)
        self.progress_queue = progress_queue
        self.results_queue = results_queue
        self.search_pattern = search_pattern
        self.search_folder = search_folder
        self.recurse = recurse
        self.stop_event = threading.Event()

        self.regex = None
        if grep_pattern:
            if match_word:
                grep_pattern = f"\\W{grep_pattern}\\W"
            self.regex = re.compile(grep_pattern, 0 if match_case else re.I)

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
