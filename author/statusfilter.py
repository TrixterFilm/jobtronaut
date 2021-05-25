from tractor.apps.blade.TrStatusFilter import TrStatusFilter as _TrStatusFilter

from ..constants import BASH_STYLES
from .plugins import Plugins


class TrStatusFilter(_TrStatusFilter):
    """ wrapper around TrStatusFilter to inject and store persistent data

    """

    description = "Base StatusFilter class to derive from."

    def __init__(self, persistent_data={}):
        super(TrStatusFilter, self).__init__()

        self.persistent_data = persistent_data

    @classmethod
    def info(cls, short=True):
        """ Provides a nicely formatted representation to be used as a terminal
        output.

        Arguments:
            cls (class): The class which should be formatted
        """

        if short:
            infostr = "{BOLD}{BG_PURPLE}{FG_WHITE}" + cls.__name__ + "{END}"
        else:
            infostr = "\n{BOLD}{BG_PURPLE}{FG_WHITE}\n" + cls.__name__ + "\n{END}\n\n"
            infostr += "{BOLD}Description:" + "{END}\n"
            infostr += cls.description + "{END}\n\n"

            infostr += "{BOLD}Module Path:" + "{END}\n"
            infostr += Plugins().get_module_path(cls.__name__) + "{END}\n\n"

            infostr += "\n"

        return infostr.format(**BASH_STYLES)