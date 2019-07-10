from setuptools import setup

setup(
    name="hysplit4",
    version="0.0.2",
    description="HYSPLIT Graphics",
    author="Sonny Zinn",
    author_email="sonny.zinn@noaa.gov",
    packages=["hysplit4", "hysplit4.traj", "hysplit4.conc"],
    python_requires="=3.7",
    install_requires=["geopandas=0.4", "cartopy=0.17", "numpy=1.16", "pytz=2019.1", "timezonefinder-4.1"]
)
