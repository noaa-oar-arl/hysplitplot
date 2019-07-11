from abc import ABC, abstractmethod
import logging
from matplotlib.backends.backend_pdf import PdfPages

from hysplitplot import const


logger = logging.getLogger(__name__)


class PlotFileWriterFactory:
    
    @staticmethod
    def create_instance(frames_per_file, output_basename, output_suffix):
        if frames_per_file == const.Frames.ALL_FILES_ON_ONE:
            if output_suffix.lower() == "pdf":
                return MultiplePlotPDFWriter(output_basename, output_suffix)
            else:
                logger.warning("Saving all plots in the [{}] format is not supported. Instead, one file per plot will be generated".format(output_suffix))

        return SinglePlotFileWriter(output_basename, output_suffix)
    

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
    
    def __init__(self, output_basename, output_suffix):
        super(SinglePlotFileWriter, self).__init__()
        self.output_basename = output_basename
        self.output_suffix = output_suffix
    
    def save(self, figure, frame_no):
        filename = self._make_filename(frame_no)
        logger.debug("Saving a plot to file %s", filename)
        figure.savefig(filename, papertype="letter")
        self.file_count += 1
    
    def _make_filename(self, frame_no):
        return "{0}{1:04d}.{2}".format(self.output_basename, frame_no, self.output_suffix)

    def close(self):
        pass
    

class MultiplePlotPDFWriter(AbstractMultiplePlotFileWriter):
    
    def __init__(self, output_basename, output_suffix):
        super(MultiplePlotPDFWriter, self).__init__()
        self.filename = "{}.{}".format(output_basename, output_suffix)
        logger.debug("Saving a plot to file %s", self.filename)
        self.pdf = PdfPages(self.filename)
    
    def save(self, figure, frame_no):
        self.pdf.savefig(figure)
        if self.file_count == 0:
            self.file_count += 1
        
    def close(self):
        self.pdf.close()
