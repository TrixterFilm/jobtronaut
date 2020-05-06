Configuration
=============


.. list-table:: You can define the following variables within your configuration file to make Jobtronaut fit into your Pipeline.
    :widths: 10 5 10 50
    :header-rows: 1
    :stub-columns: 1

    * - Variable Name
      - Type
      - Description
      - Default if not defined
    * - COMMANDFLAGS_ARGUMENT_NAME
      - ``str``
      -
      - `additional_command_flags`
    * - LOGGING_NAMESPACE
      - ``str``
      -
      - `jobtronaut`
    * -
      -
      -
      -
    * - ENABLE_PLUGIN_CACHE
      - ``bool``
      -
      - `True`
    * - PLUGIN_PATH
      - ``list``
      -
      - ``[]``
    * -
      -
      -
      -
    * - EXECUTABLE_RESOLVER
      - ``callable``
      -
      - ``lambda x: x if os.path.isfile(x) and os.path.isabs(x) and os.access(x, os.X_OK) else (_ for _ in ()).throw(OSError("Command Id `{}` is not an executable.".format(x)))``
    * - ENVIRONMENT_RESOLVER
      - ``callable``
      -
      - ``lambda: OrderedDict(sorted(os.environ.items()))``
    * - INHERIT_ENVIRONMENT
      - ``bool``
      -
      - `True`
    * -
      -
      -
      -
    * - ARGUMENTS_SERIALIZED_MAX_LENGTH
      - ``int``
      -
      - `10000`
    * - ARGUMENTS_STORAGE_PATH
      - ``str``
      -
      -
    * - JOB_STORAGE_PATH_TEMPLATE
      - ``str``
      -
      -
    * -
      -
      -
      -
    * - KATANA_SCRIPT_WRAPPER
      - ``str``
      -
      - ``<JOBTRONAUT_DIR>/author/scripts/katanascript.py``
    * - MAYA_SCRIPT_WRAPPER
      - ``str``
      -
      - ``<JOBTRONAUT_DIR>/author/scripts/mayascript.mel``
    * - NUKE_SCRIPT_WRAPPER
      - ``str``
      -
      - ``<JOBTRONAUT_DIR>/author/scripts/nukescript.py``
    * -
      -
      -
      -
    * - TRACTOR_ENGINE_CREDENTIALS_RESOLVER
      - ``callable``
      -
      - ``lambda: ("user", "password")``
    * - TRACTOR_ENGINE_USER_NAME
      - ``str``
      -
      - `unknown_user`
    * - TRACTOR_ENGINE_PASSWORD
      - ``str``
      -
      - `unknown_password`