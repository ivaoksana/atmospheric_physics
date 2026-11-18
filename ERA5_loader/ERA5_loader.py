import cdsapi
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import os
from datetime import datetime, date
from numbers import Real
from typing import Any

def download_era5_data(
        output_dir,
        variable,
        current_date,
        mode="hourly",
        daily_statistic=None,
        frequency="4_hourly",
        time_zone="utc+00:00",
        times=None,
        pressure_levels=None,
        area=None,
        grid_resolution=None,
        file_format="netcdf"
    ):
    """
    Download one ERA5 file for a specified date.

    Parameters
    ----------
    output_dir : str or os.PathLike
        Directory where the downloaded file will be saved.

    variable : str
        ERA5 variable to download (e.g., "2m_temperature").

    current_date : str, datetime or date
        Target date in "DD-MM-YYYY" format, datetime or date object.
        The date represents a single day for hourly and daily modes,
        or a month for monthly mode.

    mode : str, default "hourly"
        Temporal processing mode:
        - "hourly": hourly ERA5 data.
        - "daily": daily statistics derived from hourly data.
        - "monthly": monthly averaged ERA5 data.

    daily_statistic : str, optional
        Daily statistic to retrieve in daily mode.
        Available options depend on the dataset and variable.
        For pressure-level data, daily mean, maximum and minimum
        are available. Daily sum is available only for supported
        accumulated single-level variables.
        If None, the default daily statistic is used.

    frequency : str, default "4_hourly"
        Sub-daily sampling frequency used to calculate daily
        statistics. Used only in daily mode.

    time_zone : str, default "utc+00:00"
        Time zone used for daily aggregation.
        Used only in daily mode.

    times : list of str, optional
        Requested hours in "HH:MM" format (e.g., ["00:00", "06:00"]).
        Used only in hourly mode. If None, all 24 hourly time steps
        are requested.

    pressure_levels : list of str or int, optional
        Pressure levels in hPa.
        If None, single-level data are requested.

    area : list of float, optional
        Geographic bounding box in the format
        [North, West, South, East].

    grid_resolution : list of float, optional
        Output grid resolution in the format [latitude, longitude].
        Used only in hourly mode. If None, the default resolution
        is [1.0, 1.0].

    file_format : str, default "netcdf"
        Output data format: "netcdf" or "grib".
        Daily statistics are provided as NetCDF files
        within ZIP archives.

    Returns
    -------
    str
        Path to the downloaded file.
    """

    # 1. Validate output directory
    if not isinstance(output_dir, (str, os.PathLike)):
        raise TypeError("'output_dir' must be a string or path-like object")

    output_dir = os.fspath(output_dir) or "."

    # 2. Validate variable
    if not isinstance(variable, str) or not variable.strip():
        raise ValueError("'variable' must be a non-empty string")

    # 3. Validate date
    if isinstance(current_date, datetime):
        pass

    elif isinstance(current_date, date):
        current_date = datetime.combine(current_date, datetime.min.time())

    elif isinstance(current_date, str):
        try:
            current_date = datetime.strptime(current_date, "%d-%m-%Y")
        except ValueError:
            raise ValueError("'current_date' must have format 'DD-MM-YYYY'")

    else:
        raise TypeError("'current_date' must be a datetime, date, or string in 'DD-MM-YYYY' format")

    year = str(current_date.year)
    month = f"{current_date.month:02d}"
    day = f"{current_date.day:02d}"

    # 4. Validate mode
    valid_modes = {"hourly", "daily", "monthly"}

    if mode not in valid_modes:
        raise ValueError(f"'mode' must be one of {valid_modes}")

    # 5. Validate file format
    if file_format not in {"netcdf", "grib"}:
        raise ValueError("'file_format' must be 'netcdf' or 'grib'")

    if mode == "daily" and file_format != "netcdf":
        raise ValueError("Daily statistics are available only as NetCDF files inside a ZIP archive")

    # 6. Validate times
    if times is not None:
        if not isinstance(times, (list, tuple)) or not times:
            raise ValueError("'times' must be a non-empty list or tuple")

        for t in times:
            if not isinstance(t, str):
                raise TypeError("Each time must be a string")
            try:
                datetime.strptime(t, "%H:%M")
            except ValueError:
                raise ValueError(f"Invalid time: {t}. Expected HH:MM")

    if mode != "hourly" and times is not None:
        raise ValueError("'times' can only be specified in hourly mode")

    # 7. Validate area
    if area is not None:

        if not isinstance(area, (list, tuple)) or len(area) != 4:
            raise ValueError("'area' must contain [North, West, South, East]")

        if not all(isinstance(x, Real) and not isinstance(x, bool) for x in area):
            raise TypeError("'area' coordinates must be numeric")

        north, west, south, east = area

        if not (-90 <= north <= 90 and -90 <= south <= 90):
            raise ValueError("Latitude must be between -90 and 90")

        if not (-180 <= west <= 180 and -180 <= east <= 180):
            raise ValueError("Longitude must be between -180 and 180")

        if north < south:
            raise ValueError("North latitude must be greater than South latitude")

    # 8. Validate pressure levels
    if pressure_levels is not None:

        if not isinstance(pressure_levels, (list, tuple)) or not pressure_levels:
            raise ValueError("pressure_levels must be a non-empty list or None")

        pressure_levels = [str(level) for level in pressure_levels]


    # 9. Validate grid resolution
    if grid_resolution is not None:

        if not isinstance(grid_resolution, (list, tuple)) or len(grid_resolution) != 2:
            raise ValueError("'grid_resolution' must contain [latitude, longitude]")

        if not all(
                isinstance(x, Real)
                and not isinstance(x, bool)
                and x > 0
                for x in grid_resolution
        ):
            raise ValueError("Grid resolution values must be positive numbers")

    if  grid_resolution is None:
        grid_resolution = [1.0, 1.0]

    # 10. Validate daily statistics
    valid_statistics = {
        "mean",
        "maximum",
        "minimum",
    }
    if mode == "daily":

        if daily_statistic is None or daily_statistic not in valid_statistics:
            raise ValueError(f"'daily_statistic' must be one of {valid_statistics}")

        daily_statistic = "daily_" + daily_statistic

        if frequency not in {"1_hourly", "3_hourly","6_hourly"}:
            raise ValueError("frequency must be 1_hourly, 3_hourly, or 6_hourly")

        if time_zone not in {
            f"utc{sign}{hour:02d}:00"
            for sign in ("+", "-")
            for hour in range(0, 15)
        }:
            raise ValueError("Invalid time_zone. Example: utc+00:00")


    # 11. Select dataset
    is_pressure = pressure_levels is not None

    if mode == "hourly":
        dataset = (
            "reanalysis-era5-pressure-levels"
            if is_pressure
            else "reanalysis-era5-single-levels"
        )

    elif mode == "daily":
        dataset = (
            "derived-era5-pressure-levels-daily-statistics"
            if is_pressure
            else "derived-era5-single-levels-daily-statistics"
        )

    else:  # monthly
        dataset = (
            "reanalysis-era5-pressure-levels-monthly-means"
            if is_pressure
            else "reanalysis-era5-single-levels-monthly-means"
        )


    # 12. Define output file
    level_suffix = "_pressure" if is_pressure else "_single"

    if mode == "hourly":

        extension = ".nc" if file_format == "netcdf" else ".grib"

        output_file = os.path.join(
            output_dir,
            f"{variable}{level_suffix}_{year}-{month}-{day}{extension}"
        )

    elif mode == "daily":

        output_file = os.path.join(
            output_dir,
            f"{variable}{level_suffix}_{year}-{month}-{day}_{daily_statistic}.zip"
        )

    else:  # monthly

        extension = ".nc" if file_format == "netcdf" else ".grib"

        output_file = os.path.join(
            output_dir,
            f"{variable}{level_suffix}_{year}-{month}{extension}"
        )

    # 13. Check existing file
    if os.path.exists(output_file):
        print(f"File already exists: {output_file}")
        return output_file

    os.makedirs(output_dir, exist_ok=True)


    # 14. Build request

    request_params: dict[str, Any] = {
        "variable": [variable],
        "year": [year],
        "month": [month],
    }

    if area is not None:
        request_params["area"] = list(area)

    if grid_resolution is not None:
        request_params["grid"] = list(grid_resolution)

    if mode == "hourly":

        request_params.update({
            "product_type": ["reanalysis"],
            "day": [day],
            "time": (
                list(times)
                if times is not None
                else [f"{hour:02d}:00" for hour in range(24)]
            ),
            "data_format": file_format
        })

    elif mode == "daily":

        request_params.update({
            "product_type": ["reanalysis"],
            "day": [day],
            "daily_statistic": daily_statistic,
            "time_zone": time_zone,
            "frequency": frequency
        })

        if pressure_levels is not None:
            request_params["pressure_level"] = pressure_levels

    else:  # monthly

        request_params.update({
            "product_type": ["monthly_averaged_reanalysis"],
            "data_format": file_format
        })

    if mode == "hourly" and pressure_levels is not None:
        request_params["pressure_level"] = pressure_levels

    if mode == "monthly" and pressure_levels is not None:
        request_params["pressure_level"] = pressure_levels

    # 15. Download
    try:
        print(f"Downloading ERA5 {mode} data: {output_file}")

        client = cdsapi.Client()

        client.retrieve(
            dataset,
            request_params,
            output_file
        )

        print(f"Saved to: {output_file}")

        return output_file

    except Exception as e:

        print(f"Download failed: {e}")

        if os.path.exists(output_file):
            os.remove(output_file)

        return None


