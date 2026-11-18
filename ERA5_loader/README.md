![ERA5](era5.png)

# ERA5 reanalysis info

**ERA5** is the latest climate reanalysis produced by the European Centre for Medium-Range Weather Forecasts (ECMWF), providing hourly data on many atmospheric, land-surface and sea-state parameters together with estimates of uncertainty. 

* It is the fifth generation ECMWF atmospheric reanalysis of the global climate.

* The extension of the ERA5 reanalysis back to 1940 supplements the previously published segment covering 1979 to the present.

* The ERA5 uses a 4D-Var data assimilation system. This system is based on the method used by numerical weather prediction centers, where every 12 hours, a previous forecast is combined with newly available observations in an optimal way to produce a new best estimate of the state of the atmosphere. This new estimate, called an analysis, is then used to issue an updated, improved forecast. The ERA5 employs a hybrid data assimilation system and a 10-member ensemble 4D-VAR data assimilation (EDA) at 62km horizontal grid-mesh, with 137 levels in the vertical.

* The model used in ERA5 is the ECMWF Integrated Forecast System (IFS) CY41R2. This model includes 137 hybrid sigma-pressure (model) levels in the vertical, up to a top level of 0.01 hPa. The atmospheric model in the IFS is coupled to a land-surface model (HTESSEL), which produces parameters such as 2m temperature and soil temperatures, and an ocean wave model (WAM). The ERA5 dataset contains one (hourly, 31 km) high-resolution realization (referred to as “reanalysis” or “HRES”) and a reduced resolution ten-member ensemble (referred to as “ensemble” or “EDA”). 

* In the context of the ERA5 model, an ensemble member refers to one of the ten individual model realizations that are run with slightly different initial conditions. These ensemble members include small perturbations in atmospheric variables based on the data error. The ensemble is required for the data assimilation procedure, but as a by-product also provides an estimate of the relative, random uncertainty. The ensemble members are identified by a number ranging from 0 to 9. The ensemble mean is typically calculated as the mean of all ensemble members.

* The ERA5 provides global, hourly estimates of atmospheric, ocean-wave, and land-surface variables. The data cover the Earth on a 30km grid and resolve the atmosphere using 137 levels from the surface up to a height of 80km. However, it’s also available on regular latitude-longitude grids at 0.25 x 0.25 degree resolution. The native spatial resolution of the ERA5-Land reanalysis dataset is 9km on a reduced Gaussian grid (TCo1279). ERA5 is updated daily with a latency of about 5 days (monthly means are available around the 6th of each month).

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

# ERA5 API

