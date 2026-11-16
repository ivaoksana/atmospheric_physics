from typing import Dict, List, Literal, Optional, Hashable
import logging
import sys
import os
import glob
import dask

import xarray as xr
import numpy as np

import cftime

# Color Formatter for Logs
class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[94m',
        'INFO': '\033[92m',
        'WARNING': '\033[93m',
        'ERROR': '\033[91m',
        'CRITICAL': '\033[1;41m'
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"


# Logger Factory
def get_logger(name='default', level=logging.DEBUG) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if not logger.hasHandlers():
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = ColorFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

# Standardize Names (dims or variables)
def standardize_names(
        ds: xr.Dataset,
        name_map: Dict[str, List[str]],
        axis: Literal['dims', 'vars'],
        debug=True
) -> xr.Dataset:
    """
    Standardize dimension or variable names in a xarray Dataset.

    This helper function is used as part of `load_nc_xarray` to harmonize
    datasets originating from different models or observational sources,
    which may use different naming conventions for the same physical
    dimensions or variables.

    Parameters
    ----------
    ds : xr.Dataset
        Input xarray Dataset whose dimensions or variables are to be renamed.

    name_map : dict[str, list[str]]
        Mapping between a standard name (dictionary key) and a list of
        alternative names (dictionary values) that may appear in the dataset.
        If any alternative name is found, it is renamed to the standard name.

        Example:
            {
                "latitude": ["lat", "Latitude", "LAT"],
                "level": ["lev", "plev", "pressure"]
            }

    axis : {"dims", "vars"}
        Specifies whether the renaming should be applied to:
        - "dims": dataset dimensions (ds.dims)
        - "vars": dataset variables (ds.data_vars)

    debug : bool, default=True
        Enable logging.

    Returns
    -------
    xr.Dataset
        Dataset with standardized dimension or variable names.
    """

    logger = get_logger('standardize_names')

    for standard_name, alternatives in name_map.items():
        for alt_name in alternatives:

            if axis == "dims" and alt_name in ds.dims:
                if alt_name != standard_name:
                    if debug:
                        logger.debug(f"Renaming dimension '{alt_name}' -> '{standard_name}'")
                    ds = ds.rename({alt_name: standard_name})

            elif axis == "vars" and alt_name in ds.data_vars:
                if alt_name != standard_name:
                    if debug:
                        logger.debug(f"Renaming variable '{alt_name}' -> '{standard_name}'")
                    ds = ds.rename({alt_name: standard_name})
    return ds


# Decode Time Coordinate
def decode_time(ds: xr.Dataset, debug: bool = True) -> xr.Dataset:
    """
    Decode CF-compliant time coordinates using xarray.

    Supports standard and non-standard CF calendars, including:
        - standard / gregorian
        - proleptic_gregorian
        - julian
        - noleap / 365_day
        - all_leap / 366_day
        - 360_day

    Calendar handling is delegated to xarray and cftime.
    Standard calendars are decoded to numpy.datetime64 where possible,
    while non-standard calendars retain cftime datetime objects.

    Parameters
    ----------
    ds : xr.Dataset
        Input dataset containing a time coordinate.
        The time coordinate must have CF-compliant units.

    debug : bool, default=True
        Enable logging messages.

    Returns
    -------
    xr.Dataset
        Dataset with decoded time coordinates.

    Raises
    ------
    ValueError
        If the time coordinate has invalid or missing CF metadata.
    RuntimeError
        If time decoding fails.
    """

    logger = get_logger("decode_time", level=logging.DEBUG)

    # Check time coordinate
    if "time" not in ds.coords:
        logger.warning("No time coordinate found. Returning dataset unchanged.")
        return ds

    time = ds["time"]

    # Check whether time is already decoded
    if np.issubdtype(time.dtype, np.datetime64):
        if debug:
            logger.debug("Time coordinate is already decoded.")
        return ds

    if time.dtype == object and time.size > 0:
        first_value = time.values.flat[0]
        if isinstance(first_value, cftime.datetime):
            if debug:
                logger.debug("Time coordinate is already decoded using cftime.")
            return ds

    # Read CF metadata
    time_units = time.attrs.get("units")
    calendar = time.attrs.get("calendar", "standard")

    if not time_units:
        raise ValueError("Time coordinate does not contain CF 'units' metadata.")

    if "since" not in time_units.lower():
        raise ValueError(f"Invalid CF time units: {time_units}")

    if debug:
        logger.debug(f"Time units: {time_units}")
        logger.debug(f"Calendar: {calendar}")

    try:
        # Let xarray select the appropriate datetime representation.
        # cftime is used automatically when numpy.datetime64 is unsuitable.
        time_coder = xr.coders.CFDatetimeCoder(use_cftime=None)

        ds = xr.decode_cf(ds,decode_times=time_coder)

        if debug:
            logger.info(f"Successfully decoded time coordinate using calendar '{calendar}'.")
            logger.debug(f"Decoded time dtype: {ds.time.dtype}")

    except Exception as e:
        logger.error(f"Time decoding failed: {e}")
        raise RuntimeError(f"Failed to decode time coordinate: {e}") from e

    return ds

# Sort Coordinates
def sort_coordinates(ds: xr.Dataset, debug=True) -> xr.Dataset:
    """
    Sort spatial and vertical coordinates into a consistent physical order.

    This function ensures that coordinates follow common geophysical
    conventions required for diagnostics of stratospheric transport.

    Parameters
    ----------
    ds : xr.Dataset
        Input xarray Dataset with latitude, longitude, and/or vertical
        coordinates.

    debug : bool, default=True
        Enable logging.

    Returns
    -------
    xr.Dataset
        Dataset with:
        - latitude sorted from south to north,
        - longitude sorted eastward and converted to [-180, 180] if needed,
        - vertical levels sorted from top to bottom (descending pressure).
    """

    logger = get_logger("sort_coordinates")

    if "latitude" in ds.dims:
        if debug:
            logger.debug("Sorting latitude ascending.")
        ds = ds.sortby("latitude")

    if "longitude" in ds.dims:
        if debug:
            logger.debug("Sorting longitude ascending.")
        ds = ds.sortby("longitude")

        if ds["longitude"].max() > 180:
            if debug:
                logger.info("Converting longitude from [0,360] to [-180,180].")
            ds["longitude"] = ((ds["longitude"] + 180) % 360) - 180
            ds = ds.sortby("longitude")

    if "level" in ds.coords and ds["level"].dims == ("level",):
        level_units = ds["level"].attrs.get("units", "").strip().lower()

        pressure_units = {
            "pa", "hpa", "mbar", "millibar",
            "millibars", "bar"
        }
        conversion_factors = {
            "pa": 0.01,
            "hpa": 1.0,
            "mbar": 1.0,
            "millibar": 1.0,
            "millibars": 1.0,
            "bar": 1000.0
        }
        if debug:
            logger.debug(f"Level units '{level_units}'.")

        if level_units in pressure_units:

            if debug:
                logger.debug(f"Converting pressure units into 'hPa'")

            factor = conversion_factors[level_units]

            if factor != 1.0:
                ds = ds.assign_coords({'level':ds["level"] * factor})

            ds['level'].attrs["units"] = "hPa"

            if debug:
                logger.debug("Sorting pressure levels descending.")

            ds = ds.sortby("level", ascending=False)

        elif debug:
            logger.debug(
                f"Skipping vertical sorting: unrecognized pressure units '{level_units}'.")

    return ds


def resolve_duplicate_coordinates(
        ds: xr.Dataset,
        coord: str,
        method: Literal["mean", "first", "last", "raise"] = "mean",
        debug: bool = True
) -> xr.Dataset:
    """
    Resolve duplicate values along a coordinate.

    Parameters
    ----------
    ds : xr.Dataset
        Input dataset.

    coord : str
        Coordinate along which duplicates are checked.

    method : {"mean", "first", "last", "raise"}, default="mean"
        Method used to resolve duplicates:
        - "mean": Calculate the mean of duplicate values.
        - "first": Keep the first occurrence.
        - "last": Keep the last occurrence.
        - "raise": Raise an error if duplicates are found.

    debug : bool, default=True
        Enable logging.

    Returns
    -------
    xr.Dataset
        Dataset with unique coordinate values.
    """

    logger = get_logger("resolve_duplicate_coordinates")

    if method not in ("mean", "first", "last", "raise"):
        raise ValueError(f"Unsupported duplicate method: {method}")

    index = ds.indexes[coord]
    duplicates = index.duplicated(keep=False)

    if not duplicates.any():
        return ds

    duplicate_values = index[duplicates].unique()

    if debug:
        logger.warning(f"Found {len(duplicate_values)} duplicated values in coordinate '{coord}'.")

    if method == "raise":
        raise ValueError(f"Duplicate values detected: {list(duplicate_values[:5])}")

    if method == "mean":
        ds = ds.groupby(coord).mean(dim=coord, keep_attrs=True)

    elif method == "first":
        ds = ds.groupby(coord).first(dim=coord)

    elif method == "last":
        ds = ds.groupby(coord).last(dim=coord)

    if debug:
        logger.info(
            f"Resolved duplicate coordinates using method '{method}'. "
            f"Removed {int(duplicates.sum()) - len(duplicate_values)} excess coordinate entries."
        )

    return ds

def preprocess_dataset(
        ds: xr.Dataset,
        debug: bool = True
) -> xr.Dataset:

    logger = get_logger("preprocess_dataset")

    # Remove unnecessary coordinates
    if 'lev' in ds and 'plev' in ds:
        ds = ds.drop('lev')

    # Standardize dimensions
    if debug:
      logger.info("Standardizing dimensions...")

    ds = standardize_names(ds, {
        'time': ['time', 't', 'valid_time', 'TIME'],
        'latitude': ['latitude', 'Latitude', 'lat', 'LAT'],
        'longitude': ['longitude', 'Longitude', 'lon', 'LON'],
        'level': [
            'level', 'lev', 'pressure_level',
            'pressure', 'plev', 'pfull', 'p',
            'pre', 'isobaricInhPa'
        ],
        'dataset': ['dataset_id']
    }, axis='dims', debug=debug)

    # Standardize variables
    if debug:
      logger.info("Standardizing variables...")

    ds = standardize_names(ds, {
        # Temperature
        't': ['temperature', 'T', 'Temperature', 'ta', 'temp', 't'],

        # Wind components
        'u': ['u', 'U', 'ua'],
        'v': ['v', 'V', 'va'],
        'w': ['w', 'W', 'wa'],

        # Geopotential
        'z': ['z', 'Z', 'geopotential', 'zg', 'geopotential_height'],

        # Potential temperature
        'theta': ['theta', 'potential_temperature', 'pt'],

        # Specific humidity
        'q': ['q', 'Q', 'specific_humidity'],

        # Potential vorticity
        'pv': ['pv', 'PV', 'potential_vorticity'],

        # Chemical tracers
        'o3': ['vmro3', 'vmr_o3', 'o3', 'O3'],
        'n2o': ['vmrn2o', 'n2o', 'N2O'],
        'ch4': ['vmrch4', 'vmr_ch4', 'ch4', 'CH4'],
        'sf6': ['vmrsf6', 'vmr_sf6', 'sf6', 'SF6'],
        'h2o': ['vmrh2o', 'vmr_h2o', 'h2o', 'H2O', 'water_vapor'],

        # Additional dynamical variables
        'vo': ['vo', 'vorticity', 'relative_vorticity'],
        'd': ['d', 'divergence', 'horizontal_divergence']

    }, axis='vars', debug=debug)

    VARIABLE_LONG_NAMES = {
        't': 'Air temperature',
        'u': 'Eastward wind component',
        'v': 'Northward wind component',
        'w': 'Vertical velocity',
        'z': 'Geopotential',
        'theta': 'Potential temperature',
        'q': 'Specific humidity',
        'pv': 'Potential vorticity',
        'o3': 'Ozone mole fraction',
        'n2o': 'Nitrous oxide mole fraction',
        'ch4': 'Methane mole fraction',
        'sf6': 'Sulfur hexafluoride mole fraction',
        'h2o': 'Water vapor mole fraction',
        'vo': 'Atmosphere relative vorticity',
        'd': 'Horizontal divergence'
    }

    for var, long_name in VARIABLE_LONG_NAMES.items():
        if var in ds.data_vars:
            ds[var].attrs['long_name'] = long_name
            units = ds[var].attrs.get('units', 'unknown')
            if debug:
                logger.info(f"Detected variable, {var} - {long_name}, units {units}.")

    # Remove unnecessary coordinates
    if 'expver' in ds.coords:
        ds = ds.drop_vars('expver')

    if 'valid_time' in ds.coords:
        ds = ds.drop_vars('valid_time')

    # Sort coordinates
    if debug:
      logger.info("Sorting coordinates...")
    ds = sort_coordinates(ds, debug=debug)

    # Decode time
    if debug:
      logger.info("Decoding time axis...")
    ds = decode_time(ds, debug=debug)

    return ds

# Reads NetCDf using xarray. Use this function for reading your data from you disk!
def load_nc_xarray(
        data_path: str,
        debug=True,
        chunks=None) -> xr.Dataset:
    """
    Load and preprocess a NetCDF dataset using xarray.

    This function provides a unified interface for loading atmospheric
    model or observational data stored in NetCDF format and preparing it
    for subsequent transport diagnostics or analysis. The preprocessing
    steps are designed to handle common inconsistencies across climate
    model outputs and reanalysis products.

    The following operations are performed:

    1. Dataset loading
       - Opens the NetCDF file with `decode_times=False` to allow for
         manual handling of non-standard calendars.

    2. Coordinate and variable name standardization
       - Harmonizes dimension names (time, latitude, longitude, level)
         and variable names (e.g., temperature, u, n2o, o3) using a
         predefined mapping to ensure consistency across datasets.

    3. Coordinate sorting
       - Sorts latitude in ascending order.
       - Sorts longitude in ascending order and converts longitudes from
         [0, 360] to [-180, 180] if necessary.
       - Sorts vertical pressure levels from down to top (descending pressure).

    4. Time decoding
       - Decodes time coordinates using CF-compliant units and calendars.
       - Supports standard, Gregorian, no-leap (365-day), and 360-day
         calendars via `cftime`.
       - Converts decoded times to pandas-compatible datetime objects
         where possible.

    5. Warning handling
       - Suppresses known xarray serialization warnings related to
         multiple fill values.

    Parameters
    ----------
    data_path : str
        Path to the NetCDF file to be loaded.

    debug : bool, default=True
        Enable logging.

    chunks : dict or None, default=None
        Dask chunk configuration.

    Returns
    -------
    xr.Dataset
        A fully preprocessed xarray Dataset with standardized names,
        sorted coordinates, and decoded time axis.

    Raises
    ------
    ValueError
        If `data_path` is not provided.
    FileNotFoundError
        If the specified NetCDF file does not exist.
    RuntimeError
        If loading or preprocessing fails.
    """
    logger = get_logger("load_nc_xarray")
    if debug:
        logger.info(f"Loading file: {data_path}")

    if not data_path:
        raise ValueError("A valid data_path must be provided.")

    try:
        ds = xr.open_dataset(data_path, decode_times=False, chunks=chunks)

        if debug:
            logger.debug(f"Dimensions: {dict(ds.sizes)}")
            logger.debug(f"Variables: {list(ds.data_vars)}")
            logger.debug(f"Coordinates: {list(ds.coords)}")

    except FileNotFoundError:
        raise FileNotFoundError(f"The file at path '{data_path}' does not exist.")
    except Exception as e:
        raise RuntimeError(f"Failed to load dataset: {e}")

    ds = preprocess_dataset(ds, debug=debug)

    if debug:
        print(ds)
    return ds

# Combine Files by coordinates
def combine_files_by_coord(
        folder: str,
        coord: str = "time",
        pattern: str = "*.nc",
        chunks=None,
        parallel: bool = False,
        engine: Optional[str] = None,
        combine: Literal["by_coords", "nested"] = "by_coords",
        concat_dim: Optional[str] = None,
        sort: bool = True,
        check_duplicates: bool = True,
        duplicate_method: Literal["mean", "first", "last", "raise"] = "mean",
        debug: bool = True
) -> Optional[xr.Dataset]:
    """
    Combine multiple NetCDF files along an arbitrary coordinate.

    Each input file is preprocessed before combination using
    preprocess_dataset(). Supports coordinate-based and nested
    combination strategies.

    Parameters
    ----------
    folder : str
        Directory containing NetCDF files.

    coord : str, default="time"
        Coordinate along which files are combined.
        Must be a one-dimensional dimension coordinate.

    pattern : str, default="*.nc"
        Glob pattern used to identify NetCDF files.

    chunks : dict or None, default=None
        Dask chunk configuration.
        No explicit chunk sizes are requested. For open_mfdataset(),
        Dask is still used automatically, and chunks are determined
        according to the input file structure. For open_dataset(),
        data are loaded lazily without Dask-backed chunking by default.

    parallel : bool, default=False
        Open input files in parallel using Dask.

    engine : str or None, default=None
        NetCDF backend engine.

    combine : {"by_coords", "nested"}, default="by_coords"
        File combination strategy.

    concat_dim : str or None, default=None
        Dimension used for nested concatenation.
        Defaults to coord.

    sort : bool, default=True
        Sort the combined dataset along coord.

    check_duplicates : bool, default=True
        Detect and resolve duplicate coordinate values.

    duplicate_method : {"mean", "first", "last", "raise"}
        Method used to resolve duplicate values.

    debug : bool, default=True
        Enable detailed logging.

    Returns
    -------
    xr.Dataset or None
        Combined and preprocessed dataset.
        Returns None if no matching files are found.
    """

    logger = get_logger("combine_files_by_coord")

    # 1. Validate input arguments
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Directory does not exist: {folder}")

    if combine not in ("by_coords", "nested"):
        raise ValueError(f"Unsupported combination method: {combine}")

    if not isinstance(coord, str) or not coord:
        raise ValueError("A valid coordinate name must be provided.")

    if combine == "nested" and concat_dim is None:
        concat_dim = coord

    # 2. Find input files
    files = sorted(glob.glob(os.path.join(folder, pattern)))

    if not files:
        logger.warning(f"No files found in '{folder}' matching '{pattern}'.")
        return None

    if debug:
        logger.info(f"Found {len(files)} NetCDF file(s).")
        for file in files:
            logger.debug(f"Input file: {os.path.basename(file)}")

    ds = None

    # 3. Open and preprocess datasets
    try:

        if len(files) == 1:

            if debug:
                logger.info("Opening a single NetCDF file.")

            ds = load_nc_xarray(
                    data_path=files[0],
                    debug=debug,
                    chunks=chunks
            )

        else:

            if debug:
                axis = concat_dim if combine == "nested" else coord
                logger.info(f"Combining {len(files)} files using combine={combine} along '{axis}'.")

            ds = xr.open_mfdataset(
                files,
                combine=combine,
                concat_dim=concat_dim if combine == "nested" else None,
                preprocess=lambda ds: preprocess_dataset(ds, debug=False),
                decode_times=False,
                chunks=chunks,
                parallel=parallel,
                engine=engine
            )

    except Exception as e:

        if ds is not None:
            ds.close()

        if debug:
            logger.error(f"Failed to open or combine NetCDF files: {e}")

        raise RuntimeError(f"Failed to combine files in '{folder}': {e}") from e

    try:

        # 4. Validate coordinate
        if coord not in ds.coords:
            raise ValueError(f"Coordinate '{coord}' not found in dataset.")

        if coord not in ds.dims:
            raise ValueError(f"Coordinate '{coord}' is not a dimension.")

        if ds[coord].dims != (coord,):
            raise ValueError(f"Coordinate '{coord}' must be one-dimensional.")

        if ds.sizes[coord] == 0:
            raise ValueError(f"Coordinate '{coord}' is empty.")

        # Check missing coordinate values
        if bool(ds[coord].isnull().any()):
            raise ValueError(f"Coordinate '{coord}' contains missing values.")


        # 5. Check duplicate coordinate values
        if check_duplicates:
            if debug:
                logger.info(f"Checking duplicates along: '{coord}'")

            if duplicate_method not in ("mean", "first", "last", "raise"):
                raise ValueError(f"Unsupported duplicate resolution method: {duplicate_method}")

            ds = resolve_duplicate_coordinates(
                ds,
                coord=coord,
                method=duplicate_method,
                debug=debug
            )

        # 6.  Sort along the selected coordinate
        if sort:
            if debug:
                logger.info(f"Sorting along '{coord}'.")

            ds = ds.sortby(coord)

        # 7. Final information
        if debug:
            logger.info(f"Successfully combined {len(files)} file(s).")

            logger.info(f"Coordinate: {coord}")

            logger.info(f"Coordinate range: {ds[coord].values[0]} to {ds[coord].values[-1]}")

            logger.info(f"Number of coordinate values: {ds.sizes[coord]}")

            logger.debug(f"Dataset dimensions: {dict(ds.sizes)}")

            print(ds)

        return ds

    except ValueError:

        ds.close()
        raise

    except Exception as e:

        ds.close()

        if debug:
            logger.error(f"Dataset validation failed: {e}")

        raise RuntimeError(f"Failed to validate coordinate '{coord}': {e}") from e
