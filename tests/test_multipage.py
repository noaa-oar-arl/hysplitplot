import matplotlib.pyplot as plt
import os
import pytest

from hysplitplot import multipage, const


def test_PlotFileWriterFactory_create_instance():
    o = multipage.PlotFileWriterFactory.create_instance(const.Frames.ALL_FILES_ON_ONE, "test", "pdf")
    assert isinstance(o, multipage.MultiplePlotPDFWriter)
    if os.path.exists("test.pdf"):
        os.remove("test.pdf")
        
    o = multipage.PlotFileWriterFactory.create_instance(const.Frames.ALL_FILES_ON_ONE, "test", "PDF")
    assert isinstance(o, multipage.MultiplePlotPDFWriter)
    if os.path.exists("test.PDF"):
        os.remove("test.PDF")
            
    # A PNG image file cannot have more than one page.
    o = multipage.PlotFileWriterFactory.create_instance(const.Frames.ALL_FILES_ON_ONE, "test", "PNG")
    assert isinstance(o, multipage.SinglePlotFileWriter)


def test_SinglePlotFileWriter___init__():
    o = multipage.SinglePlotFileWriter("test", "png")
    assert o.output_basename == "test"
    assert o.output_suffix == "png"
    

def test_SinglePlotFileWriter_save():
    ax = plt.axes()
    
    o = multipage.SinglePlotFileWriter("__multipagetest", "png")
    o.save(ax.figure, 1)
    
    assert os.path.exists( "__multipagetest0001.png" )
    
    os.remove( "__multipagetest0001.png" )
    plt.close(ax.figure)
    
    
def test_SinglePlotFileWriter__make_filename():
    o = multipage.SinglePlotFileWriter("output", "ps")
     
    assert o._make_filename(1) == "output0001.ps"
    assert o._make_filename(2) == "output0002.ps"


def test_SinglePlotFileWriter_close():
    o = multipage.SinglePlotFileWriter("output", "ps")
    
    try:
        o.close()
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))


def test_MultiplePlotPDFWriter___init__():
    if os.path.exists("__multipagetest.pdf"):
        os.remove("__multipagetest.pdf")
        
    o = multipage.MultiplePlotPDFWriter("__multipagetest", "pdf")
    o.close()
    
    assert o.filename == "__multipagetest.pdf"
    assert o.pdf is not None
    assert os.path.exists("__multipagetest.pdf")

    os.remove("__multipagetest.pdf")
    

def test_MultiplePlotPDFWriter_save():
    ax = plt.axes()
    
    o = multipage.MultiplePlotPDFWriter("__multipagetest", "pdf")
    o.save(ax.figure, 1)
    o.save(ax.figure, 2)
    o.close()
    
    assert os.path.exists( "__multipagetest.pdf" )
    
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




