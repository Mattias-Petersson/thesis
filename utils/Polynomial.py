import cypari2
import numpy as np
from numpy.random import Generator, PCG64
import math
from cypari2.convert import gen_to_python
import hashlib


class Polynomial:
    """
    Helper class that implements Cypari to support polynomials over
    rings. This class has methods to return elements uniformly or
    Gaussianly from the ring, as well as converting polynomials
    to be in the ring (by taking the polynomial mod q and mod f(x)).
    """

    def __init__(
        self,
        N: int = 1024,
        q: int = 2**32 - 527,
    ):
        self.cypari: cypari2.pari_instance.Pari = cypari2.Pari()
        self.cypari.allocatemem(10**10)

        if not self.cypari.isprime(q):
            raise ValueError("q needs to be prime.")

        self.N = N
        self.q = q
        self.inversion = dict()
        self.inversion[1] = 1
        self.inversion[2] = 2147483385
        self.inversion[3] = 1431655590
        self.inversion[-1] = -1
        self.inversion[-2] = -2147483385
        self.inversion[-3] = -1431655590

    def uniform_element(self, bound: int = 0) -> cypari2.gen.Gen:
        if bound == 0:
            bound = (self.q - 1) // 2
        randomized_coeffs = np.random.randint(bound, size=self.N)
        return self.in_rq(self.cypari.Pol(randomized_coeffs))

    def gaussian_element(self, sigma: int) -> cypari2.gen.Gen:
        """
        TODO: Verify that this is behaving similar to a Gaussian distribution.
        """
        unrounded = np.random.normal(0, sigma, size=self.N)
        poly = self.cypari.round(self.cypari.Pol(unrounded))
        return self.in_rq(poly)

    def __uniform_list(self, n: int, bound: int = 0):
        return [self.uniform_element(bound) for _ in range(n)]

    def __gaussian_list(self, n: int, sigma: int):
        return [self.gaussian_element(sigma) for _ in range(n)]

    def in_rq(self, p: cypari2.gen.Gen):
        """
        Returns a polynomial congruent in R_q to the one sent in.

        Args:
        p: A polynomial or a list of polynomials.

        Returns:
        The polynomial that is congruent to the argument for the ring.
        """
        return self.cypari(
            p
            * self.cypari.Mod(1, self.q)
            * self.cypari.Mod(1, self.basis_poly())
        )

    def basis_poly(self) -> cypari2.gen.Gen:
        fx = f"x^{self.N} + 1"
        return self.cypari.Pol(fx)

    def __shape_helper(
        self, n: int | tuple[int, int], is_uniform: bool = False
    ):
        lst_helper = lambda n, bound: (
            self.__uniform_list(n, bound)
            if is_uniform
            else self.__gaussian_list(n, bound)
        )
        element_helper = lambda bound: (
            self.uniform_element(bound)
            if is_uniform
            else self.gaussian_element(bound)
        )
        if isinstance(n, int):
            func = lambda n, sigma: (
                element_helper(sigma)
                if n == 1
                else self.cypari.vector(n, lst_helper(n, sigma))
            )
        else:
            func = lambda n, sigma: self.cypari.matrix(
                *n, lst_helper(n[0] * n[1], sigma)
            )
        return func

    def uniform_array(
        self, n: int | tuple[int, int], bound: int = 0
    ) -> cypari2.gen.Gen | list[cypari2.gen.Gen]:
        func = self.__shape_helper(n, is_uniform=True)
        return func(n, sigma=bound)

    def uniform_bounded_array(
        self, n: int, bound: int
    ) -> list[cypari2.gen.Gen]:
        return self.cypari.vector(n, self.__uniform_list(n, bound))

    def gaussian_array(
        self, n: int | tuple[int, int], sigma: int
    ) -> cypari2.gen.Gen | list[cypari2.gen.Gen]:
        func = self.__shape_helper(n)
        return func(n, sigma)

    def ones(self, n: int) -> list[cypari2.gen.Gen]:
        return self.in_rq(self.cypari.matid(n))

    def l2_norm(self, list) -> float:
        return math.sqrt(sum([i**2 % self.q for i in list]))

    def pol_to_arr(self, pol) -> list[int]:
        pariVec = self.cypari.Vec(self.cypari.liftall(pol))
        return gen_to_python(pariVec)

    def challenge(
        self, kappa: int, seed: list[int] | None = None
    ) -> cypari2.gen.Gen:
        """
        Provides a polynomial in the ring R_q with an l_inf norm of one.
        Additionally, it has a l_1 norm of kappa and should be small in
        relation to N. We limit the degree of the polynomial to one fourth
        of N. A seed can be supplied to always produce the same output
        polynomial, which is useful for mapping a hash to a polynomial.
        """
        gen = Generator(PCG64(seed))
        bound = self.N // 4
        indices = gen.choice(range(bound), size=kappa, replace=False)
        coeffs = gen.choice(["+", "-"], size=kappa)
        pol = ""
        for i, j in zip(coeffs, indices):
            pol += i + f"x^{j}"
        return self.cypari.Pol(pol)

    def small_invertible(self, kappa: int) -> cypari2.gen.Gen:
        """
        The difference of two challenges c will have an l_inf norm of at
        most two. As such, all elements here will be invertible in R_q.
        """
        c1 = self.challenge(kappa)
        c2 = self.challenge(kappa)
        while self.cypari(c1 == c2):
            c1 = self.challenge(kappa)
        return self.cypari(c2 - c1)

    def hash(self, kappa: int, *args) -> cypari2.gen.Gen:
        """
        Hash an input of an arbitrary number of polynomial arrays, outputting
        a single polynomial.
        """
        h = hashlib.sha384()
        for i in args:
            h.update(str.encode(str(i)))
        integers_hash: list[int] = [i for i in h.digest()]
        return self.challenge(kappa=kappa, seed=integers_hash)
