Commandline Interface
=====================

We provide a commandline interface to easily submit any available task to Tractor or retrieve information about tasks and processors.


Usage
-----

**Available Subcommands**::

    >> jobtronaut -h
    usage: -c [-h] {info,visualize,list,submit} ...

    positional arguments:
      {info,visualize,list,submit}
        submit              Submit a job to the farm.
        list                Can list all known plugins.
        info                Get more info on a specific plugin.
        visualize           Visualize the resulting task tree.

    optional arguments:
      -h, --help            show this help message and exit


**jobtronaut submit**::

    >> jobtronaut submit -h
    usage: -c submit [-h] [--paused] --task TASK [--title TITLE]
                     [--service SERVICE] [--afterjids JIDS] [--priority PRIORITY]
                     [--tags TAGS [TAGS ...]] [--projects PROJECTS [PROJECTS ...]]
                     [--args ARGNAME:ARGVALUE [ARGNAME:ARGVALUE ...]]
                     [--env ENVVAR:ENVVALUE [ENVVAR:ENVVALUE ...]]

    optional arguments:
      -h, --help            show this help message and exit
      --paused              Submit the job in a paused state.
      --local               Submit the job locally. All commands will be enforced
                            to run on the spoolhost.
      --task TASK           Set the root task for the job.
      --title TITLE         Set a custom job title.
      --service SERVICE     Specify a hostmask to limit the blades this job can
                            run on.
      --afterjids JIDS      Only start the job when the jobs with these ids are
                            done.
      --priority PRIORITY   Set the priority of the job.
      --tags TAGS [TAGS ...]
                            Speficy custom limit tags on the job.
      --projects PROJECTS [PROJECTS ...]
                            Specify the projects of the job.
      --args ARGNAME:ARGVALUE [ARGNAME:ARGVALUE ...]
                            Job Arguments. Supported value types are: str, int,
                            float, list
      --env ENVVAR:ENVVALUE [ENVVAR:ENVVALUE ...]
                            Custom environment variables that will be set prior to
                            a command's execution on the farm


**jobtronaut list**::

    >> jobtronaut list -h
    usage: -c list [-h] {all,tasks,processors}

    positional arguments:
      {all,tasks,processors}
                            Define which plugins you want to list.

    optional arguments:
      -h, --help            Show this help message and exit
      --info                Show the detailed information for every plugin.

**jobtronaut info**::

    >> jobtronaut info -h
    usage: -c info [-h] plugin

    positional arguments:
      plugin      Specify the plugin name for which you want more information.

    optional arguments:
      -h, --help  show this help message and exit

