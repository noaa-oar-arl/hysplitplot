# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_clist.py
#
# Performs unit tests on functions and class methods declared in clist.py.
# ---------------------------------------------------------------------------

import os
import pytest

from hysplitplot import clist


@pytest.fixture
def clusterList():
    return clist.ClusterList(1).get_reader().read("data/CLUSLIST_4")


def test_ClusterList___init__():
    cl = clist.ClusterList(1)
    assert cl.percent is not None
    assert cl.start_index == 1
    assert cl.total_traj == 0


def test_ClusterList_get_label(clusterList):
    assert clusterList.get_label(-1) == ""
    assert clusterList.get_label(0) == "1 (30%)"
    assert clusterList.get_label(1) == "2 (10%)"
    assert clusterList.get_label(2) == "3 (38%)"
    assert clusterList.get_label(3) == "4 (22%)"
    assert clusterList.get_label(4) == ""


def test_ClusterList_get_reader():
    cl = clist.ClusterList(1)
    r = cl.get_reader()
    assert isinstance(r, clist.ClusterListReader)
    assert r.clist is cl
   
    
def test_ClusterList_clear(clusterList):
    assert len(clusterList.percent) == 4
    assert clusterList.total_traj > 0
    clusterList.clear()
    assert len(clusterList.percent) == 0
    assert clusterList.total_traj == 0
    

def test_ClusterListReader___init__():
    cl = clist.ClusterList(1)
    r = clist.ClusterListReader(cl)
    assert r.clist is cl


def test_ClusterListReader_read():
    r = clist.ClusterList(1).get_reader()
    cl = r.read("data/CLUSLIST_4")
    assert cl is r.clist
    assert len(cl.percent) == 4
    assert cl.total_traj == 112
    assert cl.percent[0] == 30
    assert cl.percent[1] == 10
    assert cl.percent[2] == 38
    assert cl.percent[3] == 22
 
