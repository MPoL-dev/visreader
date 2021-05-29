# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.9.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# + nbsphinx="hidden"
# %matplotlib inline

# + nbsphinx="hidden"
# %run notebook_setup
# -

# # Walkthrough: Examining DSHARP AS 209 Weights and Exporting Visibilities
#
# In this walkthrough tutorial, we'll use CASA tools to examine the visibilities, visibility residuals, and weights of a real multi-configuration dataset from the DSHARP survey.
#
# ## Obtaining and CLEANing the AS 209 measurement set
#
# The calibrated measurement sets from the DSHARP data release are available [online](https://almascience.eso.org/almadata/lp/DSHARP/), and the full description of the survey is provided in [Andrews et al. 2018](https://ui.adsabs.harvard.edu/abs/2018ApJ...869L..41A/abstract).
#
# ### Model Visibilities and MODEL_DATA
# In its simplest form, the measurement set just contains the visibility data in a ``DATA`` or ``CORRECTED_DATA`` column. In the process of using ``tclean`` to synthesize an image, however, CASA also calculates a set of model visibilities that correspond to the Fourier transform of the CLEAN model. It's possible to store these model visibilities to the measurement set if the ``tclean`` process was invoked with the ``savemodel="modelcolumn"`` parameter. The model visibilities will be stored in a ``MODEL_DATA`` column with the same shape as the ``DATA`` column.
#
# The calibrated DSHARP measurement sets available from the archive do not contain this ``MODEL_DATA`` column (most likely for space reasons), so we will need to recreate them by running the ``tclean`` algorithm with the relevant settings. The full reduction scripts are [available online](https://almascience.eso.org/almadata/lp/DSHARP/scripts/AS209_continuum.py), but we just need reproduce the relevant ``tclean`` commands used to produce a FITS image from the final, calibrated measurement set.
#
# Because the measurement set is large (0.9 Gb) and the ``tclean`` process is computationally expensive (taking about 1 hr on a single core), we have pre-executed those commands and cached the measurement set and ``tclean`` products into the ``AS209_MS`` local directory. If you're interested in the exact ``tclean`` commands used, please check out the [dl_and_tclean_AS209.py](dl_and_tclean_AS209.py) script directly.

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import os

# change to the cached subdirectory that contains the cleaned MS
workdir = "AS209_MS"
os.chdir(workdir)
fname = "AS209_continuum.ms"
fitsname = "AS209.fits"

# ### Visualizing the CLEANed image
# Just to make sure the ``tclean`` process ran OK, let's check the synthesized image that was produced

from astropy.io import fits

hdul = fits.open(fitsname)
header = hdul[0].header
data = 1e3 * hdul[0].data  # mJy/pixel
# get the coordinate labels
nx = header["NAXIS1"]
ny = header["NAXIS2"]
# RA coordinates
CDELT1 = 3600 * header["CDELT1"]  # arcsec (converted from decimal deg)
CRPIX1 = header["CRPIX1"] - 1.0  # Now indexed from 0
# DEC coordinates
CDELT2 = 3600 * header["CDELT2"]  # arcsec
CRPIX2 = header["CRPIX2"] - 1.0  # Now indexed from 0
RA = (np.arange(nx) - nx / 2) * CDELT1  # [arcsec]
DEC = (np.arange(ny) - ny / 2) * CDELT2  # [arcsec]
# extent needs to include extra half-pixels.
# RA, DEC are pixel centers
ext = (
    RA[0] - CDELT1 / 2,
    RA[-1] + CDELT1 / 2,
    DEC[0] - CDELT2 / 2,
    DEC[-1] + CDELT2 / 2,
)  # [arcsec]
norm = matplotlib.colors.Normalize(vmin=0, vmax=np.max(data))

