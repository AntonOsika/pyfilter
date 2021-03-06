import numpy as np
import abc
import scipy.stats as stats
import pyfilter.utils.utils as helps
from scipy.special import gamma
from .transforms import NonTransformable, Log, LogOdds, Interval, TransformMixin


def _get(x, y):
    """
    Returns x if not None, else y
    :param x:
    :param y:
    :return:
    """

    out = x if x is not None else y

    return np.array(out) if not isinstance(out, (np.ndarray,)) else out


class Distribution(TransformMixin):
    ndim = None
    _values = None

    @property
    def values(self):
        """
        Returns the values of current instance.
        :rtype: np.ndarray
        """
        return self._values

    @property
    def t_values(self):
        """
        Returns the transformed values of the current instance.
        :rtype: np.ndarray
        """
        return self.transform(self.values)

    @values.setter
    def values(self, x):
        """
        Sets the values of the property.
        :param x: The new parameters.
        :type x: float|int|np.ndarray
        """

        if self._values is None:
            self._values = x
            return

        assert isinstance(x, type(self._values))

        low, high = self.bounds()
        if isinstance(x, np.ndarray):
            v_low, v_high = x.min(), x.max()
            assert self._values.shape == x.shape
        else:
            v_low, v_high = x, x

        assert (v_low >= low) and (v_high <= high)

        self._values = x

        return

    @t_values.setter
    def t_values(self, x):
        """
        Sets the transformed values of the instance, i.e. inverse transforms the values and sets the values.
        :param x: The new parameters
        :type x: float|int|np.ndarray
        """
        self.values = self.inverse_transform(x)

    def sample(self, size=None):
        """
        Samples a random sample and overwrites `values`.
        :param size: The size
        :type size: tuple|list
        :return: Self
        :rtype: Distribution
        """

        self.values = self.rvs(size=size)

        return self

    def logpdf(self, *args, **kwargs):
        """
        Implements the logarithm of the PDF.
        :param args:
        :param kwargs:
        :return:
        """
        raise NotImplementedError()

    def rvs(self, *args, **kwargs):
        """
        Samples from the distribution of interest
        :param args:
        :param kwargs:
        :return:
        """
        raise NotImplementedError()

    def bounds(self):
        """
        Return the bounds on which the RV is defined.
        :return:
        """

        raise NotImplementedError()

    def std(self):
        """
        Returns the standard deviation of the RV.
        :return: 
        """

        raise NotImplementedError()

    def opt_bounds(self, offset=1e-8):
        """
        Returns optimization bounds, i.e. actual bounds offset with `offset`.
        :param offset: The offset to use
        :type offset: float
        :return:
        """

        low, up = self.bounds()

        return low + offset, up - offset


class OneDimensional(Distribution):
    ndim = 1

    def cov(self):
        return self.std() ** 2


class MultiDimensional(Distribution):
    @abc.abstractmethod
    def ndim(self):
        return 2

    def cov(self):
        return self._cov


class Normal(OneDimensional, NonTransformable):
    def __init__(self, loc=0, scale=1):
        self.loc = loc
        self.scale = scale

    def logpdf(self, x, loc=None, scale=None, size=None, **kwargs):
        m, s = _get(loc, self.loc), _get(scale, self.scale) ** 2

        return -np.log(2 * np.pi * s) / 2 - (x - m) ** 2 / 2 / s

    def rvs(self, loc=None, scale=None, size=None, **kwargs):
        m, s = _get(loc, self.loc), _get(scale, self.scale)

        return np.random.normal(loc=m, scale=s, size=size)

    def bounds(self):
        return -np.infty, np.infty

    def std(self):
        return stats.norm(loc=self.loc, scale=self.scale).std()


class Uniform(OneDimensional, Interval):
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def logpdf(self, x, *args, **kwargs):
        return stats.uniform(self.a, self.b + 1).logpdf(x)

    def rvs(self, a=None, b=None, size=None, **kwargs):
        a, b = _get(a, self.a), _get(b, self.b)

        return np.random.uniform(a, b, size=size)

    def bounds(self):
        return self.a, self.b

    def std(self):
        return stats.uniform(self.a, self.b + 1).std()


class Student(Normal, NonTransformable):
    def __init__(self, nu, loc=0, scale=1):
        super().__init__(loc, scale)
        self.nu = nu

    def logpdf(self, x, loc=None, scale=None, size=None, **kwargs):
        m, s = _get(loc, self.loc), _get(scale, self.scale)

        temp = (self.nu + 1) / 2
        diff = (x - m) / s
        t1 = np.log(gamma(temp))
        t2 = np.log(np.pi * self.nu) / 2 + np.log(gamma(self.nu / 2))
        t3 = temp * np.log(1 + diff ** 2 / self.nu)

        return t1 - (t2 + t3) - np.log(s)

    def rvs(self, loc=None, scale=None, size=None, **kwargs):
        m, s = _get(loc, self.loc), _get(scale, self.scale)

        return m + s * np.random.standard_t(self.nu, size=size)

    def std(self):
        return stats.t.std(self.nu, loc=self.loc, scale=self.scale).std()


