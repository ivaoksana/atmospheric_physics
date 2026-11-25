![ERA5](era5.png)

# ERA5 reanalysis info

**ERA5** is the latest climate reanalysis produced by the European Centre for Medium-Range Weather Forecasts (ECMWF), providing hourly data on many atmospheric, land-surface and sea-state parameters together with estimates of uncertainty. 

* It is the fifth generation ECMWF atmospheric reanalysis of the global climate.

* The extension of the ERA5 reanalysis back to 1940 supplements the previously published segment covering 1979 to the present.

* The ERA5 uses a 4D-Var data assimilation system. This system is based on the method used by numerical weather prediction centers, where every 12 hours, a previous forecast is combined with newly available observations in an optimal way to produce a new best estimate of the state of the atmosphere. This new estimate, called an analysis, is then used to issue an updated, improved forecast. The ERA5 employs a hybrid data assimilation system and a 10-member ensemble 4D-VAR data assimilation (EDA) at 62km horizontal grid-mesh, with 137 levels in the vertical.

* The model used in ERA5 is the ECMWF Integrated Forecast System (IFS) CY41R2. This model includes 137 hybrid sigma-pressure (model) levels in the vertical, up to a top level of 0.01 hPa. The atmospheric model in the IFS is coupled to a land-surface model (HTESSEL), which produces parameters such as 2m temperature and soil temperatures, and an ocean wave model (WAM). The ERA5 dataset contains one (hourly, 31 km) high-resolution realization (referred to as “reanalysis” or “HRES”) and a reduced resolution ten-member ensemble (referred to as “ensemble” or “EDA”). 

* In the context of the ERA5 model, an ensemble member refers to one of the ten individual model realizations that are run with slightly different initial conditions. These ensemble members include small perturbations in atmospheric variables based on the data error. The ensemble is required for the data assimilation procedure, but as a by-product also provides an estimate of the relative, random uncertainty. The ensemble members are identified by a number ranging from 0 to 9. The ensemble mean is typically calculated as the mean of all ensemble members.

* The ERA5 provides global, hourly estimates of atmospheric, ocean-wave, and land-surface variables. The data cover the Earth on a 30km grid and resolve the atmosphere using 137 levels from the surface up to a height of 80km. However, it’s also available on regular latitude-longitude grids at 0.25 x 0.25 degree resolution. The native spatial resolution of the ERA5-Land reanalysis dataset is 9km on a reduced Gaussian grid (TCo1279). 
 
* ERA5 is updated regularly. Near-real-time ERA5T data are generally
available with a delay of about 5 days. Monthly means are typically available about 5 days after the end of the month. Availability times are not guaranteed.

* The ERA5 reanalisys product has 37 pressure levels not 137 as model!

The ERA5 dataset provides hourly estimates of a large number of atmospheric, land, and oceanic climate variables. Datasets are available on different levels such as single levels, pressure levels, potential temperature levels, potential vorticity level, and model levels. The data are available at a sub-daily and monthly frequency and consist of analyses and short (18 hour) forecasts. Here is some active links to the ERA5 data:

  * <a href="https://cds.climate.copernicus.eu/datasets/reanalysis-era5-pressure-levels?tab=overview" target="_blank">ERA5 hourly data on pressure levels from 1940 to present</a>

  * <a href="https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview" target="_blank">ERA5 hourly data on single levels from 1940 to present</a>

  * <a href="https://cds.climate.copernicus.eu/datasets/derived-era5-pressure-levels-daily-statistics?tab=overview" target="_blank">ERA5 post-processed daily statistics on pressure levels from 1940 to present</a>

    This catalogue entry provides post-processed ERA5 hourly pressure-level data aggregated to daily time steps. In addition to the data selection options found on the hourly page, the following options can be selected for the daily statistic calculation:
    
    The daily aggregation statistic (daily mean, daily max, daily min)
    The sub-daily frequency sampling of the original data (1 hour, 3 hours, 6 hours)
    The option to shift to any local time zone in UTC (no shift means the statistic is computed from UTC+00:00)
    Users should be aware that the daily aggregation is calculated during the retrieval process and is not part of a permanently archived dataset.
 
  * <a href="https://cds.climate.copernicus.eu/datasets/reanalysis-era5-pressure-levels-monthly-means?tab=overview" target="_blank">ERA5 monthly averaged data on pressure levels from 1940 to present</a>

  * <a href="https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels-monthly-means?tab=overview" target="_blank">ERA5 monthly averaged data on single levels from 1940 to present</a>
    
  * <a href="https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview" target="_blank">ERA5-Land hourly data from 1950 to present</a>

# Download data from the ERA5 API

This project provides a Python module for retrieving ERA5 data  from the Copernicus Climate Data Store (CDS) using
`ecmwf-datastores-client`.