fig, ax = plt.subplots(nrows=1, figsize=(4.5, 3.5))
fig.subplots_adjust(left=0.2, bottom=0.2)
im = ax.imshow(data, extent=ext, origin="lower", animated=True, norm=norm)
cb = plt.colorbar(im, label="mJy / pixel")
r = 2.2
ax.set_xlim(r, -r)
ax.set_ylim(-r, r)
ax.set_xlabel(r"$\Delta \alpha \cos \delta$ [${}^{\prime\prime}$]")
ax.set_ylabel(r"$\Delta \delta$ [${}^{\prime\prime}$]")

# Great, it looks like things check out. Note that the main reason (at least for this tutorial) that we ran ``tclean`` was to generate the ``MODEL_DATA`` column in the measurement set. The actual CLEANed FITS image is just a nice byproduct.

# ## Examining measurement set structure
#
# Before you dive into the full analysis with CASA tools, it's a very good idea to inspect the measurement set using [listobs](https://casa.nrao.edu/casadocs-devel/stable/global-task-list/task_listobs/about).
#
# After you've done that, let's start exploring the visibility values. First we'll need to import and then instantiate the relevant CASA tools, [table](https://casa.nrao.edu/casadocs-devel/stable/global-tool-list/tool_table/methods) and [ms](https://casa.nrao.edu/casadocs-devel/stable/global-tool-list/tool_ms/methods).

import casatools

tb = casatools.table()
ms = casatools.ms()

# We can get the indexes of the unique spectral windows, which are typically indexed by the ``DATA_DESC_ID``.

tb.open(fname + "/DATA_DESCRIPTION")
SPECTRAL_WINDOW_ID = tb.getcol("SPECTRAL_WINDOW_ID")
tb.close()
print(SPECTRAL_WINDOW_ID)

# We see that there are 25 separate spectral windows! This is because the DSHARP images were produced using all available Band 6 continuum data on each source---not just the long baseline observations acquired in ALMA cycle 4. The merging of all of these individual observations is what creates this structure with so many spectral windows.

# Next, let's open the main table of the measurement set and inspect the column names

tb.open(fname)
colnames = tb.colnames()
tb.close()
print(colnames)

# Because there are multiple spectral windows which do not share the same dimensions, we cannot use the ``tb`` tool to read the data directly. If we try, we'll get an error.

try:
    tb.open(fname)
    weight = tb.getcol("WEIGHT")  # array of float64 with shape [npol, nvis]
    flag = tb.getcol("FLAG")  # array of bool with shape [npol, nchan, nvis]
    data = tb.getcol("DATA")  # array of complex128 with shape [npol, nchan, nvis]
except RuntimeError:
    print(
        "We can't use table tools here... the spws have different numbers of channels"
    )
finally:
    tb.close()

# So, we'll need to use the ``ms`` tool to read the visibilities for each spectral window, like so

ms.open(fname)
# select the spectral window
ms.selectinit(datadescid=0)
# query the desired columnames as a list
query = ms.getdata(["WEIGHT", "UVW", "DATA"])
# always a good idea to reset the earmarked data
ms.selectinit(reset=True)
ms.close()

# The returned query is a dictionary whose keys are the lowercase column names

print(query.keys())

# and whose values are the numerical arrays for the spectral window that we queried

print(query["data"])


# ## Using the tclean model to calculate residual visibilities
#
# In any data analysis where you're computing a forward model, it's a good consitency check to examine the data residuals from that model, and, in particular, whether their scatter matches the expectations from the noise properties.
#
# We can calculate data residuals using the model visibilities derived from the tclean model and stored in the ``MODEL_DATA`` column of the measurement set.

ms.open(fname)
# select the spectral window
ms.selectinit(datadescid=0)
# query the desired columnames as a list
query = ms.getdata(["MODEL_DATA"])
# always a good idea to reset the earmarked data
ms.selectinit(reset=True)
ms.close()

print(query["model_data"])

# Using these model visibilities, let's calculate the residuals for each polarization (XX, YY) in units of $\sigma$, where
#
# $$
# \sigma = \mathrm{sigma\_rescale} \times \sigma_0
# $$
#
# and
#
# $$
# \sigma_0 = \sqrt{1/w}
# $$
#
# The scatter is defined as
#
# $$
# \mathrm{scatter} = \frac{\mathrm{DATA} - \mathrm{MODEL\_DATA}}{\sigma}
# $$
# For now, $\mathrm{sigma\_rescale} = 1$, but we'll see why this parameter is needed in a moment.

