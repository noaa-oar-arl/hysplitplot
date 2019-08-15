from setuptools import setup

setup(
    name="hysplitplot",
    version="0.1.0",
    description="HYSPLIT Graphics",
    author="Sonny Zinn",
    author_email="sonny.zinn@noaa.gov",
    packages=["hysplitplot", "hysplitplot.traj", "hysplitplot.conc"],
    python_requires="==3.7",
    install_requires=["hysplitdata==0.0", "geopandas==0.4", "cartopy==0.17",
                      "numpy==1.16", "pytz==2019.1", "timezonefinder==4.1",
                      "contextily==0.99", "mercantile==1.1"]
)
