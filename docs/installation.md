# Visread Installation

:::{note}
This page describes how to install the *visread* package, along with the CASA 6.x modular installation. Note that you *do not* need to install visread or any other packages to read visibilities from CASA. All of the routines in the *Introduction to CASA tools* will work directly with the tools [built in to the monolithic CASA distributions](https://casadocs.readthedocs.io/en/stable/api/casatools.html).
:::

Because the *visread* package relies on the CASA 6.x modular installation, it is unfortunately subject to the package requirements currently imposed by that environment. More information on these requirements is [here](https://casadocs.readthedocs.io/en/stable/notebooks/introduction.html#Compatibility).

:::{note}
If you are using an operating system that doesn't support the installation of the modular CASA 6.x distribution, you can still use the casatools directly (e.g., `tb` and `ms`) via the interactive prompt of the 'monolithic' CASA 5.x series. You just won't be able to install the wrapper functionality of *visread* (though you are welcome to copy and paste relevant source code to the terminal).
:::

Following standard practice, it's recommended that you first create and activate a [Python virtual environment](https://docs.python.org/3/tutorial/venv.html) specific to your current project, whatever that may be. The CASA docs explicitly recommend using `venv` instead of a [conda environment](https://docs.conda.io/projects/conda/en/4.6.1/user-guide/tasks/manage-environments.html) (or a `virtualenv`), though it's possible that the other environments might still work.

In the following example of a virtual environment, the first line uses the `venv` tool to create a subdirectory named `venv`, which hosts the virtual environment files. The second line activates this environment in your current shell session. Keep in mind that this is something you'll need to do for every shell session, since the point of virtual environments is to create an environment specific to your project

```
$ python3 -m venv venv
$ source venv/bin/activate
```

Then you can install *visread* and the CASA dependencies with

```
$ pip install visread
```

If you have any problems, please file a detailed [Github issue](https://github.com/MPoL-dev/visread/issues).

## Installation and Usage Patterns

Case 1:

You are unable to install Modular CASA (i.e., `casatools`) into your primary computing enivronment. Common reasons include Python version incompatability (e.g., you are running Python 3.12, but Modular CASA only installs into Python 3.8) or Operating System incompatibility (e.g., you are running MacOS 14, but Modular CASA only installs into MacOS 12).

So, you normally work with CASA to reduce your data in a specialized environment that supports the installation of CASA. Presumably there are factors that make this environment more difficult to access than your primary environment (such as SSH or VNC to a server), otherwise it would probably be your primary environment.

We suggest the following workflow. In your specialized, CASA-friendly environment, install `visread[casa]` to help export the visibilities from the measurement set to a neutral data format, like `.npy` or `.asdf`. Then, trasnsfer this file to your primary environment.

Into your primary environment, install `visread`, without the CASA dependency. And you can use data visualization tools.

Case 2:

You are able to install Modular CASA into your primary computing environment. In this case, install `visread[casa]` directly into your primary environment.

## Development

If you're interested in extending the package, you can clone it from GitHub and then install it locally for development:

```
$ pip install -e .[dev]
```

If you make a useful change, please consider submitting a [pull request](https://docs.github.com/en/free-pro-team@latest/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request) to the [github repo](https://github.com/MPoL-dev/visread)!

## Testing

You can run the tests on the package by first installing it with:

```
$ pip install -e .[test]
```

(which installs the casatasks and pytest packages, you could also just additionally install those yourself, too). Then run:

```
$ python -m pytest
```

The tests work by creating a fake measurement set using [simobserve](https://casa.nrao.edu/casadocs-devel/stable/global-task-list/task_simobserve/about) and then working with it with *visread*. If any tests fail on your machine, please file a detailed [Github issue](https://github.com/MPoL-dev/visread/issues).