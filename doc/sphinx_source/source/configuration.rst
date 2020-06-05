Configuration
=============

To make **Jobtronaut** fit into your environment nicely you can define your own configuation. This is supposed to be a
python file and its full filepath need to be made available via the `JOBTRONAUT_PLUGIN_PATH` env var.

The following variables can be overwritten.


.. list-table:: You can define the following variables within your configuration file to make Jobtronaut fit into your Pipeline.
    :widths: 10 5 50 50
    :header-rows: 1
    :stub-columns: 1

    * - Variable Name
      - Type
      - Description
      - Default if not defined
    * - COMMANDFLAGS_ARGUMENT_NAME
      - ``str``
      - A magic argument with the given name that can be used to inject additional flags into any command. This is especially useful if you are using an application bootstrap framework.
      - `additional_command_flags`
    * - LOGGING_NAMESPACE
      - ``str``
      - A custom namespace that can be used instead of the default one.
      - `jobtronaut`
    * -
      -
      -
      -
    * - ENABLE_PLUGIN_CACHE
      - ``bool``
      - If True it will reuse plugins from its own cache instead of resourcing modules when initializing the Plugins discovery.
      - `True`
    * - PLUGIN_PATH
      - ``list``
      - A list of directories Jobtronaut's Plugins discovery mechanism will use. All .py files in the given directories will be considered.
      - ``[]``
    * -
      -
      -
      -
    * - EXECUTABLE_RESOLVER
      - ``callable``
      - A custom callable that can be used to resolve a executable declared in within any of your Command tasks. The first item of `Task.cmd()` will be passed to the callable.
      - ``lambda x: x if os.path.isfile(x) and os.path.isabs(x) and os.access(x, os.X_OK) else (_ for _ in ()).throw(OSError("Command Id `{}` is not an executable.".format(x)))``
    * - ENVIRONMENT_RESOLVER
      - ``callable``
      - A custom callable that can be used to resolve an environment. This will be ignored in case `INHERIT_ENVIRONMENT` is set to False.
      - ``lambda: OrderedDict(sorted(os.environ.items()))``
    * - INHERIT_ENVIRONMENT
      - ``bool``
      - If set to True it will use the `ENVIRONMENT_RESOLVER` to add its return value to the envkey attribute of any resulting job.
      - `True`
    * -
      -
      -
      -
    * - ARGUMENTS_SERIALIZED_MAX_LENGTH
      - ``int``
      - The maximum number of characters a serialized Arguments object can have within a command. It it exceeds this limit the serialized Arguments will be dumped into a file within the defined `ARGUMENTS_STORAGE_PATH`.
      - `10000`
    * - ARGUMENTS_STORAGE_PATH
      - ``str``
      - A directory path where serialized Arguments objects can be dumped.
      -
    * - JOB_STORAGE_PATH_TEMPLATE
      - ``str``
      - If set it defines where .alf job representation files will be dumped whenever a job was submitted.
      -
    * -
      -
      -
      -
    * - KATANA_SCRIPT_WRAPPER
      - ``str``
      - Path to a custom python file that acts like a wrapper for Katana to allow consume python code directly.
      - ``<JOBTRONAUT_DIR>/author/scripts/katanascript.py``
    * - MAYA_SCRIPT_WRAPPER
      - ``str``
      - Path to a custom python file that acts like a wrapper for Maya to allow consume python code directly.
      - ``<JOBTRONAUT_DIR>/author/scripts/mayascript.mel``
    * - NUKE_SCRIPT_WRAPPER
      - ``str``
      - Path to a custom python file that acts like a wrapper for Nuke to allow consume python code directly.
      - ``<JOBTRONAUT_DIR>/author/scripts/nukescript.py``
    * -
      -
      -
      -
    * - TRACTOR_ENGINE_CREDENTIALS_RESOLVER
      - ``callable``
      - A custom callable that needs to be set whenever internal processes will use the tractor query api or you will use any of the jobtronaut.query features directly. This callable needs to return a valid Tractor user and password with proper permissions.
      - ``lambda: ("unknown_user", "unknown_password")``