# ### Helper functions for examining weight scatter
# Because we'd like to repeat this analysis for each spectral window in the measurement set, it makes things easier if we write these calculations as functions.
#
# The functions provided in this document are only dependent on the CASA tools ``tb`` and ``ms``. If you find yourself using these routines frequently, you might consider installing the *visread* package, since similar commands are provided in the API.


def get_scatter_datadescid(datadescid, sigma_rescale=1.0, apply_flags=True):
    """
    Calculate the scatter for each polarization.

    Args:
        datadescid (int): the DATA_DESC_ID to be queried
        sigma_rescale (int):  multiply the uncertainties by this factor
        apply_flags (bool): calculate the scatter *after* the flags have been applied

    Returns:
        scatter_XX, scatter_YY: a 2-tuple of numpy arrays containing the scatter in each polarization.
        If ``apply_flags==True``, each array will be 1-dimensional. If ``apply_flags==False``, each array
        will retain its original shape, including channelization (e.g., shape ``nchan,nvis``).
    """
    ms.open(fname)
    # select the key
    ms.selectinit(datadescid=datadescid)
    query = ms.getdata(
        ["DATA", "MODEL_DATA", "WEIGHT", "UVW", "ANTENNA1", "ANTENNA2", "FLAG"]
    )
    ms.selectinit(reset=True)
    ms.close()

    data, model_data, weight, flag = (
        query["data"],
        query["model_data"],
        query["weight"],
        query["flag"],
    )

    assert (
        len(model_data) > 0
    ), "MODEL_DATA column empty, retry tclean with savemodel='modelcolumn'"

    # subtract model from data
    residuals = data - model_data

    # calculate sigma from weight
    sigma = np.sqrt(1 / weight)
    sigma *= sigma_rescale

    # divide by weight, augmented for channel dim
    scatter = residuals / sigma[:, np.newaxis, :]

    # separate polarizations
    scatter_XX, scatter_YY = scatter
    flag_XX, flag_YY = flag

    if apply_flags:
        # flatten across channels
        scatter_XX = scatter_XX[~flag_XX]
        scatter_YY = scatter_YY[~flag_YY]

    return scatter_XX, scatter_YY


def gaussian(x):
    r"""
    Evaluate a reference Gaussian as a function of :math:`x`

    Args:
        x (float): location to evaluate Gaussian

    The Gaussian is defined as

    .. math::

        f(x) = \frac{1}{\sqrt{2 \pi}} \exp \left ( -\frac{x^2}{2}\right )

    Returns:
        Gaussian function evaluated at :math:`x`
    """
    return 1 / np.sqrt(2 * np.pi) * np.exp(-0.5 * x ** 2)


def scatter_hist(scatter_XX, scatter_YY, log=False, **kwargs):
    """
    Plot a normalized histogram of scatter for real and imaginary
    components of XX and YY polarizations.

    Args:
        scatter_XX (1D numpy array)
        scatter_YY (1D numpy array)

    Returns:
        matplotlib figure
    """
    xs = np.linspace(-5, 5)

    figsize = kwargs.get("figsize", (6, 6))
    bins = kwargs.get("bins", 40)

    fig, ax = plt.subplots(ncols=2, nrows=2, figsize=figsize)
    ax[0, 0].hist(scatter_XX.real, bins=bins, density=True, log=log)
    ax[0, 0].set_xlabel(
        r"$\Re \{ V_\mathrm{XX} - \bar{V}_\mathrm{XX} \} / \sigma_\mathrm{XX}$"
    )
    ax[0, 1].hist(scatter_XX.imag, bins=bins, density=True, log=log)
    ax[0, 1].set_xlabel(
        r"$\Im \{ V_\mathrm{XX} - \bar{V}_\mathrm{XX} \} / \sigma_\mathrm{XX}$"
    )

    ax[1, 0].hist(scatter_YY.real, bins=bins, density=True, log=log)
    ax[1, 0].set_xlabel(
        r"$\Re \{ V_\mathrm{YY} - \bar{V}_\mathrm{YY} \} / \sigma_\mathrm{YY}$"
    )
    ax[1, 1].hist(scatter_YY.imag, bins=bins, density=True, log=log)
    ax[1, 1].set_xlabel(
        r"$\Im \{ V_\mathrm{YY} - \bar{V}_\mathrm{YY} \} / \sigma_\mathrm{YY}$"
    )

    for a in ax.flatten():
        a.plot(xs, gaussian(xs))

    fig.subplots_adjust(hspace=0.25, top=0.95)

    return fig


