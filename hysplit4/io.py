import logging
import os


logger = logging.getLogger(__name__)


class FormattedLineReader:
    """Parses a text line with a FORTRAN-like format

    """

    def parse_format(self, format):
        flist = []

        repeat = 1; type = None; width = None; precision = None

        state = 0; start = 0; last = -1;
        for k in range(len(format)):
            c = format[k:k+1]
            if state == 0:
                # looking for type
                if c.isdigit():
                    last = k + 1
                elif c.isalpha():
                    repeat = int(format[start:last]) if last > start else 1
                    type = c; start = k + 1; last = -1;
                    if c == 'X':
                        flist.append([repeat, type])
                    elif c == 'F':
                        state = 2
                    else:
                        state = 1
                elif c == ' ':
                    start = k + 1
            elif state == 1:
                # looking for integer width
                if c.isdigit():
                    last = k + 1
                elif c == ',' or c == ' ':
                    width = int(format[start:last])
                    flist.append([repeat, type, width])
                    type = None; start = k + 1; last = -1;
                    state = 0
            elif state == 2:
                # looking for float width
                if c.isdigit():
                    last = k + 1
                elif c == '.':
                    width = int(format[start:last])
                    start = k + 1; last = -1;
                    state = 3
            elif state == 3:
                # looking for float precision
                if c.isdigit():
                    last = k + 1
                elif c == ',' or c == ' ':
                    precision = int(format[start:last])
                    flist.append([repeat, type, width, precision])
                    type = None; start = k + 1; last = -1;
                    state = 0

        if state == 1:
            width = int(format[start:last])
            flist.append([repeat, type, width])
        elif state == 2:
            width = int(format[start:last])
            precision = 0
            flist.append([repeat, type, width, precision])
        elif state == 3:
            precision = int(format[start:last])
            flist.append([repeat, type, width, precision])

        return flist

    def parse(self, format, line):
        data = []
        line_len = len(line)

        flist = self.parse_format(format)

        start = last = 0;
        for fmt in flist:
            for k in range(fmt[0]): # repetition, e.g., 3 in 3I6
                c = fmt[1]
                if c == 'X':
                    start += 1
                elif c == 'A':
                    last = start + fmt[2]
                    if start < line_len:
                        str = line[start:last]
                        data.append(str)
                    start = last
                elif c == 'I':
                    last = start + fmt[2]
                    if start < line_len:
                        str = line[start:last]
                        data.append(int(str))
                    start = last
                elif c == 'F':
                    last = start + fmt[2]
                    if start < line_len:
                        str = line[start:last]
                        data.append(float(str))
                    start = last
                else:
                    raise Exception("unknown format type [{0}]".format(c))

        return data


class FormattedTextFileReader:
    """File reader for text data in FORTRAN way

    """

    def __init__(self):
        self.lines = ()
        self.line_index = -1
        self.buffer = None
        self.formatter = FormattedLineReader()

    def open(self, filename):
        logger.debug("reading text file %s", filename)

        if os.path.exists(filename):
            # store lines without the newline char.
            with open(filename, "r") as f:
                self.lines = f.read().splitlines()

            self.line_index = -1
            self.buffer = None
            f.close()
        else:
            raise Exception("FATAL ERROR - File not found: {0}".format(filename))

    def close(self):
        # do nothing as the file is already closed in open().
        return

    def fetch_line(self):
        if self.line_index < len(self.lines):
            self.line_index += 1
            self.buffer = self.lines[self.line_index]
        else:
            raise Exception("reached end of line")
        return self.buffer

    def has_next(self):
        return True if (self.line_index < len(self.lines) - 1) else False

    def parse_line(self, format):
        return self.formatter.parse(format, self.fetch_line())

    def look_ahead(self, format):
        if self.has_next():
            return self.formatter.parse(format, self.lines[self.line_index + 1])
        raise Exception("reached end of line")

    def get_current_line(self):
        return self.buffer
