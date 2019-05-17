from setuptools import setup

setup(
    name="hysplit4",
    version="0.0.0",
    description="HYSPLIT Graphics",
    author="Sonny Zinn",
    author_email="sonny.zinn@noaa.gov",
    packages=["hysplit4"],
    install_requires=["geopandas", "cartopy", "numpy"]
)
