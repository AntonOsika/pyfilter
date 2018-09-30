import unittest
from pyfilter.timeseries import BaseModel, EulerMaruyma
import scipy.stats as stats
import numpy as np
import torch
from torch.distributions import Normal


def f(x, alpha, sigma):
    return alpha * x


def g(x, alpha, sigma):
    return sigma


def f0(alpha, sigma):
    return 0.


def g0(alpha, sigma):
    return sigma


class Tests(unittest.TestCase):
    norm = Normal(0., 1.)

    linear = BaseModel((f0, g0), (f, g), (1, 1), (norm, norm))

    def test_TimeseriesCreate_1D(self):

        assert self.linear.mean(1.) == 1. and self.linear.scale(1.) == 1.

    def test_Timeseries2DState(self):
        x = np.random.normal(size=500)

        assert np.allclose(self.linear.mean(x), f(x, 1, 1))

    def test_Timeseries3DState2DParam(self):
        alpha = 0.5 * torch.ones((500, 1))
        x = torch.randn(size=(500, 200))
        linear = BaseModel((f0, g0), (f, g), (alpha, 1.), (Normal(0., 1.), Normal(0., 1.)))

        assert np.allclose(linear.mean(x), f(x, alpha, 1.))

    def test_SampleInitial(self):
        x = self.linear.i_sample()

        assert isinstance(x, torch.Tensor)

    def test_Propagate(self):
        out = torch.zeros(500)

        out[0] = self.linear.i_sample()

        for i in range(1, out.shape[0]):
            out[i] = self.linear.propagate(out[i-1])

        assert not all(out == 0.)

    def test_SampleTrajectory1D(self):
        sample = self.linear.sample(500)

        assert sample.shape[0] == 500

    def test_SampleTrajectory2D(self):
        sample = self.linear.sample(500, 250)

        assert sample.shape == (500, 250)

    def test_Weight1D(self):
        sample = self.linear.i_sample()

        obs = 0

        assert self.linear.weight(obs, sample) == stats.norm.logpdf(obs, loc=sample, scale=1)

    def test_Weight2D(self):
        sample = self.linear.i_sample(shape=(500, 200))

        obs = 1

        assert np.allclose(self.linear.weight(obs, sample), stats.norm.logpdf(obs, loc=sample, scale=1))

    def test_OverrideParameters(self):
        "Just make sure it runs"
        sample = self.linear.i_sample(shape=500)

        x = self.linear.propagate(sample, params=(2, 2))

    def test_EulerMaruyama(self):
        mod = EulerMaruyma((lambda: 0., lambda: 1.), (lambda u: 0, lambda u: 1), (), (Normal(0., 1.), Normal(0., 1.)))

        samples = mod.sample(30)

        assert samples.shape == (30, 1)


