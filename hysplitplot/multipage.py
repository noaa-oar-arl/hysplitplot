# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# multipage.py
#
# For writing one or more plots to a file. If a file format does not support
# multiple pages (for example, the PNG image format), each plot is saved
# to a different file using a numeric sequence.
# ---------------------------------------------------------------------------

from abc import ABC, abstractmethod
import logging
import os
from matplotlib.backends.backend_pdf import PdfPages

from hysplitplot import const, util


logger = logging.getLogger(__name__)


class PlotFileWriterFactory:

    @staticmethod
    def create_instance(frames_per_file, output_basename, output_suffix,
                        output_format):
        if frames_per_file == const.Frames.ALL_FILES_ON_ONE:
            if output_format.lower() == "pdf":
                return MultiplePlotPDFWriter(output_basename, output_suffix)
            elif output_format.lower() == "ps":
                return MultiplePlotPostscriptWriter(output_basename,
                                                    output_suffix)
            else:
                logger.warning("%s format supports one plot per file: will "
                               "insert a frame number to file name",
                               output_suffix)

        return SinglePlotFileWriter(output_basename, output_suffix,
                                    output_format)


class AbstractMultiplePlotFileWriter(ABC):

    def __init__(self):
        self.file_count = 0

    @abstractmethod
    def save(self, figure, frame_number):
        pass

    @abstractmethod
    def close(self):
        pass


class SinglePlotFileWriter(AbstractMultiplePlotFileWriter):

    def __init__(self, output_basename, output_suffix, output_format):
        super(SinglePlotFileWriter, self).__init__()
        self.output_basename = output_basename
        self.output_suffix = output_suffix
        self.output_format = output_format

    def save(self, figure, frame_no):
        filename = self._make_filename(frame_no)
        logger.info("Saving plot %d to file %s", frame_no, filename)
        figure.savefig(filename, papertype="letter", format=self.output_format)
        self.file_count += 1

    def _make_filename(self, frame_no):
        return "{0}{1:04d}.{2}".format(self.output_basename, frame_no,
                                       self.output_suffix)

    def close(self):
        pass


class MultiplePlotPDFWriter(AbstractMultiplePlotFileWriter):

    def __init__(self, output_basename, output_suffix):
        super(MultiplePlotPDFWriter, self).__init__()
        self.filename = "{}.{}".format(output_basename, output_suffix)
        logger.debug("Opening file %s", self.filename)
        self.pdf = PdfPages(self.filename)

    def save(self, figure, frame_no):
        logger.info("Saving plot %d to file %s", frame_no, self.filename)
        self.pdf.savefig(figure)
        if self.file_count == 0:
            self.file_count += 1

    def close(self):
        self.pdf.close()


class MultiplePlotPostscriptWriter(AbstractMultiplePlotFileWriter):

    def __init__(self, output_basename, output_suffix):
        super(MultiplePlotPostscriptWriter, self).__init__()
        self.filename = "{}.{}".format(output_basename, output_suffix)
        logger.debug("Opening file %s", self.filename)
        self.page_count = 0

    def save(self, figure, frame_no):
        logger.info("Saving plot %d to file %s", frame_no, self.filename)
        if self.page_count == 0:
            figure.savefig(self.filename, papertype="letter", format="ps")
        else:
            tempfile = "{}.{}".format(self.filename, self.page_count)
            figure.savefig(tempfile, papertype="letter", format="ps")
            util.join_file(tempfile, self.filename)
            os.remove(tempfile)
        self.page_count += 1

        if self.file_count == 0:
            self.file_count += 1

    def close(self):
        pass
