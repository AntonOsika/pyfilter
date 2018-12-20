from .base import Proposal
from torch.distributions import Normal, MultivariateNormal, Independent
from ..timeseries import LinearGaussianObservations as LGO
import torch


# TODO: Seems to work for 1D models currently, will need to extend to multidimensional
class LinearGaussianObservations(Proposal):
    def set_model(self, model):
        if not isinstance(model, LGO):
            raise ValueError('Model must be of instance {}'.format(LGO.__name__))

        self._model = model

        return self

    @staticmethod
    def _kernel_1d(y, loc, h_var_inv, o_var_inv, c):
        cov = 1 / (h_var_inv + c ** 2 * o_var_inv)
        m = cov * (h_var_inv * loc + c * o_var_inv * y)

        kernel = Normal(m, cov.sqrt())

        return kernel

    def _kernel_2d(self, y, loc, h_var_inv, o_var_inv, c):
        tc = c if c.dim() > 1 else c.unsqueeze(0)

        # ===== Define covariance ===== #
        t2 = torch.matmul(tc.t(), o_var_inv.unsqueeze(-1) * tc)

        cov = (torch.diag(h_var_inv) + t2).inverse()

        # ===== Get mean ===== #
        t1 = h_var_inv * loc

        t2 = o_var_inv * y
        t3 = torch.matmul(tc.t(), t2)

        m = torch.matmul(cov, (t1 + t3).unsqueeze(-1))[..., 0]

        return MultivariateNormal(m, scale_tril=torch.cholesky(cov))

    def draw(self, y, x, size=None, *args, **kwargs):
        # ===== Hidden ===== #
        loc = self._model.hidden.mean(x)
        h_var_inv = 1 / self._model.hidden.scale(x) ** 2

        # ===== Observable ===== #
        c = self._model.observable.theta_vals[0]
        o_var_inv = 1 / self._model.observable.scale(x) ** 2

        if self._model.hidden_ndim < 2:
            kernel = self._kernel_1d(y, loc, h_var_inv, o_var_inv, c)
        else:
            kernel = self._kernel_2d(y, loc, h_var_inv, o_var_inv, c)

        return kernel.sample()

    def weight(self, y, xn, xo, *args, **kwargs):
        c = self._model.observable.theta_vals[0]
        fx = self._model.hidden.mean(xo)

        m = self._model.observable.mean(fx)

        h_var = self._model.hidden.scale(xo) ** 2
        o_var = self._model.observable.scale(xo) ** 2

        if self._model.hidden_ndim < 2:
            std = (h_var + c ** 2 * o_var).sqrt()

            return Normal(m, std).log_prob(y)

        tc = c if c.dim() > 1 else c.unsqueeze(0)

        temp = torch.matmul(tc, h_var.unsqueeze(-1) * tc.t())
        cov = torch.diag(o_var) + temp

        if cov.shape[0] > 1:
            return MultivariateNormal(m, scale_tril=torch.cholesky(cov)).log_prob(y)

        return Normal(m, cov[..., 0, 0].sqrt()).log_prob(y)