def download_era5_data_for_period(
    output_dir,
    variable,
    date_from,
    date_to,
    mode="hourly",
    daily_statistic=None,
    frequency="4_hourly",
    time_zone="utc+00:00",
    times=None,
    pressure_levels=None,
    area=None,
    grid_resolution=None,
    file_format="netcdf"
):
    """
    Download ERA5 data for a specified period.

    The function generates a sequence of dates based on the selected
    mode and downloads one file for each date or month using
    download_era5_data().

    Downloads are performed sequentially.

    Parameters
    ----------
    output_dir : str or os.PathLike
        Directory where downloaded files will be saved.

    variable : str
        ERA5 variable to download (e.g., "2m_temperature").

    date_from : str
        Start date in "DD-MM-YYYY" format.

    date_to : str
        End date in "DD-MM-YYYY" format.

    mode : str, default "hourly"
        Temporal processing mode:
        - "hourly": hourly ERA5 data, one file per day.
        - "daily": daily statistics, one file per day.
        - "monthly": monthly averaged data, one file per month.

    daily_statistic : str, optional
        Daily statistic to retrieve in daily mode.
        Available options depend on the dataset and variable.
        For pressure-level data, daily mean, maximum and minimum
        are available. Daily sum is available only for supported
        accumulated single-level variables.
        If None, the default daily statistic is used.

    frequency : str, default "4_hourly"
        Sub-daily sampling frequency used to calculate daily
        statistics. Used only in daily mode.

    time_zone : str, default "utc+00:00"
        Time zone used for daily aggregation.
        Used only in daily mode.

    times : list of str, optional
        Requested hours in "HH:MM" format.
        Used only in hourly mode. If None, all 24 hourly time steps
        are requested.

    pressure_levels : list of str or int, optional
        Pressure levels in hPa.
        If None, single-level data are requested.

    area : list of float, optional
        Geographic bounding box in the format
        [North, West, South, East].

    grid_resolution : list of float, optional
        Output grid resolution in the format [latitude, longitude].
        Used only in hourly mode. If None, the default resolution
        is [1.0, 1.0].

    file_format : str, default "netcdf"
        Output data format: "netcdf" or "grib".
        Daily statistics are provided as NetCDF files
        within ZIP archives.

    Returns
    -------
    list of str
        Paths to successfully downloaded files, ordered
        chronologically.
    """

    downloaded_files = []

    # Generate dates based on the selected mode
    if mode in {"hourly", "daily"}:

        dates = pd.date_range(
            start=date_from,
            end=date_to,
            freq="D"
        )

    elif mode == "monthly":

        dates = pd.date_range(
            start=date_from.replace(day=1),
            end=date_to.replace(day=1),
            freq="MS"
        )

    for date in dates:

        try:
            result = download_era5_data(
                output_dir=output_dir,
                variable=variable,
                current_date=date.strftime("%d-%m-%Y"),
                times=times,
                area=area,
                pressure_levels=pressure_levels,
                file_format=file_format,
                grid_resolution=grid_resolution,
                mode=mode,
                daily_statistic=daily_statistic,
                frequency=frequency,
                time_zone=time_zone
            )

            if result:
                downloaded_files.append(result)

        except Exception as e:
            print("Download failed for %s: %s", date.strftime("%Y-%m-%d"), e)

    return downloaded_files
