A Python utility for loading, preprocessing, and combining atmospheric NetCDF datasets using xarray.

The module is designed to simplify the handling of atmospheric model outputs and reanalysis datasets by providing a consistent structure for coordinates, variables, and time axes. It aims to reduce inconsistencies between different data sources and facilitate subsequent atmospheric analysis.

## Features

1. NetCDF loading
* Load individual NetCDF files using xarray.

* Support lazy data loading.

* Optional Dask chunking for handling large datasets.

* Configurable logging for monitoring the loading and preprocessing steps.

2. Coordinate and variable standardization

The module harmonizes common naming conventions used by different atmospheric datasets.

The recognized aliases are predefined in the module and can be extended to accommodate additional datasets.

3. Time coordinate decoding

The module decodes CF-compliant time coordinates using xarray and cftime.

Supported calendar types include:

* standard / gregorian

* proleptic_gregorian

* julian

* noleap / 365_day

* all_leap / 366_day

* 360_day

Standard calendars are decoded to NumPy datetime objects when possible, while non-standard calendars retain cftime datetime objects.

4. Coordinate sorting and normalization

The preprocessing pipeline applies the following operations:

* Sort latitude in ascending order (south to north).

* Sort longitude in ascending order (eastward).

* Convert longitude from [0, 360] to [-180, 180] when necessary.

* Convert recognized pressure units to hPa.

* Sort pressure levels in descending order.

* Vertical sorting and unit conversion are performed only when recognized pressure units are available.

5. Combining multiple NetCDF files

The combine_files_by_coord() function supports combining multiple NetCDF files along a selected coordinate.

Two combination strategies are available:

* by_coords — combines datasets based on their coordinate values.

* nested — combines datasets according to the supplied file order using concatenation.

Additional options include:

* Dask chunk configuration.

* Parallel file opening.

* Selection of a NetCDF backend engine.

* Sorting along the selected coordinate.

* Detection and handling of duplicate coordinate values.


## Installation

Clone or download this repository and install the required Python packages:

pip install numpy xarray dask cftime

A NetCDF backend such as netCDF4 or h5netcdf may also be installed:

pip install netCDF4

### Usage

Load a single NetCDF file
```python
from custom_netcdf_loader import load_nc_xarray

data = load_nc_xarray(
    data_path="path/to/dataset.nc",
    debug=True
)
```
The returned object is an xarray.Dataset with standardized names, normalized coordinates, and a decoded time axis.
```python
Load large datasets with Dask

data = load_nc_xarray(
    data_path="path/to/dataset.nc",
    chunks={"time": 30},
    debug=False
)
```
Chunk sizes should be selected according to the dataset dimensions, available memory, and intended analysis.

Combine multiple NetCDF files
```python
from custom_netcdf_loader import combine_files_by_coord

ds = combine_files_by_coord(
    folder="path/to/netcdf/files",
    coord="time",
    pattern="*.nc",
    combine="by_coords",
    chunks=None,
    parallel=False,
    sort=True,
    check_duplicates=True,
    duplicate_method="mean",
    debug=True
)
```
The function returns a combined xarray.Dataset. If no files match the specified pattern, it returns None.

Use nested concatenation

For datasets that should be concatenated according to file order:

```python
ds = combine_files_by_coord(
    folder="path/to/netcdf/files",
    coord="time",
    pattern="*.nc",
    combine="nested",
    concat_dim="time",
    sort=True,
    check_duplicates=True,
    duplicate_method="first"
)
```
With combine="nested", the input files are ordered lexicographically by filename. Therefore, filenames should follow the intended concatenation order.

## Project structure

```python
project/
│
├── custom_netcdf_loader.py
├── sample.ipynb
└── README.md
```
custom_netcdf_loader.py — main module containing the loading, preprocessing, coordinate standardization, time decoding, and file combination functions.

sample.ipynb — example notebook demonstrating module usage and testing time decoding for different CF calendars.

README.md — project documentation.

Notes and limitations

The module is designed for datasets with recognizable atmospheric coordinate and variable conventions. Unrecognized names are not automatically inferred.

Coordinate and variable aliases are defined explicitly in the preprocessing function.

Pressure unit conversion is performed only for recognized units.

The coord argument in combine_files_by_coord() must refer to a one-dimensional dimension coordinate.

With combine="nested", the file order determines concatenation order.

Duplicate handling with mean averages data variables along the selected coordinate. This should be used only when averaging duplicate records is scientifically appropriate.

The returned datasets may remain lazily backed by their source files. Keep the source files accessible while working with the dataset and close the dataset when it is no longer needed.

Dependencies

* Python

* NumPy

* xarray

* Dask

* cftime

A compatible NetCDF backend (netCDF4 or h5netcdf)

License

No license has been specified yet.