from tractor.apps.blade.TrStatusFilter import TrStatusFilter as _TrStatusFilter


class TrStatusFilter(_TrStatusFilter):
    """ wrapper arount TrStatusFilter to inject and store persistent data

    """

    def __init__(self, persistent_data={}):
        super(TrStatusFilter, self).__init__()

        self.persistent_data = persistent_data