from ..proposals import Linearized
import numpy as np
from ..utils.utils import choose, customcholesky
from ..utils.unscentedtransform import UnscentedTransform
from ..distributions.continuous import MultivariateNormal, Normal


class Unscented(Linearized):
    """
    Implements the Unscented proposal developed in "The Unscented Particle Filter" by van der Merwe et al.
    """
    def __init__(self, **utkwargs):
        super().__init__()
        self.ut = None     # type: UnscentedTransform
        self._ut_settings = utkwargs

    def set_model(self, model, nested=False):
        self._model = model
        self._nested = nested
        self.ut = UnscentedTransform(model, **self._ut_settings)

        return self

    def draw(self, y, x, size=None, *args, **kwargs):
        mean, cov = self.ut.construct(y)

        if self._model.hidden_ndim > 1:
            self._kernel = MultivariateNormal(mean, customcholesky(cov))
        else:
            self._kernel = Normal(mean[0], np.sqrt(cov[0, 0]))

        return self._kernel.rvs(size=size)

    def resample(self, inds):
        self.ut._mean = choose(self.ut._mean, inds)
        self.ut._cov = choose(self.ut._cov, inds)

        return self


class GlobalUnscented(Unscented):
    def draw(self, y, x, size=None, *args, **kwargs):
        mean, cov = self.ut.globalconstruct(y, x)

        if self._model.hidden_ndim > 1:
            self._kernel = MultivariateNormal(mean, customcholesky(cov))
        else:
            self._kernel = Normal(mean[0], np.sqrt(cov[0, 0]))

        return self._kernel.rvs(size=size)

    def resample(self, inds):
        return self