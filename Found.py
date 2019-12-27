class Found:
    def __init__(self, path, is_folder=False, lines=None):
        self.path = path
        self.is_folder = is_folder
        self.lines = lines if lines else []