### Step 1: Set up your CDS API credentials

Register or sign in at the [Copernicus Climate Data Store](https://cds.climate.copernicus.eu/), then obtain your API key from the [API key page](https://cds.climate.copernicus.eu/how-to-api).

Create a file named `.ecmwfdatastoresrc` in your home directory (on Windows, usually `C:\\Users\\<username>\\.ecmwfdatastoresrc`) with the following content:

```text
url: https://cds.climate.copernicus.eu/api
key: <your-personal-api-key>
```

Keep this file private. Do not add your API key to the notebook or share it.

### Step 2: Install the required packages

Install the client used by `ERA5_loader.py` and its pandas dependency:

```python
pip install ecmwf-datastores-client pandas
```

Restart the notebook kernel after installation if the package was not already available.

### Example of using
```python
from ERA5_loader import *

request_infos = submit_era5_data(
    output_dir="ERA5_data",
    variable="2m_temperature",
    start_date="01-01-2020",
    end_date="31-01-2020",
    mode="hourly",
)
# wait until your request will be accepted and then run
download_era5_results()
```
### ERA5 grid resolution

The current CDS Data Stores request schemas used here do not expose a custom `grid` parameter.
Requests therefore use the native resolution of the selected ERA5 dataset. Leave
`grid_resolution=None` (the default); a custom value is rejected explicitly by the loader.

### Required parameter database

The file `era5_parameters_database.csv` must be placed in the
same directory as `ERA5_loader.py`.

This file contains ERA5 variable metadata required by the loader.
The module will raise a `FileNotFoundError` if the database is missing.

# CDS API Request Queue Limit

The Copernicus Climate Data Store (CDS) may temporarily reject data retrieval requests when the maximum number of queued requests for a specific dataset has been reached.

This is a server-side limitation and does not necessarily indicate an error in the request parameters or the downloader itself. Even valid requests may be rejected during periods of high server demand.

**Possible error message:**
```text
Maximum number queued requests for this dataset has been reached.
Please configure your scripts to request data sequentially.
```

**What should you do?**

- Make sure that no multiple instances of the downloader are running simultaneously.
- Avoid submitting multiple requests to the same dataset at the same time.
- If a request is rejected due to the queue limit, wait for some time before trying again.
- Do not repeatedly resubmit rejected requests, as this may increase the load on the CDS service.

The downloader uses sequential requests to reduce the likelihood of reaching this limit. However, queue availability also depends on the overall CDS server workload and requests submitted by other users.

**Note:** This limitation is imposed by the CDS infrastructure and is outside the control of this downloader.

# Recommended Time for Data Downloads

CDS request processing times vary depending on the overall system workload. Although there is no officially guaranteed time when the request queue is least busy, downloads may be processed faster during off-peak hours.

**Recommended practices:**

- Consider submitting large data requests during nighttime or early morning hours (UTC), when user activity may be lower.
- Avoid peak daytime periods when possible.
- Check the current CDS queue status before starting large download operations: [CDS Live](https://cds.climate.copernicus.eu/live).
- Monitor the queue status to identify periods of lower activity.
- For large download operations, consider running the script overnight rather than during working hours.

**Important:** Nighttime downloads are not guaranteed to be faster. CDS workload varies continuously and depends on
dataset availability, request size, server capacity, and activity from other users. The recommended time window is
a practical suggestion, not an official CDS scheduling policy.

# CDS Processing Time and Request Expiration

Even small requests (a few megabytes) may remain in the CDS queue for several hours before processing completes. Additionally, completed results are stored on CDS servers only temporarily and can expire if not downloaded in time.

**Why small requests can take hours:**

- **Shared CDS queue:** The total duration shown in the CDS portal (e.g., several hours) includes the waiting time in the shared user queue (`Accepted` / `Queued`) before a worker slot is assigned, not just the time required to extract the data. When other users submit large multi-terabyte requests ahead of yours, smaller requests must wait in line.
- **MARS tape archive retrieval:** While frequently accessed ERA5 subsets reside on fast spinning disks, requests spanning many years or less common parameter combinations may require retrieving data from the ECMWF MARS tape archive, which significantly increases turnaround time.

**Request expiration (`Expired` status):**

- Completed files are retained in temporary CDS storage for a limited period—typically **24 to 72 hours** after completion (depending on current cache load, with 24 hours as the baseline retention window).
- Once a request expires, its results are deleted from the CDS server and can no longer be downloaded.
- **How this downloader handles expiration:** If a previously `successful` request has expired (`results_ready=False`), `check_era5_status()` and `download_era5_results()` automatically mark it as `expired` in `ERA5_requests.db`. Re-running `submit_era5_data()` with the same parameters will detect the expired status and automatically submit a fresh request.