def plot_histogram_datadescid(
    datadescid, sigma_rescale=1.0, log=False, apply_flags=True
):
    """Wrap the scatter routine to plot a histogram of scatter for real and imaginary components of XX and YY polarizations, given a ``DATA_DESC_ID``.

    Args:
        datadescid (int): the DATA_DESC_ID to be queried
        sigma_rescale (int):  multiply the uncertainties by this factor
        log (bool): plot the histogram with a log stretch
        apply_flags (bool): calculate the scatter *after* the flags have been applied


    Returns:
        matplotlib figure
    """

    scatter_XX, scatter_YY = get_scatter_datadescid(
        datadescid=datadescid, sigma_rescale=sigma_rescale, apply_flags=apply_flags
    )

    scatter_XX = scatter_XX.flatten()
    scatter_YY = scatter_YY.flatten()

    fig = scatter_hist(scatter_XX, scatter_YY, log=log)
    fig.suptitle("DATA_DESC_ID: {:}".format(datadescid))


# ## Checking scatter for each spectral window
# Now lets use our helper functions to investigate the characteristics of each spectral window.

# ### Spectral Window 7: A correctly scaled SPW
# Let's see how the residual visibilities in spectral window 7 scatter relative to their expected Gaussian envelope

plot_histogram_datadescid(7, apply_flags=False)

# Great, it looks like things are pretty much as we would expect here.

# ### Spectral Window 22: Visibility outliers
# In the last example, we were a little bit cavalier and plotted the residuals for *all* visibilities, regardless of whether their ``FLAG`` was true. If we do the same for the visibilities in spectral window 22,

plot_histogram_datadescid(22, apply_flags=False)

# We find that something looks a little bit strange. Let's try plotting things on a log scale to get a closer look.

plot_histogram_datadescid(22, apply_flags=False, log=True)

# It appears as though there are several "outlier" visibilities included in this spectral window. If the calibration and data preparation processes were done correctly, most likely, these visibilities are actually flagged. Let's try plotting only the valid, unflagged, visibilities

plot_histogram_datadescid(22, apply_flags=True, log=True)

# Great, it looks like the outlier visibilities were correctly flagged, and everything checks out.

# ### Spectral Window 24: Incorrectly scaled weights

# 24 no outliers, but scaled incorrectly
plot_histogram_datadescid(24)

# That's strange, the scatter of these visibilities looks reasonably Gaussian, but the scatter is too large relative to what should be expected given the weight values.
#
# If we rescale the $\sigma$ values to make them a factor of $\sqrt{2}$ larger (decrease the weight values by a factor of 2), it looks like everything checks out

plot_histogram_datadescid(24, sigma_rescale=np.sqrt(2))


# ## Rescaling weights for export.
# We can use the previous routines to iterate through plots of each spectral window. We see that the visibilities in the following spectral windows need to be rescaled by a factor of $\sqrt{2}$:

SPWS_RESCALE = [9, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]

# for ID in SPECTRAL_WINDOW_ID:
#     plot_histogram_datadescid(ID)

#
#
# We'll draw upon the "Introduction to CASA tools" tutorial to read all of the visibilities, average polarizations, convert baselines to kilolambda, etc. The difference is that in this application we will need to treat the visibilities on a per-spectral window basis *and* we will need to rescale the weights when they are incorrect relative to the actual scatter.
