from .smc2 import SMC2
from .ness import NESS
import numpy as np
import pandas as pd
from tqdm import tqdm


class NESSMC2(SMC2):
    def __init__(self, model, particles, handshake=0.2, nesskwargs=None, smc2kwargs=None, **kwargs):
        """
        Implements a hybrid of the NESS and SMC2 algorithm, as recommended in the NESS article. That is, we use the
        SMC2 algorithm for the first part of the series and then switch to NESS when it becomes too computationally
        demanding to use the SMC2.
        :param model: The state-space model to filter
        :type model: pyfilter.timeseries.model.StateSpaceModel
        :param particles: The number of particles to use targeting (parameters, states)
        :type particles: tuple of int
        :param handshake: At which point to switch algorithms, (in percent of length of the series) shoud be <= 1.
        :type handshake: float
        :param kwargs: Keyworded arguments used in both algorithms
        """
        super().__init__(model, particles, **kwargs)

        self._hs = handshake
        self._switched = False

        # ===== Set some key-worded arguments ===== #
        nk = nesskwargs or {}
        sm2k = smc2kwargs or {}

        self._smc2 = SMC2(model, particles, threshold=sm2k.pop('threshold', 0.4), **sm2k, **kwargs)
        self._ness = NESS(model, particles, shrinkage=nk.pop('shrinkage', 0.95), p=nk.pop('p', 1),  **nk, **kwargs)

        self._filter = self._ness._filter = self._smc2._filter

    def filter(self, y):
        if self._smc2._ior < self._hs * self._td.shape[0]:
            return self._smc2.filter(y)

        if not self._switched:
            self._switched = True

            inds = self._resamp(self._smc2._recw)
            self._filter = self._ness._filter = self._smc2._filter.resample(inds)
            self._recw = np.zeros_like(self._smc2._recw)

        return self._ness.filter(y)

    def longfilter(self, data):
        # TODO: Fix a better way to avoid copying code

        if isinstance(data, pd.DataFrame):
            data = data.values
        elif isinstance(data, list):
            data = np.array(data)

        # ===== SMC2 needs the entire dataset ==== #
        self._td = self._smc2._td = data

        for i in tqdm(range(data.shape[0]), desc=str(self.__class__.__name__), leave=True):
            self.filter(data[i])

        self._td = self._smc2._td = None

        return self