class Gamma(OneDimensional, Log):
    def __init__(self, a, loc=0, scale=1):
        self.a = a
        self.loc = loc
        self.scale = scale

    def logpdf(self, x, a=None, loc=None, scale=None, size=None, **kwargs):
        a = _get(a, self.a)
        loc = _get(loc, self.loc)
        scale = _get(scale, self.scale)

        return stats.gamma.logpdf(x, a=a, loc=loc, scale=scale, **kwargs)

    def rvs(self, a=None, loc=None, scale=None, size=None, **kwargs):
        a = _get(a, self.a)
        loc = _get(loc, self.loc)
        scale = _get(scale, self.scale)

        return loc + np.random.gamma(a, scale, size=size)

    def bounds(self):
        return self.loc, np.infty

    def std(self):
        return stats.gamma(a=self.a, loc=self.loc, scale=self.scale).std()


class InverseGamma(OneDimensional, Log):
    def __init__(self, a, loc=0, scale=1):
        self.a = a
        self.loc = loc
        self.scale = scale

    def std(self):
        return stats.invgamma(a=self.a, loc=self.loc, scale=self.scale).std()

    def logpdf(self, x, a=None, loc=None, scale=None, size=None, **kwargs):
        a = _get(a, self.a)
        loc = _get(loc, self.loc)
        scale = _get(scale, self.scale)

        return stats.invgamma.logpdf(x, a=a, loc=loc, scale=scale, **kwargs)

    def rvs(self, a=None, loc=None, scale=None, size=None, **kwargs):
        a = _get(a, self.a)
        loc = _get(loc, self.loc)
        scale = _get(scale, self.scale)

        return stats.invgamma(a, scale=scale, loc=loc).rvs(size=size)

    def bounds(self):
        return self.loc, np.infty


class Beta(OneDimensional, LogOdds):
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def rvs(self, a=None, b=None, size=None, **kwargs):
        a, b = _get(a, self.a), _get(b, self.b)

        return np.random.beta(a, b, size=size)

    def logpdf(self, x, a=None, b=None, size=None, **kwargs):
        a, b = _get(a, self.a), _get(b, self.b)
        return stats.beta.logpdf(x, a, b)

    def bounds(self):
        return 0, 1

    def std(self):
        return stats.beta(a=self.a, b=self.b).std()


class Exponential(OneDimensional, Log):
    def __init__(self, lam):
        self.lam = lam

    def rvs(self, lam=None, size=None, **kwargs):
        return np.random.exponential(1 / _get(lam, self.lam), size=size)

    def logpdf(self, x, lam=None, **kwargs):
        return stats.expon(scale=1 / _get(lam, self.lam)).logpdf(x)

    def bounds(self):
        return 0, np.inf

    def std(self):
        return stats.expon(scale=1 / self.lam).std()


class MultivariateNormal(MultiDimensional, NonTransformable):
    def __init__(self, mean=np.zeros(2), scale=np.eye(2), ndim=None):

        if ndim:
            self._mean = np.zeros(ndim)
            self._cov = np.eye(ndim)
            self._ndim = ndim
        else:
            self._mean = mean
            self._cov = scale
            self._ndim = scale.shape[0]

        self._hmean = np.zeros(self._ndim)
        self._hcov = np.eye(self._ndim)

    @property
    def ndim(self):
        return self._ndim

    def rvs(self, loc=None, scale=None, size=None, **kwargs):
        loc, scale = _get(loc, self._mean), _get(scale, self._cov)

        rvs = np.random.multivariate_normal(mean=self._hmean, cov=self._hcov, size=(size or loc.shape[1:]))
        scaledrvs = np.einsum('ij...,...j->i...', scale, rvs)

        try:
            return loc + scaledrvs
        except ValueError:
            return (loc + scaledrvs.T).T

    def logpdf(self, x, loc=None, scale=None, **kwargs):
        loc, scale = _get(loc, self._mean), _get(scale, self._cov)

        cov = helps.outer(scale, self._hcov)

        t1 = - 0.5 * np.log(np.linalg.det(2 * np.pi * cov.T)).T
        t2 = - 0.5 * helps.square((x.T - loc.T).T, np.linalg.inv(cov.T).T)

        return t1 + t2

    def bounds(self):
        bound = np.infty * np.ones_like(self._mean)
        return -bound, bound

    def std(self):
        return self._cov