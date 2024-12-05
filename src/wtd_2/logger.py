class Logger:

    def __init__(self):
        self._lines_printed  = 0
        pass

    def print(self, *args, **kwargs):
        self._lines_printed += 1
        print(*args, **kwargs)

    def get_lines_printed(self):
        newLinesCount = self._lines_printed
        self._lines_printed = 0
        return newLinesCount
