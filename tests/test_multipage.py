# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_multipage.py
#
# Performs unit tests on functions and class methods declared in multipage.py.
# ---------------------------------------------------------------------------

import matplotlib.pyplot as plt
import os
import pytest

from hysplitplot import multipage, const


class AbstractMultiplePlotFileWriterTest(multipage.AbstractMultiplePlotFileWriter):
    
    def save(self, figure, frame_number):
        pass
    
    def close(self):
        pass
    

def test_PlotFileWriterFactory_create_instance():
    o = multipage.PlotFileWriterFactory.create_instance(const.Frames.ALL_FILES_ON_ONE, "test", "pdf", "pdf")
    assert isinstance(o, multipage.MultiplePlotPDFWriter)
    if os.path.exists("test.pdf"):
        o.close()
        os.remove("test.pdf")
        
    o = multipage.PlotFileWriterFactory.create_instance(const.Frames.ALL_FILES_ON_ONE, "test", "PDF", "pdf")
    assert isinstance(o, multipage.MultiplePlotPDFWriter)
    if os.path.exists("test.PDF"):
        o.close()
        os.remove("test.PDF")
    
    o = multipage.PlotFileWriterFactory.create_instance(const.Frames.ALL_FILES_ON_ONE, "test", "ps", "ps")
    assert isinstance(o, multipage.MultiplePlotPostscriptWriter)
        
    # A PNG image file cannot have more than one page.
    o = multipage.PlotFileWriterFactory.create_instance(const.Frames.ALL_FILES_ON_ONE, "test", "PNG", "png")
    assert isinstance(o, multipage.SinglePlotFileWriter)


def test_AbstractMultiplePlotFileWriter___init__():
    o = AbstractMultiplePlotFileWriterTest()
    assert o.file_count == 0
    
    
def test_SinglePlotFileWriter___init__():
    o = multipage.SinglePlotFileWriter("test", "3141", "png")
    assert o.file_count == 0
    assert o.output_basename == "test"
    assert o.output_suffix == "3141"
    assert o.output_format == "png"
    

def test_SinglePlotFileWriter_save():
    ax = plt.axes()
    
    o = multipage.SinglePlotFileWriter("__multipagetest", "png", "png")
    o.save(ax.figure, 1)
    o.save(ax.figure, 2)
    
    assert os.path.exists( "__multipagetest0001.png" )
    assert os.path.exists( "__multipagetest0002.png" )
    assert o.file_count == 2
    
    os.remove( "__multipagetest0001.png" )
    os.remove( "__multipagetest0002.png" )
    plt.close(ax.figure)
    
    
def test_SinglePlotFileWriter__make_filename():
    o = multipage.SinglePlotFileWriter("output", "ps", "ps")
     
    assert o._make_filename(1) == "output0001.ps"
    assert o._make_filename(2) == "output0002.ps"


def test_SinglePlotFileWriter_close():
    o = multipage.SinglePlotFileWriter("output", "ps", "ps")
    
    try:
        o.close()
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))


def test_MultiplePlotPDFWriter___init__():
    if os.path.exists("__multipagetest.3141"):
        os.remove("__multipagetest.3141")
        
    o = multipage.MultiplePlotPDFWriter("__multipagetest", "3141")
    assert o.file_count == 0
    
    o.close()
    
    assert o.filename == "__multipagetest.3141"
    assert o.pdf is not None
    assert os.path.exists("__multipagetest.3141")

    os.remove("__multipagetest.3141")
    

def test_MultiplePlotPDFWriter_save():
    ax = plt.axes()
    
    o = multipage.MultiplePlotPDFWriter("__multipagetest", "pdf")
    o.save(ax.figure, 1)
    o.save(ax.figure, 2)
    o.close()
    
    assert os.path.exists( "__multipagetest.pdf" )
    assert o.file_count == 1
    
    os.remove( "__multipagetest.pdf" )
    plt.close(ax.figure)
    
    
def test_MultiplePlotPDFWriter_close():
    o = multipage.MultiplePlotPDFWriter("__multipagetest", "pdf")
    
    try:
        o.close()
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
        
    if os.path.exists("__multipagetest.pdf"):
        os.remove("__multipagetest.pdf")


def test_MultiplePlotPostscriptWriter___init__():
    o = multipage.MultiplePlotPostscriptWriter("__multipagetest", "ps")
    assert o.file_count == 0
    assert o.filename == "__multipagetest.ps"
    assert o.page_count == 0


def test_MultiplePlotPostscriptWriter_save():
    ax = plt.axes()
    
    o = multipage.MultiplePlotPostscriptWriter("__multipagetest", "ps")
    o.save(ax.figure, 1)
    o.save(ax.figure, 2)
    o.close()
    
    assert os.path.exists( "__multipagetest.ps" )
    assert o.file_count == 1
    assert o.page_count == 2
    
    os.remove( "__multipagetest.ps" )
    plt.close(ax.figure)
    
    
def test_MultiplePlotPostscriptWriter_close():
    o = multipage.MultiplePlotPostscriptWriter("__multipagetest", "ps")
    
    try:
        o.close()
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
        
    if os.path.exists("__multipagetest.ps"):
        os.remove("__multipagetest.ps")
