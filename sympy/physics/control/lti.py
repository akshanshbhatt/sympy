from sympy import Basic, Mul, Pow, degree, Symbol, expand, cancel, Expr, exp, roots, ShapeError
from sympy.core.evalf import EvalfMixin
from sympy.core.logic import fuzzy_and
from sympy.core.numbers import Integer
from sympy.core.sympify import sympify, _sympify
from sympy.polys import Poly, rootof
from sympy.series import limit

__all__ = ['TransferFunction', 'Series', 'Parallel', 'Feedback', 'TransferFunctionMatrix']


def _roots(poly, var):
    """ like roots, but works on higher-order polynomials. """
    r = roots(poly, var, multiple=True)
    n = degree(poly)
    if len(r) != n:
        r = [rootof(poly, var, k) for k in range(n)]
    return r


class TransferFunction(Basic, EvalfMixin):
    """
    A class for representing LTI (Linear, time-invariant) systems that can be strictly described
    by ratio of polynomials in the Laplace Transform complex variable. The arguments
    are ``num``, ``den``, and ``var``, where ``num`` and ``den`` are numerator and
    denominator polynomials of the ``TransferFunction`` respectively, and the third argument is
    a complex variable of the Laplace transform used by these polynomials of the transfer function.
    ``num`` and ``den`` can be either polynomials or numbers, whereas ``var``
    has to be a Symbol.

    Parameters
    ==========

    num : Expr, Number
        The numerator polynomial of the transfer function.
    den : Expr, Number
        The denominator polynomial of the transfer function.
    var : Symbol
        Complex variable of the Laplace transform used by the
        polynomials of the transfer function.

    Raises
    ======

    TypeError
        When ``var`` is not a Symbol or when ``num`` or ``den`` is not
        a number or a polynomial. Also, when ``num`` or ``den`` has
        a time delay term.
    ValueError
        When ``den`` is zero.

    Examples
    ========

    >>> from sympy.abc import s, p, a
    >>> from sympy.physics.control.lti import TransferFunction
    >>> tf1 = TransferFunction(s + a, s**2 + s + 1, s)
    >>> tf1
    TransferFunction(a + s, s**2 + s + 1, s)
    >>> tf1.num
    a + s
    >>> tf1.den
    s**2 + s + 1
    >>> tf1.var
    s
    >>> tf1.args
    (a + s, s**2 + s + 1, s)

    Any complex variable can be used for ``var``.

    >>> tf2 = TransferFunction(a*p**3 - a*p**2 + s*p, p + a**2, p)
    >>> tf2
    TransferFunction(a*p**3 - a*p**2 + p*s, a**2 + p, p)
    >>> tf3 = TransferFunction((p + 3)*(p - 1), (p - 1)*(p + 5), p)
    >>> tf3
    TransferFunction((p - 1)*(p + 3), (p - 1)*(p + 5), p)

    To negate a transfer function the ``-`` operator can be prepended:

    >>> tf4 = TransferFunction(-a + s, p**2 + s, p)
    >>> -tf4
    TransferFunction(a - s, p**2 + s, p)
    >>> tf5 = TransferFunction(s**4 - 2*s**3 + 5*s + 4, s + 4, s)
    >>> -tf5
    TransferFunction(-s**4 + 2*s**3 - 5*s - 4, s + 4, s)

    You can use a Float or an Integer (or other constants) as numerator and denominator:

    >>> tf6 = TransferFunction(1/2, 4, s)
    >>> tf6.num
    0.500000000000000
    >>> tf6.den
    4
    >>> tf6.var
    s
    >>> tf6.args
    (0.5, 4, s)

    You can take the integer power of a transfer function using the ``**`` operator:

    >>> tf7 = TransferFunction(s + a, s - a, s)
    >>> tf7**3
    TransferFunction((a + s)**3, (-a + s)**3, s)
    >>> tf7**0
    TransferFunction(1, 1, s)
    >>> tf8 = TransferFunction(p + 4, p - 3, p)
    >>> tf8**-1
    TransferFunction(p - 3, p + 4, p)

    Addition, subtraction, and multiplication of transfer functions can form
    unevaluated ``Series`` or ``Parallel`` objects.

    >>> tf9 = TransferFunction(s + 1, s**2 + s + 1, s)
    >>> tf10 = TransferFunction(s - p, s + 3, s)
    >>> tf11 = TransferFunction(4*s**2 + 2*s - 4, s - 1, s)
    >>> tf12 = TransferFunction(1 - s, s**2 + 4, s)
    >>> tf9 + tf10
    Parallel(TransferFunction(s + 1, s**2 + s + 1, s), TransferFunction(-p + s, s + 3, s))
    >>> tf10 - tf11
    Parallel(TransferFunction(-p + s, s + 3, s), TransferFunction(-4*s**2 - 2*s + 4, s - 1, s))
    >>> tf9 * tf10
    Series(TransferFunction(s + 1, s**2 + s + 1, s), TransferFunction(-p + s, s + 3, s))
    >>> tf10 - (tf9 + tf12)
    Parallel(TransferFunction(-p + s, s + 3, s), TransferFunction(-s - 1, s**2 + s + 1, s), TransferFunction(s - 1, s**2 + 4, s))
    >>> tf10 - (tf9 * tf12)
    Parallel(TransferFunction(-p + s, s + 3, s), Series(TransferFunction(-1, 1, s), Series(TransferFunction(s + 1, s**2 + s + 1, s), TransferFunction(1 - s, s**2 + 4, s))))
    >>> tf11 * tf10 * tf9
    Series(TransferFunction(4*s**2 + 2*s - 4, s - 1, s), TransferFunction(-p + s, s + 3, s), TransferFunction(s + 1, s**2 + s + 1, s))
    >>> tf9 * tf11 + tf10 * tf12
    Parallel(Series(TransferFunction(s + 1, s**2 + s + 1, s), TransferFunction(4*s**2 + 2*s - 4, s - 1, s)), Series(TransferFunction(-p + s, s + 3, s), TransferFunction(1 - s, s**2 + 4, s)))
    >>> (tf9 + tf12) * (tf10 + tf11)
    Series(Parallel(TransferFunction(s + 1, s**2 + s + 1, s), TransferFunction(1 - s, s**2 + 4, s)), Parallel(TransferFunction(-p + s, s + 3, s), TransferFunction(4*s**2 + 2*s - 4, s - 1, s)))

    These unevaluated ``Series`` or ``Parallel`` objects can convert into the
    resultant transfer function using ``.doit()`` method or by ``.rewrite(TransferFunction)``.

    >>> ((tf9 + tf10) * tf12).doit()
    TransferFunction((1 - s)*((-p + s)*(s**2 + s + 1) + (s + 1)*(s + 3)), (s + 3)*(s**2 + 4)*(s**2 + s + 1), s)
    >>> (tf9 * tf10 - tf11 * tf12).rewrite(TransferFunction)
    TransferFunction(-(1 - s)*(s + 3)*(s**2 + s + 1)*(4*s**2 + 2*s - 4) + (-p + s)*(s - 1)*(s + 1)*(s**2 + 4), (s - 1)*(s + 3)*(s**2 + 4)*(s**2 + s + 1), s)

    See Also
    ========

    Feedback, Series, Parallel

    """
    def __new__(cls, num, den, var):
        num, den = _sympify(num), _sympify(den)

        if not isinstance(var, Symbol):
            raise TypeError("Variable input must be a Symbol.")
        if den == 0:
            raise ValueError("TransferFunction can't have a zero denominator.")

        if (((isinstance(num, Expr) and num.has(Symbol) and not num.has(exp)) or num.is_number) and
            ((isinstance(den, Expr) and den.has(Symbol) and not den.has(exp)) or den.is_number)):
            obj = super(TransferFunction, cls).__new__(cls, num, den, var)
            obj._num = num
            obj._den = den
            obj._var = var
            obj._num_inputs, obj._num_outputs = 1, 1
            return obj
        else:
            raise TypeError("Unsupported type for numerator or denominator of TransferFunction.")

    @property
    def num(self):
        """
        Returns the numerator polynomial of the transfer function.

        Examples
        ========

        >>> from sympy.abc import s, p
        >>> from sympy.physics.control.lti import TransferFunction
        >>> G1 = TransferFunction(s**2 + p*s + 3, s - 4, s)
        >>> G1.num
        p*s + s**2 + 3
        >>> G2 = TransferFunction((p + 5)*(p - 3), (p - 3)*(p + 1), p)
        >>> G2.num
        (p - 3)*(p + 5)

        """
        return self._num

    @property
    def den(self):
        """
        Returns the denominator polynomial of the transfer function.

        Examples
        ========

        >>> from sympy.abc import s, p
        >>> from sympy.physics.control.lti import TransferFunction
        >>> G1 = TransferFunction(s + 4, p**3 - 2*p + 4, s)
        >>> G1.den
        p**3 - 2*p + 4
        >>> G2 = TransferFunction(3, 4, s)
        >>> G2.den
        4

        """
        return self._den

    @property
    def var(self):
        """
        Returns the complex variable of the Laplace transform used by the polynomials of
        the transfer function.

        Examples
        ========

        >>> from sympy.abc import s, p
        >>> from sympy.physics.control.lti import TransferFunction
        >>> G1 = TransferFunction(p**2 + 2*p + 4, p - 6, p)
        >>> G1.var
        p
        >>> G2 = TransferFunction(0, s - 5, s)
        >>> G2.var
        s

        """
        return self._var

    @property
    def num_inputs(self):
        return self._num_inputs

    @property
    def num_outputs(self):
        return self._num_outputs

    @property
    def shape(self):
        return self._num_outputs, self._num_inputs

    def _eval_subs(self, old, new):
        arg_num = self.num.subs(old, new)
        arg_den = self.den.subs(old, new)
        argnew = TransferFunction(arg_num, arg_den, self.var)
        return self if old == self.var else argnew

    def _eval_evalf(self, prec):
        return TransferFunction(
            self.num._eval_evalf(prec),
            self.den._eval_evalf(prec),
            self.var)

    def _eval_simplify(self, **kwargs):
        tf = cancel(Mul(self.num, 1/self.den, evaluate=False), expand=False).as_numer_denom()
        num_, den_ = tf[0], tf[1]
        return TransferFunction(num_, den_, self.var)

    def expand(self):
        """
        Returns the transfer function with numerator and denominator
        in expanded form.

        Examples
        ========

        >>> from sympy.abc import s, p, a, b
        >>> from sympy.physics.control.lti import TransferFunction
        >>> G1 = TransferFunction((a - s)**2, (s**2 + a)**2, s)
        >>> G1.expand()
        TransferFunction(a**2 - 2*a*s + s**2, a**2 + 2*a*s**2 + s**4, s)
        >>> G2 = TransferFunction((p + 3*b)*(p - b), (p - b)*(p + 2*b), p)
        >>> G2.expand()
        TransferFunction(-3*b**2 + 2*b*p + p**2, -2*b**2 + b*p + p**2, p)

        """
        return TransferFunction(expand(self.num), expand(self.den), self.var)

    def dc_gain(self):
        """
        Computes the gain of the response as the frequency approaches zero.

        The DC gain is infinite for systems with pure integrators.

        Examples
        ========

        >>> from sympy.abc import s, p, a, b
        >>> from sympy.physics.control.lti import TransferFunction
        >>> tf1 = TransferFunction(s + 3, s**2 - 9, s)
        >>> tf1.dc_gain()
        -1/3
        >>> tf2 = TransferFunction(p**2, p - 3 + p**3, p)
        >>> tf2.dc_gain()
        0
        >>> tf3 = TransferFunction(a*p**2 - b, s + b, s)
        >>> tf3.dc_gain()
        (a*p**2 - b)/b
        >>> tf4 = TransferFunction(1, s, s)
        >>> tf4.dc_gain()
        oo

        """
        m = Mul(self.num, Pow(self.den, -1, evaluate=False), evaluate=False)
        return limit(m, self.var, 0)

    def poles(self):
        """
        Returns the poles of a transfer function.

        Examples
        ========

        >>> from sympy.abc import s, p, a
        >>> from sympy.physics.control.lti import TransferFunction
        >>> tf1 = TransferFunction((p + 3)*(p - 1), (p - 1)*(p + 5), p)
        >>> tf1.poles()
        [-5, 1]
        >>> tf2 = TransferFunction((1 - s)**2, (s**2 + 1)**2, s)
        >>> tf2.poles()
        [I, I, -I, -I]
        >>> tf3 = TransferFunction(s**2, a*s + p, s)
        >>> tf3.poles()
        [-p/a]

        """
        return _roots(Poly(self.den, self.var), self.var)

    def zeros(self):
        """
        Returns the zeros of a transfer function.

        Examples
        ========

        >>> from sympy.abc import s, p, a
        >>> from sympy.physics.control.lti import TransferFunction
        >>> tf1 = TransferFunction((p + 3)*(p - 1), (p - 1)*(p + 5), p)
        >>> tf1.zeros()
        [-3, 1]
        >>> tf2 = TransferFunction((1 - s)**2, (s**2 + 1)**2, s)
        >>> tf2.zeros()
        [1, 1]
        >>> tf3 = TransferFunction(s**2, a*s + p, s)
        >>> tf3.zeros()
        [0, 0]

        """
        return _roots(Poly(self.num, self.var), self.var)

    def is_stable(self):
        """
        Returns True if the transfer function is asymptotically stable; else False.

        This would not check the marginal or conditional stability of the system.

        Examples
        ========

        >>> from sympy.abc import s, p, a
        >>> from sympy.core.symbol import symbols
        >>> q, r = symbols('q, r', negative=True)
        >>> from sympy.physics.control.lti import TransferFunction
        >>> tf1 = TransferFunction((1 - s)**2, (s + 1)**2, s)
        >>> tf1.is_stable()
        True
        >>> tf2 = TransferFunction((1 - p)**2, (s**2 + 1)**2, s)
        >>> tf2.is_stable()
        False
        >>> tf3 = TransferFunction(4, q*s - r, s)
        >>> tf3.is_stable()
        False

        # not enough info about the symbols to determine stability
        >>> tf4 = TransferFunction(p + 1, a*p - s**2, p)
        >>> tf4.is_stable() is None
        True

        """
        return fuzzy_and(pole.as_real_imag()[0].is_negative for pole in self.poles())

    def __add__(self, other):
        if isinstance(other, (TransferFunction, Series)):
            if not self.var == other.var:
                raise ValueError("All the transfer functions should use the same complex variable "
                    "of the Laplace transform.")
            return Parallel(self, other)
        elif isinstance(other, Parallel):
            if not self.var == other.var:
                raise ValueError("All the transfer functions should use the same complex variable "
                    "of the Laplace transform.")
            arg_list = list(other.args)
            return Parallel(self, *arg_list)
        else:
            raise ValueError("TransferFunction cannot be added with {}.".
                format(type(other)))

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        if isinstance(other, (TransferFunction, Series)):
            if not self.var == other.var:
                raise ValueError("All the transfer functions should use the same complex variable "
                    "of the Laplace transform.")
            return Parallel(self, -other)
        elif isinstance(other, Parallel):
            if not self.var == other.var:
                raise ValueError("All the transfer functions should use the same complex variable "
                    "of the Laplace transform.")
            arg_list = [-i for i in list(other.args)]
            return Parallel(self, *arg_list)
        else:
            raise ValueError("{} cannot be subtracted from a TransferFunction."
                .format(type(other)))

    def __rsub__(self, other):
        return -self + other

    def __mul__(self, other):
        if isinstance(other, (TransferFunction, Parallel)):
            if not self.var == other.var:
                raise ValueError("All the transfer functions should use the same complex variable "
                    "of the Laplace transform.")
            return Series(self, other)
        elif isinstance(other, Series):
            if not self.var == other.var:
                raise ValueError("All the transfer functions should use the same complex variable "
                    "of the Laplace transform.")
            arg_list = list(other.args)
            return Series(self, *arg_list)
        else:
            raise ValueError("TransferFunction cannot be multiplied with {}."
                .format(type(other)))

    __rmul__ = __mul__

    def __truediv__(self, other):
        if (isinstance(other, Parallel) and len(other.args) == 2 and isinstance(other.args[0], TransferFunction)
            and isinstance(other.args[1], (Series, TransferFunction))):

            if not self.var == other.var:
                raise ValueError("Both TransferFunction and Parallel should use the"
                    " same complex variable of the Laplace transform.")
            if other.args[1] == self:
                # plant and controller with unit feedback.
                return Feedback(self, other.args[0])
            other_arg_list = list(other.args[1].args) if isinstance(other.args[1], Series) else other.args[1]
            if other_arg_list == other.args[1]:
                return Feedback(self, other_arg_list)
            elif self in other_arg_list:
                other_arg_list.remove(self)
            else:
                return Feedback(self, Series(*other_arg_list))

            if len(other_arg_list) == 1:
                return Feedback(self, *other_arg_list)
            else:
                return Feedback(self, Series(*other_arg_list))
        else:
            raise ValueError("TransferFunction cannot be divided by {}.".
                format(type(other)))

    __rtruediv__ = __truediv__

    def __pow__(self, p):
        p = sympify(p)
        if not isinstance(p, Integer):
            raise ValueError("Exponent must be an Integer.")
        if p == 0:
            return TransferFunction(1, 1, self.var)
        elif p > 0:
            num_, den_ = self.num**p, self.den**p
        else:
            p = abs(p)
            num_, den_ = self.den**p, self.num**p

        return TransferFunction(num_, den_, self.var)

    def __neg__(self):
        return TransferFunction(-self.num, self.den, self.var)

    @property
    def is_proper(self):
        """
        Returns True if degree of the numerator polynomial is less than
        or equal to degree of the denominator polynomial, else False.

        Examples
        ========

        >>> from sympy.abc import s, p, a, b
        >>> from sympy.physics.control.lti import TransferFunction
        >>> tf1 = TransferFunction(b*s**2 + p**2 - a*p + s, b - p**2, s)
        >>> tf1.is_proper
        False
        >>> tf2 = TransferFunction(p**2 - 4*p, p**3 + 3*p + 2, p)
        >>> tf2.is_proper
        True

        """
        return degree(self.num, self.var) <= degree(self.den, self.var)

    @property
    def is_strictly_proper(self):
        """
        Returns True if degree of the numerator polynomial is strictly less
        than degree of the denominator polynomial, else False.

        Examples
        ========

        >>> from sympy.abc import s, p, a, b
        >>> from sympy.physics.control.lti import TransferFunction
        >>> tf1 = TransferFunction(a*p**2 + b*s, s - p, s)
        >>> tf1.is_strictly_proper
        False
        >>> tf2 = TransferFunction(s**3 - 2, s**4 + 5*s + 6, s)
        >>> tf2.is_strictly_proper
        True

        """
        return degree(self.num, self.var) < degree(self.den, self.var)

    @property
    def is_biproper(self):
        """
        Returns True if degree of the numerator polynomial is equal to
        degree of the denominator polynomial, else False.

        Examples
        ========

        >>> from sympy.abc import s, p, a, b
        >>> from sympy.physics.control.lti import TransferFunction
        >>> tf1 = TransferFunction(a*p**2 + b*s, s - p, s)
        >>> tf1.is_biproper
        True
        >>> tf2 = TransferFunction(p**2, p + a, p)
        >>> tf2.is_biproper
        False

        """
        return degree(self.num, self.var) == degree(self.den, self.var)


class Series(Basic):
    """
    A class for representing product of transfer functions or transfer functions in a
    series configuration.

    Examples
    ========

    >>> from sympy.abc import s, p, a, b
    >>> from sympy.physics.control.lti import TransferFunction, Series, Parallel
    >>> tf1 = TransferFunction(a*p**2 + b*s, s - p, s)
    >>> tf2 = TransferFunction(s**3 - 2, s**4 + 5*s + 6, s)
    >>> tf3 = TransferFunction(p**2, p + s, s)
    >>> S1 = Series(tf1, tf2)
    >>> S1
    Series(TransferFunction(a*p**2 + b*s, -p + s, s), TransferFunction(s**3 - 2, s**4 + 5*s + 6, s))
    >>> S1.var
    s
    >>> S2 = Series(tf2, Parallel(tf3, -tf1))
    >>> S2
    Series(TransferFunction(s**3 - 2, s**4 + 5*s + 6, s), Parallel(TransferFunction(p**2, p + s, s), TransferFunction(-a*p**2 - b*s, -p + s, s)))
    >>> S2.var
    s
    >>> S3 = Series(Parallel(tf1, tf2), Parallel(tf2, tf3))
    >>> S3
    Series(Parallel(TransferFunction(a*p**2 + b*s, -p + s, s), TransferFunction(s**3 - 2, s**4 + 5*s + 6, s)), Parallel(TransferFunction(s**3 - 2, s**4 + 5*s + 6, s), TransferFunction(p**2, p + s, s)))
    >>> S3.var
    s

    You can get the resultant transfer function by using ``.doit()`` method:

    >>> S3 = Series(tf1, tf2, -tf3)
    >>> S3.doit()
    TransferFunction(-p**2*(s**3 - 2)*(a*p**2 + b*s), (-p + s)*(p + s)*(s**4 + 5*s + 6), s)
    >>> S4 = Series(tf2, Parallel(tf1, -tf3))
    >>> S4.doit()
    TransferFunction((s**3 - 2)*(-p**2*(-p + s) + (p + s)*(a*p**2 + b*s)), (-p + s)*(p + s)*(s**4 + 5*s + 6), s)

    Notes
    =====

    All the transfer functions should use the same complex variable
    ``var`` of the Laplace transform.

    See Also
    ========

    Parallel, TransferFunction, Feedback

    """
    def __new__(cls, *args, evaluate=False):
        if len(args) == 0:
            raise ValueError("Needs at least 1 argument.")
        if not all(isinstance(arg, (TransferFunction, TransferFunctionMatrix, Parallel, Series))
            for arg in args):
            raise TypeError("Unsupported type of argument(s) for Series.")

        obj = super(Series, cls).__new__(cls, *args)
        obj._is_not_matrix = all(isinstance(arg.doit(), TransferFunction) for arg in args)
        if not obj._is_not_matrix:
            obj._num_outputs, obj._num_inputs = args[0].num_outputs, args[-1].num_inputs
            for x in range(len(args) - 1):
                # input-output sizes should be consistent.
                if args[x].num_inputs != args[x + 1].num_outputs:
                    raise ValueError("Argument {0} of Series has {1} input(s),"
                        " but argument {2} has {3} output(s)."
                        .format(x + 1, args[x].num_inputs, x + 2, args[x + 1].num_outputs))
        else:
            obj._num_outputs, obj._num_inputs = 1, 1

        tf = "transfer functions" if obj._is_not_matrix else "TransferFunctionMatrix objects"
        obj._var = args[0].var
        if not all(arg.var == obj._var for arg in args):
            raise ValueError("All {0} should use the same complex"
                " variable of the Laplace transform.".format(tf))
        return obj.doit() if evaluate else obj

    @property
    def var(self):
        """
        Returns the complex variable used by all the transfer functions.

        Examples
        ========

        >>> from sympy.abc import p
        >>> from sympy.physics.control.lti import TransferFunction, Series, Parallel
        >>> G1 = TransferFunction(p**2 + 2*p + 4, p - 6, p)
        >>> G2 = TransferFunction(p, 4 - p, p)
        >>> G3 = TransferFunction(0, p**4 - 1, p)
        >>> Series(G1, G2).var
        p
        >>> Series(-G3, Parallel(G1, G2)).var
        p

        """
        return self._var

    @property
    def num_inputs(self):
        return self._num_inputs

    @property
    def num_outputs(self):
        return self._num_outputs

    @property
    def shape(self):
        return self._num_outputs, self._num_inputs

    def doit(self, **kwargs):
        """
        Returns the resultant transfer function obtained after evaluating
        the transfer functions in series configuration.

        Examples
        ========

        >>> from sympy.abc import s, p, a, b
        >>> from sympy.physics.control.lti import TransferFunction, Series
        >>> tf1 = TransferFunction(a*p**2 + b*s, s - p, s)
        >>> tf2 = TransferFunction(s**3 - 2, s**4 + 5*s + 6, s)
        >>> Series(tf2, tf1).doit()
        TransferFunction((s**3 - 2)*(a*p**2 + b*s), (-p + s)*(s**4 + 5*s + 6), s)
        >>> Series(-tf1, -tf2).doit()
        TransferFunction((2 - s**3)*(-a*p**2 - b*s), (-p + s)*(s**4 + 5*s + 6), s)

        """
        res = None
        for arg in self.args:
            arg = arg.doit()
            if res is None:
                res = arg
            else:
                if self._is_not_matrix:
                    num_ = arg.num * res.num
                    den_ = arg.den * res.den
                    res = TransferFunction(num_, den_, self.var)
                else:
                    # Now we multiply two transfer function matrices...
                    # If we have two TFMs with shape (a, b) and (b, d), respectively,
                    # then the resultant TFM will be of shape (a, d).
                    if res.num_outputs == 1 and arg.num_inputs == 1:
                        a = [None]
                        for i in range(res.num_inputs):
                            if a[0] is None:
                                a[0] = res.args[0][0][i] * arg.args[0][i]
                            else:
                                a[0] += res.args[0][0][i] * arg.args[0][i]

                    elif res.num_outputs == 1 or arg.num_inputs == 1:
                        if res.num_outputs == 1:
                            a = [[None] * arg.num_inputs]

                            for j in range(arg.num_inputs):
                                for k in range(arg.num_outputs):
                                    if a[0][j] is None:
                                        a[0][j] = res.args[0][0][j] * arg.args[0][k][j]
                                    else:
                                        a[0][j] += res.args[0][0][j] * arg.args[0][k][j]

                        else:
                            a = [None] * res.num_outputs

                            for i in range(res.num_outputs):
                                for k in range(arg.num_outputs):
                                    if a[i] is None:
                                        if res.num_inputs == 1:
                                            a[i] = res.args[0][i] * arg.args[0][k]
                                        else:
                                            a[i] = res.args[0][i][k] * arg.args[0][k]
                                    else:
                                        a[i] += res.args[0][i][k] * arg.args[0][k]

                    else:
                        a = [[None] * arg.num_inputs for _ in range(res.num_outputs)]
                        for i in range(res.num_outputs):
                            for j in range(arg.num_inputs):
                                for k in range(arg.num_outputs):
                                    if a[i][j] is None:     # First operation.
                                        if res.num_inputs == 1:
                                            a[i][j] = res.args[0][i] * arg.args[0][k][j]
                                        else:
                                            a[i][j] = res.args[0][i][k] * arg.args[0][k][j]
                                    else:
                                        a[i][j] += res.args[0][i][k] * arg.args[0][k][j]

                    res = TransferFunctionMatrix(a, (res.num_outputs, arg.num_inputs), arg.var)

        return res

    def _eval_rewrite_as_TransferFunction(self, *args, **kwargs):
        """ Series(tfm1, tfm2, Parallel(tfm3, tfm4, ...), ...) not allowed. """
        if not self._is_not_matrix:
            raise ValueError("Only transfer functions or a collection of transfer functions"
                " is allowed in the arguments.")

        return self.doit()

    def _eval_rewrite_as_TransferFunctionMatrix(self, *args, **kwargs):
        """ Series(tf1, tf2, Parallel(tf3, tf4, ...), ...) not allowed. """
        if self._is_not_matrix:
            raise ValueError("Only transfer function matrices or a collection of transfer function"
                " matrices is allowed in the arguments.")

        return self.doit()

    def __add__(self, other):
        if isinstance(other, (TransferFunction, Series, TransferFunctionMatrix)):
            if isinstance(other, Series):
                if self._is_not_matrix != other._is_not_matrix:
                    raise ValueError("Both Series objects should either handle SISO or MIMO"
                        " transfer function.")

            if isinstance(other, TransferFunctionMatrix):
                if self._is_not_matrix:
                    raise ValueError("Series object should handle MIMO transfer function to"
                        " perform this addition.")
            if not self.shape == other.shape:
                raise ShapeError("Shapes of operands are not compatible for addition.")
            if not self.var == other.var:
                raise ValueError("All the transfer functions should use the same complex variable "
                    "of the Laplace transform.")

            return Parallel(self, other)
        elif isinstance(other, Parallel):
            if self._is_not_matrix != other._is_not_matrix:
                raise ValueError("Both Series and Parallel objects should either handle SISO or MIMO"
                    " transfer function.")

            if not self.shape == other.shape:
                raise ShapeError("Shapes of operands are not compatible for addition.")
            if not self.var == other.var:
                raise ValueError("All the transfer functions should use the same complex variable "
                    "of the Laplace transform.")
            arg_list = list(other.args)

            return Parallel(self, *arg_list)
        else:
            raise ValueError("This expression is invalid.")

    __radd__ = __add__

    def __sub__(self, other):
        return self + (-other)

    def __rsub__(self, other):
        return -self + other

    def __mul__(self, other):
        if isinstance(other, (TransferFunction, Parallel, TransferFunctionMatrix)):
            if isinstance(other, Parallel):
                if self._is_not_matrix != other._is_not_matrix:
                    raise ValueError("Both Series and Parallel objects should either handle SISO or MIMO"
                        " transfer function.")
            if isinstance(other, TransferFunctionMatrix):
                if self._is_not_matrix:
                    raise ValueError("Series object should only handle MIMO transfer function to"
                        " perform this multiplication.")

            if not self.num_inputs == other.num_outputs:
                raise ValueError("C = A * B: A has {0} input(s), but B has {1} output(s)."
                    .format(self.num_inputs, other.num_outputs))
            if not self.var == other.var:
                raise ValueError("All the transfer functions should use the same complex variable "
                    "of the Laplace transform.")
            arg_list = list(self.args)

            return Series(*arg_list, other)
        elif isinstance(other, Series):
            if self._is_not_matrix != other._is_not_matrix:
                raise ValueError("Both Series objects should either handle SISO or MIMO"
                    " transfer function.")

            if not self.num_inputs == other.num_outputs:
                raise ValueError("C = A * B: A has {0} input(s), but B has {1} output(s)."
                    .format(self.num_inputs, other.num_outputs))
            if not self.var == other.var:
                raise ValueError("All the transfer functions should use the same complex variable "
                    "of the Laplace transform.")
            self_arg_list = list(self.args)
            other_arg_list = list(other.args)

            return Series(*self_arg_list, *other_arg_list)
        else:
            raise ValueError("This expression is invalid.")

    def __truediv__(self, other):
        if (isinstance(other, Parallel) and len(other.args) == 2
            and isinstance(other.args[0], TransferFunction) and isinstance(other.args[1], Series)):

            if not self.var == other.var:
                raise ValueError("All the transfer functions should use the same complex variable "
                    "of the Laplace transform.")
            self_arg_list = set(list(self.args))
            other_arg_list = set(list(other.args[1].args))
            res = list(self_arg_list ^ other_arg_list)
            if len(res) == 0:
                return Feedback(self, other.args[0])
            elif len(res) == 1:
                return Feedback(self, *res)
            else:
                return Feedback(self, Series(*res))
        else:
            raise ValueError("This expression is invalid.")

    def __neg__(self):
        if self._is_not_matrix:
            return Series(TransferFunction(-1, 1, self.var), self)
        else:
            neg_tfm = [[TransferFunction(-1, 1, self.var)] * self.num_outputs]
            return Series(TransferFunctionMatrix(neg_tfm), self)

    @property
    def is_proper(self):
        """
        Returns True if degree of the numerator polynomial of the resultant transfer
        function is less than or equal to degree of the denominator polynomial of
        the same, else False.

        Examples
        ========

        >>> from sympy.abc import s, p, a, b
        >>> from sympy.physics.control.lti import TransferFunction, Series
        >>> tf1 = TransferFunction(b*s**2 + p**2 - a*p + s, b - p**2, s)
        >>> tf2 = TransferFunction(p**2 - 4*p, p**3 + 3*s + 2, s)
        >>> tf3 = TransferFunction(s, s**2 + s + 1, s)
        >>> S1 = Series(-tf2, tf1)
        >>> S1.is_proper
        False
        >>> S2 = Series(tf1, tf2, tf3)
        >>> S2.is_proper
        True

        """
        return self.doit().is_proper

    @property
    def is_strictly_proper(self):
        """
        Returns True if degree of the numerator polynomial of the resultant transfer
        function is strictly less than degree of the denominator polynomial of
        the same, else False.

        Examples
        ========

        >>> from sympy.abc import s, p, a, b
        >>> from sympy.physics.control.lti import TransferFunction, Series
        >>> tf1 = TransferFunction(a*p**2 + b*s, s - p, s)
        >>> tf2 = TransferFunction(s**3 - 2, s**2 + 5*s + 6, s)
        >>> tf3 = TransferFunction(1, s**2 + s + 1, s)
        >>> S1 = Series(tf1, tf2)
        >>> S1.is_strictly_proper
        False
        >>> S2 = Series(tf1, tf2, tf3)
        >>> S2.is_strictly_proper
        True

        """
        return self.doit().is_strictly_proper

    @property
    def is_biproper(self):
        r"""
        Returns True if degree of the numerator polynomial of the resultant transfer
        function is equal to degree of the denominator polynomial of
        the same, else False.

        Examples
        ========

        >>> from sympy.abc import s, p, a, b
        >>> from sympy.physics.control.lti import TransferFunction, Series
        >>> tf1 = TransferFunction(a*p**2 + b*s, s - p, s)
        >>> tf2 = TransferFunction(p, s**2, s)
        >>> tf3 = TransferFunction(s**2, 1, s)
        >>> S1 = Series(tf1, -tf2)
        >>> S1.is_biproper
        False
        >>> S2 = Series(tf2, tf3)
        >>> S2.is_biproper
        True

        """
        return self.doit().is_biproper
        
    @property
    def is_SISO(self):
        if self._is_not_Matrix:
            return True
        else:
            return False

class Parallel(Basic):
    """
    A class for representing addition of transfer functions or transfer functions
    in a parallel configuration.

    Examples
    ========

    >>> from sympy.abc import s, p, a, b
    >>> from sympy.physics.control.lti import TransferFunction, Parallel, Series
    >>> tf1 = TransferFunction(a*p**2 + b*s, s - p, s)
    >>> tf2 = TransferFunction(s**3 - 2, s**4 + 5*s + 6, s)
    >>> tf3 = TransferFunction(p**2, p + s, s)
    >>> P1 = Parallel(tf1, tf2)
    >>> P1
    Parallel(TransferFunction(a*p**2 + b*s, -p + s, s), TransferFunction(s**3 - 2, s**4 + 5*s + 6, s))
    >>> P1.var
    s
    >>> P2 = Parallel(tf2, Series(tf3, -tf1))
    >>> P2
    Parallel(TransferFunction(s**3 - 2, s**4 + 5*s + 6, s), Series(TransferFunction(p**2, p + s, s), TransferFunction(-a*p**2 - b*s, -p + s, s)))
    >>> P2.var
    s
    >>> P3 = Parallel(Series(tf1, tf2), Series(tf2, tf3))
    >>> P3
    Parallel(Series(TransferFunction(a*p**2 + b*s, -p + s, s), TransferFunction(s**3 - 2, s**4 + 5*s + 6, s)), Series(TransferFunction(s**3 - 2, s**4 + 5*s + 6, s), TransferFunction(p**2, p + s, s)))
    >>> P3.var
    s

    You can get the resultant transfer function by using ``.doit()`` method:

    >>> Parallel(tf1, tf2, -tf3).doit()
    TransferFunction(-p**2*(-p + s)*(s**4 + 5*s + 6) + (p + s)*((-p + s)*(s**3 - 2) + (a*p**2 + b*s)*(s**4 + 5*s + 6)), (-p + s)*(p + s)*(s**4 + 5*s + 6), s)
    >>> Parallel(tf2, Series(tf1, -tf3)).doit()
    TransferFunction(-p**2*(a*p**2 + b*s)*(s**4 + 5*s + 6) + (-p + s)*(p + s)*(s**3 - 2), (-p + s)*(p + s)*(s**4 + 5*s + 6), s)

    Notes
    =====

    All the transfer functions should use the same complex variable
    ``var`` of the Laplace transform.

    See Also
    ========

    Series, TransferFunction, Feedback

    """
    def __new__(cls, *args, evaluate=False):
        if len(args) == 0:
            raise ValueError("Needs at least 1 argument.")
        if not all(isinstance(arg, (TransferFunction, TransferFunctionMatrix, Series, Parallel))
            for arg in args):
            raise TypeError("Unsupported type of argument(s) for Parallel.")

        obj = super(Parallel, cls).__new__(cls, *args)
        obj._is_not_matrix = all(isinstance(arg.doit(), TransferFunction) for arg in args)
        if not obj._is_not_matrix:
            obj._num_inputs, obj._num_outputs = args[0].num_inputs, args[0].num_outputs
            # All MIMO --> assert matching shapes..
            if not all(arg.shape == args[0].shape for arg in args):
                raise ShapeError("Dimensions of all TransferFunctionMatrix"
                    " objects should match.")
        else:
            obj._num_inputs, obj._num_outputs = 1, 1

        tf = "transfer functions" if obj._is_not_matrix else "TransferFunctionMatrix objects"
        obj._var = args[0].var
        if not all(arg.var == obj._var for arg in args):
            raise ValueError("All {0} should use the same complex"
                " variable of the Laplace transform.".format(tf))
        return obj.doit() if evaluate else obj

    @property
    def var(self):
        """
        Returns the complex variable used by all the transfer functions.

        Examples
        ========

        >>> from sympy.abc import p
        >>> from sympy.physics.control.lti import TransferFunction, Parallel, Series
        >>> G1 = TransferFunction(p**2 + 2*p + 4, p - 6, p)
        >>> G2 = TransferFunction(p, 4 - p, p)
        >>> G3 = TransferFunction(0, p**4 - 1, p)
        >>> Parallel(G1, G2).var
        p
        >>> Parallel(-G3, Series(G1, G2)).var
        p

        """
        return self._var

    @property
    def num_inputs(self):
        return self._num_inputs

    @property
    def num_outputs(self):
        return self._num_outputs

    @property
    def shape(self):
        return self._num_outputs, self._num_inputs

    def doit(self, **kwargs):
        """
        Returns the resultant transfer function obtained after evaluating
        the transfer functions in parallel configuration.

        Examples
        ========

        >>> from sympy.abc import s, p, a, b
        >>> from sympy.physics.control.lti import TransferFunction, Parallel
        >>> tf1 = TransferFunction(a*p**2 + b*s, s - p, s)
        >>> tf2 = TransferFunction(s**3 - 2, s**4 + 5*s + 6, s)
        >>> Parallel(tf2, tf1).doit()
        TransferFunction((-p + s)*(s**3 - 2) + (a*p**2 + b*s)*(s**4 + 5*s + 6), (-p + s)*(s**4 + 5*s + 6), s)
        >>> Parallel(-tf1, -tf2).doit()
        TransferFunction((2 - s**3)*(-p + s) + (-a*p**2 - b*s)*(s**4 + 5*s + 6), (-p + s)*(s**4 + 5*s + 6), s)

        """
        res = None
        for arg in self.args:
            arg = arg.doit()
            if res is None:
                res = arg
            else:
                if self._is_not_matrix:
                    if res.den == arg.den:
                        num_, den_ = res.num + arg.num, res.den
                    else:
                        num_, den_ = res.num * arg.den + res.den * arg.num, res.den * arg.den
                    res = TransferFunction(num_, den_, self.var)
                else:
                    if self.num_inputs == 1:
                        a = [None] * self.num_outputs
                        for x in range(self.num_outputs):
                            a[x] = res.args[0][x] + arg.args[0][x]
                    else:
                        a = [[None] * self.num_inputs for _ in range(self.num_outputs)]
                        for row in range(self.num_outputs):
                            for col in range(self.num_inputs):
                                a[row][col] = res.args[0][row][col] + arg.args[0][row][col]
                    res = TransferFunctionMatrix(a, self.shape, self.var)
        return res

    def _eval_rewrite_as_TransferFunction(self, *args, **kwargs):
        """ Parallel(tfm1, tfm2, Series(tfm3, tfm4, ...), ...) not allowed. """
        if not self._is_not_matrix:
            raise ValueError("Only transfer functions or a collection of transfer functions"
                " is allowed in the arguments.")

        return self.doit()

    def _eval_rewrite_as_TransferFunctionMatrix(self, *args, **kwargs):
        """ Parallel(tf1, tf2, Series(tf3, tf4, ...), ...) not allowed. """
        if self._is_not_matrix:
            raise ValueError("Only transfer function matrices or a collection of transfer function"
                " matrices is allowed in the arguments.")

        return self.doit()

    def __add__(self, other):
        if isinstance(other, (TransferFunction, Series, TransferFunctionMatrix)):
            if isinstance(other, TransferFunctionMatrix):
                if self._is_not_matrix:
                    raise ValueError("Only transfer function matrices are allowed in the "
                        "parallel configuration.")
            if isinstance(other, Series):
                if self._is_not_matrix != other._is_not_matrix:
                    raise ValueError("Both Series and Parallel objects should either handle SISO or MIMO"
                        " transfer function.")
            if not self.shape == other.shape:
                raise ShapeError("Shapes of operands are not compatible for addition.")
            if not self.var == other.var:
                raise ValueError("All the transfer functions should use the same complex variable "
                    "of the Laplace transform.")

            arg_list = list(self.args)
            arg_list.append(other)

            return Parallel(*arg_list)
        elif isinstance(other, Parallel):
            if self._is_not_matrix != other._is_not_matrix:
                raise ValueError("Both Parallel objects should either handle SISO or MIMO"
                    " transfer function.")
            if not self.shape == other.shape:
                raise ShapeError("Shapes of operands are not compatible for addition.")
            if not self.var == other.var:
                raise ValueError("All the transfer functions should use the same complex variable "
                    "of the Laplace transform.")

            self_arg_list = list(self.args)
            other_arg_list = list(other.args)
            for elem in other_arg_list:
                self_arg_list.append(elem)

            return Parallel(*self_arg_list)
        else:
            raise ValueError("This expression is invalid.")

    def __sub__(self, other):
        return self + (-other)

    def __mul__(self, other):
        if isinstance(other, (TransferFunction, Parallel, TransferFunctionMatrix)):
            if isinstance(other, Parallel):
                if self._is_not_matrix != other._is_not_matrix:
                    raise ValueError("Both Parallel objects should either handle SISO or MIMO"
                        " transfer function.")
            if isinstance(other, TransferFunctionMatrix):
                if self._is_not_matrix:
                    raise ValueError("The Parallel object should only handle MIMO transfer function to"
                        " perform this multiplication.")
            if not self.num_inputs == other.num_outputs:
                raise ValueError("C = A * B: A has {0} input(s), but B has {1} output(s)."
                    .format(self.num_inputs, other.num_outputs))
            if not self.var == other.var:
                raise ValueError("All the transfer functions should use the same complex variable "
                    "of the Laplace transform.")

            return Series(self, other)
        elif isinstance(other, Series):
            if self._is_not_matrix != other._is_not_matrix:
                raise ValueError("Both Series and Parallel objects should either handle SISO or MIMO"
                    " transfer function.")
            if not self.num_inputs == other.num_outputs:
                raise ValueError("C = A * B: A has {0} input(s), but B has {1} output(s)."
                    .format(self.num_inputs, other.num_outputs))
            if not self.var == other.var:
                raise ValueError("All the transfer functions should use the same complex variable "
                    "of the Laplace transform.")

            arg_list = list(other.args)
            return Series(self, *arg_list)
        else:
            raise ValueError("This expression is invalid.")

    __rmul__ = __mul__

    def __neg__(self):
        if self._is_not_matrix:
            return Series(TransferFunction(-1, 1, self.var), self)
        else:
            neg_args = [-arg for arg in self.args]
            return Parallel(*neg_args)

    @property
    def is_proper(self):
        """
        Returns True if degree of the numerator polynomial of the resultant transfer
        function is less than or equal to degree of the denominator polynomial of
        the same, else False.

        Examples
        ========

        >>> from sympy.abc import s, p, a, b
        >>> from sympy.physics.control.lti import TransferFunction, Parallel
        >>> tf1 = TransferFunction(b*s**2 + p**2 - a*p + s, b - p**2, s)
        >>> tf2 = TransferFunction(p**2 - 4*p, p**3 + 3*s + 2, s)
        >>> tf3 = TransferFunction(s, s**2 + s + 1, s)
        >>> P1 = Parallel(-tf2, tf1)
        >>> P1.is_proper
        False
        >>> P2 = Parallel(tf2, tf3)
        >>> P2.is_proper
        True

        """
        return self.doit().is_proper

    @property
    def is_strictly_proper(self):
        """
        Returns True if degree of the numerator polynomial of the resultant transfer
        function is strictly less than degree of the denominator polynomial of
        the same, else False.

        Examples
        ========

        >>> from sympy.abc import s, p, a, b
        >>> from sympy.physics.control.lti import TransferFunction, Parallel
        >>> tf1 = TransferFunction(a*p**2 + b*s, s - p, s)
        >>> tf2 = TransferFunction(s**3 - 2, s**4 + 5*s + 6, s)
        >>> tf3 = TransferFunction(s, s**2 + s + 1, s)
        >>> P1 = Parallel(tf1, tf2)
        >>> P1.is_strictly_proper
        False
        >>> P2 = Parallel(tf2, tf3)
        >>> P2.is_strictly_proper
        True

        """
        return self.doit().is_strictly_proper

    @property
    def is_biproper(self):
        """
        Returns True if degree of the numerator polynomial of the resultant transfer
        function is equal to degree of the denominator polynomial of
        the same, else False.

        Examples
        ========

        >>> from sympy.abc import s, p, a, b
        >>> from sympy.physics.control.lti import TransferFunction, Parallel
        >>> tf1 = TransferFunction(a*p**2 + b*s, s - p, s)
        >>> tf2 = TransferFunction(p**2, p + s, s)
        >>> tf3 = TransferFunction(s, s**2 + s + 1, s)
        >>> P1 = Parallel(tf1, -tf2)
        >>> P1.is_biproper
        True
        >>> P2 = Parallel(tf2, tf3)
        >>> P2.is_biproper
        False

        """
        return self.doit().is_biproper


class Feedback(Basic):
    """
    A class for representing negative feedback interconnection between two
    input/output systems. The first argument, ``num``, is called as the
    primary plant or the numerator, and the second argument, ``den``, is
    called as the feedback plant (which is often a feedback controller) or
    the denominator. Both ``num`` and ``den`` can either be ``Series`` or
    ``TransferFunction`` objects.

    Parameters
    ==========

    num : Series, TransferFunction
        The primary plant.
    den : Series, TransferFunction
        The feedback plant (often a feedback controller).

    Raises
    ======

    ValueError
        When ``num`` is equal to ``den`` or when they are not using the
        same complex variable of the Laplace transform.
    TypeError
        When either ``num`` or ``den`` is not a ``Series`` or a
        ``TransferFunction`` object.

    Examples
    ========

    >>> from sympy.abc import s
    >>> from sympy.physics.control.lti import TransferFunction, Feedback
    >>> plant = TransferFunction(3*s**2 + 7*s - 3, s**2 - 4*s + 2, s)
    >>> controller = TransferFunction(5*s - 10, s + 7, s)
    >>> F1 = Feedback(plant, controller)
    >>> F1
    Feedback(TransferFunction(3*s**2 + 7*s - 3, s**2 - 4*s + 2, s), TransferFunction(5*s - 10, s + 7, s))
    >>> F1.var
    s
    >>> F1.args
    (TransferFunction(3*s**2 + 7*s - 3, s**2 - 4*s + 2, s), TransferFunction(5*s - 10, s + 7, s))

    You can get the primary and the feedback plant using ``.num`` and ``.den`` respectively.

    >>> F1.num
    TransferFunction(3*s**2 + 7*s - 3, s**2 - 4*s + 2, s)
    >>> F1.den
    TransferFunction(5*s - 10, s + 7, s)

    You can get the resultant closed loop transfer function obtained by negative feedback
    interconnection using ``.doit()`` method.

    >>> F1.doit()
    TransferFunction((s + 7)*(s**2 - 4*s + 2)*(3*s**2 + 7*s - 3), ((s + 7)*(s**2 - 4*s + 2) + (5*s - 10)*(3*s**2 + 7*s - 3))*(s**2 - 4*s + 2), s)
    >>> G = TransferFunction(2*s**2 + 5*s + 1, s**2 + 2*s + 3, s)
    >>> C = TransferFunction(5*s + 10, s + 10, s)
    >>> F2 = Feedback(G*C, TransferFunction(1, 1, s))
    >>> F2.doit()
    TransferFunction((s + 10)*(5*s + 10)*(s**2 + 2*s + 3)*(2*s**2 + 5*s + 1), (s + 10)*((s + 10)*(s**2 + 2*s + 3) + (5*s + 10)*(2*s**2 + 5*s + 1))*(s**2 + 2*s + 3), s)

    To negate a ``Feedback`` object, the ``-`` operator can be prepended:

    >>> -F1
    Feedback(TransferFunction(-3*s**2 - 7*s + 3, s**2 - 4*s + 2, s), TransferFunction(5*s - 10, s + 7, s))
    >>> -F2
    Feedback(Series(TransferFunction(-1, 1, s), Series(TransferFunction(2*s**2 + 5*s + 1, s**2 + 2*s + 3, s), TransferFunction(5*s + 10, s + 10, s))), TransferFunction(1, 1, s))

    See Also
    ========

    TransferFunction, Series, Parallel

    """
    def __new__(cls, num, den):
        if not (isinstance(num, (TransferFunction, Series))
            and isinstance(den, (TransferFunction, Series))):
            raise TypeError("Unsupported type for numerator or denominator of Feedback.")

        if num == den:
            raise ValueError("The numerator cannot be equal to the denominator.")
        if not num.var == den.var:
            raise ValueError("Both numerator and denominator should be using the"
                " same complex variable.")
        obj = super(Feedback, cls).__new__(cls, num, den)
        obj._num = num
        obj._den = den
        obj._var = num.var

        return obj

    @property
    def num(self):
        """
        Returns the primary plant of the negative feedback closed loop.

        Examples
        ========

        >>> from sympy.abc import s, p
        >>> from sympy.physics.control.lti import TransferFunction, Feedback
        >>> plant = TransferFunction(3*s**2 + 7*s - 3, s**2 - 4*s + 2, s)
        >>> controller = TransferFunction(5*s - 10, s + 7, s)
        >>> F1 = Feedback(plant, controller)
        >>> F1.num
        TransferFunction(3*s**2 + 7*s - 3, s**2 - 4*s + 2, s)
        >>> G = TransferFunction(2*s**2 + 5*s + 1, p**2 + 2*p + 3, p)
        >>> C = TransferFunction(5*p + 10, p + 10, p)
        >>> P = TransferFunction(1 - s, p + 2, p)
        >>> F2 = Feedback(TransferFunction(1, 1, p), G*C*P)
        >>> F2.num
        TransferFunction(1, 1, p)

        """
        return self._num

    @property
    def den(self):
        """
        Returns the feedback plant (often a feedback controller) of the
        negative feedback closed loop.

        Examples
        ========

        >>> from sympy.abc import s, p
        >>> from sympy.physics.control.lti import TransferFunction, Feedback
        >>> plant = TransferFunction(3*s**2 + 7*s - 3, s**2 - 4*s + 2, s)
        >>> controller = TransferFunction(5*s - 10, s + 7, s)
        >>> F1 = Feedback(plant, controller)
        >>> F1.den
        TransferFunction(5*s - 10, s + 7, s)
        >>> G = TransferFunction(2*s**2 + 5*s + 1, p**2 + 2*p + 3, p)
        >>> C = TransferFunction(5*p + 10, p + 10, p)
        >>> P = TransferFunction(1 - s, p + 2, p)
        >>> F2 = Feedback(TransferFunction(1, 1, p), G*C*P)
        >>> F2.den
        Series(TransferFunction(2*s**2 + 5*s + 1, p**2 + 2*p + 3, p), TransferFunction(5*p + 10, p + 10, p), TransferFunction(1 - s, p + 2, p))

        """
        return self._den

    @property
    def var(self):
        """
        Returns the complex variable of the Laplace transform used by all
        the transfer functions involved in the negative feedback closed loop.

        Examples
        ========

        >>> from sympy.abc import s, p
        >>> from sympy.physics.control.lti import TransferFunction, Feedback
        >>> plant = TransferFunction(3*s**2 + 7*s - 3, s**2 - 4*s + 2, s)
        >>> controller = TransferFunction(5*s - 10, s + 7, s)
        >>> F1 = Feedback(plant, controller)
        >>> F1.var
        s
        >>> G = TransferFunction(2*s**2 + 5*s + 1, p**2 + 2*p + 3, p)
        >>> C = TransferFunction(5*p + 10, p + 10, p)
        >>> P = TransferFunction(1 - s, p + 2, p)
        >>> F2 = Feedback(TransferFunction(1, 1, p), G*C*P)
        >>> F2.var
        p

        """
        return self._var

    def doit(self, **kwargs):
        """
        Returns the resultant closed loop transfer function obtained by the
        negative feedback interconnection.

        Examples
        ========

        >>> from sympy.abc import s
        >>> from sympy.physics.control.lti import TransferFunction, Feedback
        >>> plant = TransferFunction(3*s**2 + 7*s - 3, s**2 - 4*s + 2, s)
        >>> controller = TransferFunction(5*s - 10, s + 7, s)
        >>> F1 = Feedback(plant, controller)
        >>> F1.doit()
        TransferFunction((s + 7)*(s**2 - 4*s + 2)*(3*s**2 + 7*s - 3), ((s + 7)*(s**2 - 4*s + 2) + (5*s - 10)*(3*s**2 + 7*s - 3))*(s**2 - 4*s + 2), s)
        >>> G = TransferFunction(2*s**2 + 5*s + 1, s**2 + 2*s + 3, s)
        >>> F2 = Feedback(G, TransferFunction(1, 1, s))
        >>> F2.doit()
        TransferFunction((s**2 + 2*s + 3)*(2*s**2 + 5*s + 1), (s**2 + 2*s + 3)*(3*s**2 + 7*s + 4), s)

        """
        arg_list = list(self.num.args) if isinstance(self.num, Series) else [self.num]
        # F_n and F_d are resultant TFs of num and den of Feedback.
        F_n, tf = self.num.doit(), TransferFunction(1, 1, self.num.var)
        F_d = Parallel(tf, Series(self.den, *arg_list)).doit()

        return TransferFunction(F_n.num*F_d.den, F_n.den*F_d.num, F_n.var)

    def _eval_rewrite_as_TransferFunction(self, num, den, **kwargs):
        return self.doit()

    def __neg__(self):
        return Feedback(-self.num, self.den)


class TransferFunctionMatrix(Basic):
    """
    A class for representing the MIMO (multiple-input and multiple-output)
    generalization of the SISO (single-input and single-output) transfer function.

    It is a matrix of transfer functions (``TransferFunction`` objects).
    The arguments are ``arg``, ``shape``, and ``var``, where only the first one
    is the compulsory argument. ``arg`` can be a list/tuple, list of lists or even a
    tuple of tuples, which holds the transfer functions. ``shape`` is a tuple which is
    equal to ``(# of outputs of the system, # of inputs of the system)``, and ``var``
    is a complex variable (which has to be a ``Symbol``) of the Laplace transform
    used by all the transfer functions in the matrix.

    Examples
    ========

    >>> from sympy.abc import s, p, a
    >>> from sympy.physics.control.lti import TransferFunction, TransferFunctionMatrix
    >>> tf1 = TransferFunction(s + a, s**2 + s + 1, s)
    >>> tf2 = TransferFunction(p**4 - 3*p + 2, s + p, s)
    >>> tf3 = TransferFunction(3, s + 2, s)
    >>> tf4 = TransferFunction(s - p, p**2 + 8, p)
    >>> tf5 = TransferFunction(-a + p, 9*s - 9, s)
    >>> TFM1 = TransferFunctionMatrix([tf1, tf2, tf3], (3, 1), s)
    >>> TFM1
    TransferFunctionMatrix([TransferFunction(a + s, s**2 + s + 1, s), TransferFunction(p**4 - 3*p + 2, p + s, s), TransferFunction(3, s + 2, s)])
    >>> TFM1.var
    s
    >>> TFM1.num_inputs
    1
    >>> TFM1.num_outputs
    3
    >>> TFM1.shape
    (3, 1)
    >>> TFM1.args
    ([TransferFunction(a + s, s**2 + s + 1, s), TransferFunction(p**4 - 3*p + 2, p + s, s), TransferFunction(3, s + 2, s)],)

    >>> # also valid when ``shape`` and ``var`` are not specified.
    >>> TFM2 = TransferFunctionMatrix((tf1, tf2, tf3))
    >>> TFM2
    TransferFunctionMatrix((TransferFunction(a + s, s**2 + s + 1, s), TransferFunction(p**4 - 3*p + 2, p + s, s), TransferFunction(3, s + 2, s)))
    >>> TFM2.var
    s
    >>> TFM2.shape
    (3, 1)
    >>> TFM2.num_inputs
    1
    >>> TFM2.num_outputs
    3
    >>> TFM2.args
    ((TransferFunction(a + s, s**2 + s + 1, s), TransferFunction(p**4 - 3*p + 2, p + s, s), TransferFunction(3, s + 2, s)),)

    Any complex variable can be used for ``var``.

    >>> TFM3 = TransferFunctionMatrix([tf4], (1, 1), p)   # [[tf4]] and (tf4,) are also valid as the first arguments.
    >>> TFM3
    TransferFunctionMatrix([TransferFunction(-p + s, p**2 + 8, p)])
    >>> TFM3.var
    p
    >>> TFM3.shape
    (1, 1)

    >>> TFM4 = TransferFunctionMatrix([[tf1, -tf3], [tf2, -tf1], [tf3, -tf2]], (3, 2), s)
    >>> TFM4
    TransferFunctionMatrix([[TransferFunction(a + s, s**2 + s + 1, s), TransferFunction(-3, s + 2, s)], [TransferFunction(p**4 - 3*p + 2, p + s, s), TransferFunction(-a - s, s**2 + s + 1, s)], [TransferFunction(3, s + 2, s), TransferFunction(-p**4 + 3*p - 2, p + s, s)]])
    >>> TFM4.var
    s
    >>> TFM4.shape
    (3, 2)
    >>> TFM4.num_outputs
    3
    >>> TFM4.num_inputs
    2
    >>> TFM4.args
    ([[TransferFunction(a + s, s**2 + s + 1, s), TransferFunction(-3, s + 2, s)], [TransferFunction(p**4 - 3*p + 2, p + s, s), TransferFunction(-a - s, s**2 + s + 1, s)], [TransferFunction(3, s + 2, s), TransferFunction(-p**4 + 3*p - 2, p + s, s)]],)

    To negate a transfer function matrix the ``-`` operator can be prepended:

    >>> TFM5 = TransferFunctionMatrix((tf2, -tf1, tf3))
    >>> -TFM5
    TransferFunctionMatrix([TransferFunction(-p**4 + 3*p - 2, p + s, s), TransferFunction(a + s, s**2 + s + 1, s), TransferFunction(-3, s + 2, s)])
    >>> TFM6 = TransferFunctionMatrix([[tf1, tf2], [tf3, -tf1]], (2, 2), s)
    >>> -TFM6
    TransferFunctionMatrix([[TransferFunction(-a - s, s**2 + s + 1, s), TransferFunction(-p**4 + 3*p - 2, p + s, s)], [TransferFunction(-3, s + 2, s), TransferFunction(a + s, s**2 + s + 1, s)]])

    Addition, subtraction, and multiplication of transfer function matrices can form
    unevaluated ``Series`` or ``Parallel`` objects.
    For addition and subtraction:
        All the transfer function matrices must have the same shape.
    For multiplication (C = A * B):
        The number of inputs of the first transfer function matrix (A) must be equal to the
        number of outputs of the second transfer function matrix (B).
    Also, use pretty-printing (``pprint``) to analyse better.

    >>> TFM7 = TransferFunctionMatrix([[tf5, -tf1, tf3], [-tf2, -tf5, -tf3]], (2, 3), s)
    >>> TFM8 = TransferFunctionMatrix([tf3, tf2, -tf1], (3, 1), s)
    >>> TFM9 = TransferFunctionMatrix([-tf3], (1, 1), s)
    >>> TFM10 = TransferFunctionMatrix((tf1, tf2, tf5))
    >>> TFM11 = TransferFunctionMatrix([tf5, -tf1], (2, 1), s)
    >>> TFM8 + TFM10
    Parallel(TransferFunctionMatrix([TransferFunction(3, s + 2, s), TransferFunction(p**4 - 3*p + 2, p + s, s), TransferFunction(-a - s, s**2 + s + 1, s)]), TransferFunctionMatrix((TransferFunction(a + s, s**2 + s + 1, s), TransferFunction(p**4 - 3*p + 2, p + s, s), TransferFunction(-a + p, 9*s - 9, s))))
    >>> -TFM10 - TFM8
    Parallel(TransferFunctionMatrix([TransferFunction(-a - s, s**2 + s + 1, s), TransferFunction(-p**4 + 3*p - 2, p + s, s), TransferFunction(a - p, 9*s - 9, s)]), TransferFunctionMatrix([TransferFunction(-3, s + 2, s), TransferFunction(-p**4 + 3*p - 2, p + s, s), TransferFunction(a + s, s**2 + s + 1, s)]))
    >>> TFM7 * TFM8
    Series(TransferFunctionMatrix([[TransferFunction(-a + p, 9*s - 9, s), TransferFunction(-a - s, s**2 + s + 1, s), TransferFunction(3, s + 2, s)], [TransferFunction(-p**4 + 3*p - 2, p + s, s), TransferFunction(a - p, 9*s - 9, s), TransferFunction(-3, s + 2, s)]]), TransferFunctionMatrix([TransferFunction(3, s + 2, s), TransferFunction(p**4 - 3*p + 2, p + s, s), TransferFunction(-a - s, s**2 + s + 1, s)]))
    >>> TFM7 * TFM8 * TFM9
    Series(TransferFunctionMatrix([[TransferFunction(-a + p, 9*s - 9, s), TransferFunction(-a - s, s**2 + s + 1, s), TransferFunction(3, s + 2, s)], [TransferFunction(-p**4 + 3*p - 2, p + s, s), TransferFunction(a - p, 9*s - 9, s), TransferFunction(-3, s + 2, s)]]), TransferFunctionMatrix([TransferFunction(3, s + 2, s), TransferFunction(p**4 - 3*p + 2, p + s, s), TransferFunction(-a - s, s**2 + s + 1, s)]), TransferFunctionMatrix([TransferFunction(-3, s + 2, s)]))
    >>> TFM10 + TFM8*TFM9
    Parallel(TransferFunctionMatrix((TransferFunction(a + s, s**2 + s + 1, s), TransferFunction(p**4 - 3*p + 2, p + s, s), TransferFunction(-a + p, 9*s - 9, s))), Series(TransferFunctionMatrix([TransferFunction(3, s + 2, s), TransferFunction(p**4 - 3*p + 2, p + s, s), TransferFunction(-a - s, s**2 + s + 1, s)]), TransferFunctionMatrix([TransferFunction(-3, s + 2, s)])))

    These unevaluated ``Series`` or ``Parallel`` objects can convert into the
    resultant transfer function matrix using ``.doit()`` method or by
    ``.rewrite(TransferFunctionMatrix)``.

    >>> (-TFM8 + TFM10 + TFM8*TFM9).doit()
    TransferFunctionMatrix([Parallel(TransferFunction(-3, s + 2, s), TransferFunction(a + s, s**2 + s + 1, s), Series(TransferFunction(3, s + 2, s), TransferFunction(-3, s + 2, s))), Parallel(TransferFunction(-p**4 + 3*p - 2, p + s, s), TransferFunction(p**4 - 3*p + 2, p + s, s), Series(TransferFunction(p**4 - 3*p + 2, p + s, s), TransferFunction(-3, s + 2, s))), Parallel(TransferFunction(a + s, s**2 + s + 1, s), TransferFunction(-a + p, 9*s - 9, s), Series(TransferFunction(-a - s, s**2 + s + 1, s), TransferFunction(-3, s + 2, s)))])
    >>> (-TFM7 * -TFM8 * -TFM9).rewrite(TransferFunctionMatrix)
    TransferFunctionMatrix([Series(Parallel(Series(TransferFunction(a - p, 9*s - 9, s), TransferFunction(-3, s + 2, s)), Series(TransferFunction(a + s, s**2 + s + 1, s), TransferFunction(-p**4 + 3*p - 2, p + s, s)), Series(TransferFunction(-3, s + 2, s), TransferFunction(a + s, s**2 + s + 1, s))), TransferFunction(3, s + 2, s)), Series(Parallel(Series(TransferFunction(p**4 - 3*p + 2, p + s, s), TransferFunction(-3, s + 2, s)), Series(TransferFunction(-a + p, 9*s - 9, s), TransferFunction(-p**4 + 3*p - 2, p + s, s)), Series(TransferFunction(3, s + 2, s), TransferFunction(a + s, s**2 + s + 1, s))), TransferFunction(3, s + 2, s))])

    And ``.doit().doit()`` on this resultant transfer function matrix will expand the internal ``Series``
    or ``Parallel`` objects.

    >>> (-TFM8 + TFM10 + TFM8*TFM9).doit().doit()
    TransferFunctionMatrix([TransferFunction((s + 2)**2*(-3*s**2 - 3*s + (a + s)*(s + 2) - 3) - 9*(s + 2)*(s**2 + s + 1), (s + 2)**3*(s**2 + s + 1), s), TransferFunction((p + s)*(-3*p**4 + 9*p - 6), (p + s)**2*(s + 2), s), TransferFunction((3*a + 3*s)*(9*s - 9)*(s**2 + s + 1) + (s + 2)*((-a + p)*(s**2 + s + 1) + (a + s)*(9*s - 9))*(s**2 + s + 1), (s + 2)*(9*s - 9)*(s**2 + s + 1)**2, s)])

    See Also
    ========

    TransferFunction, Series, Parallel, Feedback

    """
    def __new__(cls, arg, shape=None, var=None):
        if not (isinstance(arg, (list, tuple)) and
            (all(isinstance(i, (list, tuple)) for i in arg) or
            all(isinstance(i, (TransferFunction, Parallel, Series)) for i in arg))):
            raise TypeError("Unsupported type for argument of TransferFunctionMatrix.")

        if shape and var:
            if not isinstance(shape, tuple):
                raise TypeError("Shape must be a tuple, not {}.".format(type(shape)))
            if not isinstance(var, Symbol):
                raise TypeError("Var must be a Symbol, not {}.".format(type(var)))

        obj = super(TransferFunctionMatrix, cls).__new__(cls, arg)
        if all(isinstance(i, (TransferFunction, Series, Parallel)) for i in arg):
            # TFM with 1st argument of the type - [tf1, tf2, tf3, ...] or (tf1, tf2, ...)
            if shape and var:
                if not all(elem.var == var for elem in arg):
                    raise ValueError("All transfer functions should use the same complex"
                        " variable (var) of the Laplace transform.")
                if not (shape[0] == len(arg) and shape[1] == 1):
                    raise ValueError("The provided Shape does not match the shape of the input."
                        " Shape must be equal to ({0}, {1}).".format(len(arg), 1))
                obj._num_outputs, obj._num_inputs, obj._var = shape[0], shape[1], var
            else:
                obj._var = arg[0].var
                obj._num_outputs, obj._num_inputs = (len(arg), 1)
                if not all(elem.var == obj._var for elem in arg):
                    raise ValueError("All transfer functions should use the same complex"
                        " variable of the Laplace transform.")
        else:
            # TFM with 1st argument of the type - [[tf1, tf2, ...], [tf3, tf4, ...], ...]
            # or ((tf1, tf2, ...), (tf3, tf4, ...), ...)
            if not all(isinstance(arg[row][col], (TransferFunction, Series, Parallel))
                for col in range(len(arg[0])) for row in range(len(arg))):
                raise TypeError("All the lists/tuples in the first argument of TransferFunctionMatrix"
                    " only support transfer functions, and Series/Parallel objects in them.")
            if not all(len(l) == len(arg[0]) for l in arg):
                raise ValueError("Length of all the lists/tuples in the argument of"
                    " TransferFunctionMatrix should be equal.")
            if shape and var:
                if not (shape[0] == len(arg) and shape[1] == len(arg[0])):
                    raise ValueError("The provided Shape does not match the shape of the input."
                        " Shape must be equal to ({0}, {1}).".format(len(arg), len(arg[0])))
                if not all(arg[row][col].var == var
                    for col in range(shape[1]) for row in range(shape[0])):
                    raise ValueError("All transfer functions should use the same complex"
                        " variable (var) of the Laplace transform.")
                obj._num_outputs, obj._num_inputs, obj._var = shape[0], shape[1], var
            else:
                obj._var, obj._num_outputs, obj._num_inputs = arg[0][0].var, len(arg), len(arg[0])
                if not all(arg[row][col].var == obj._var
                    for col in range(len(arg[0])) for row in range(len(arg))):
                    raise ValueError("All transfer functions should use the same complex"
                        " variable of the Laplace transform.")
        return obj

    @property
    def var(self):
        """
        Returns the complex variable used by all the transfer functions or
        ``Series``/``Parallel`` objects in a transfer function matrix.

        If explicitly provided as the third argument of ``TransferFunctionMatrix``, then returns
        the same, else, ``TransferFunctionMatrix`` automatically looks up the ``var`` used by
        transfer functions inside the list/tuple provided as the first argument and returns that.

        Examples
        ========

        >>> from sympy.abc import p, s
        >>> from sympy.physics.control.lti import TransferFunction, TransferFunctionMatrix, Series, Parallel
        >>> G1 = TransferFunction(p**2 + 2*p + 4, p - 6, p)
        >>> G2 = TransferFunction(p, 4 - p, p)
        >>> G3 = TransferFunction(0, p**4 - 1, p)
        >>> G4 = TransferFunction(s + 1, s**2 + s + 1, s)
        >>> S1 = Series(G1, G2)
        >>> S2 = Series(-G3, Parallel(G2, -G1))
        >>> tfm1 = TransferFunctionMatrix([G1, G2, G3], (3, 1), p)
        >>> tfm1.var
        p
        >>> tfm2 = TransferFunctionMatrix(((-S1, -S2), (S1, S2)), (2, 2), p)
        >>> tfm2.var
        p
        >>> tfm3 = TransferFunctionMatrix([[G4]], (1, 1), s)
        >>> tfm3.var
        s

        """
        return self._var

    @property
    def num_inputs(self):
        """
        Returns the number of inputs of the system.

        Examples
        ========

        >>> from sympy.abc import s, p
        >>> from sympy.physics.control.lti import TransferFunction, TransferFunctionMatrix
        >>> G1 = TransferFunction(s + 3, s**2 - 3, s)
        >>> G2 = TransferFunction(4, s**2, s)
        >>> G3 = TransferFunction(p**2 + s**2, p - 3, s)
        >>> tfm1 = TransferFunctionMatrix((G1, G2), (2, 1), s)
        >>> tfm1.num_inputs
        1
        >>> tfm2 = TransferFunctionMatrix([[G2, -G1, G3], [-G2, -G1, -G3]])
        >>> tfm2.num_inputs
        3

        """
        return self._num_inputs

    @property
    def num_outputs(self):
        """
        Returns the number of outputs of the system.

        Examples
        ========

        >>> from sympy.abc import s, p, a, b
        >>> from sympy.physics.control.lti import TransferFunction, Series, TransferFunctionMatrix
        >>> tf1 = TransferFunction(a*p**2 + b*s, s - p, s)
        >>> tf2 = TransferFunction(s**3 - 2, s**4 + 5*s + 6, s)
        >>> tf3 = TransferFunction(a*s - 4, s**4 + 1, s)
        >>> S1, S2 = Series(tf1, -tf2), Series(tf2, tf3, -tf1)
        >>> TFM1 = TransferFunctionMatrix([tf1, tf2, tf3])
        >>> TFM1.num_outputs
        3
        >>> TFM2 = TransferFunctionMatrix(((S1, S2), (-S2, -S1)))
        >>> TFM2.num_outputs
        2

        """
        return self._num_outputs

    @property
    def shape(self):
        """
        Returns the shape of the transfer function matrix, that is, ``(# of outputs, # of inputs)``.

        If explicitly provided as the second argument of ``TransferFunctionMatrix``, then returns the same,
        else, ``TransferFunctionMatrix`` automatically looks up the shape from the list/tuple provided as
        the first argument and returns that.

        Examples
        ========

        >>> from sympy.abc import s, p
        >>> from sympy.physics.control.lti import TransferFunction, TransferFunctionMatrix
        >>> tf1 = TransferFunction(p**2 - 1, s**4 + s**3 - p, p)
        >>> tf2 = TransferFunction(1 - p, p**2 - 3*p + 7, p)
        >>> tf3 = TransferFunction(3, 4, p)
        >>> tfm1 = TransferFunctionMatrix([[tf1, -tf2]], (1, 2), p)
        >>> tfm1.shape
        (1, 2)
        >>> tfm2 = TransferFunctionMatrix(((-tf2, tf3), (tf1, -tf1)))
        >>> tfm2.shape
        (2, 2)

        """
        return self._num_outputs, self._num_inputs

    def __add__(self, other):
        if isinstance(other, (TransferFunctionMatrix, Series)):
            if isinstance(other, Series):
                if other._is_not_matrix:
                    raise ValueError("All the arguments of Series must be either"
                        " TransferFunctionMatrix or Parallel objects.")

            if not self.shape == other.shape:
                raise ShapeError("Shapes of operands are not compatible for addition.")
            if not self.var == other.var:
                raise ValueError("All the TransferFunctionMatrix objects should use the same"
                    " complex variable of the Laplace transform.")
            return Parallel(self, other)

        elif isinstance(other, Parallel):
            if other._is_not_matrix:
                raise ValueError("All the arguments of Parallel must be either TransferFunctionMatrix"
                    " or Series objects.")
            if not self.shape == other.shape:
                raise ShapeError("Shapes of operands are not compatible for addition.")
            if not self.var == other.var:
                raise ValueError("All the TransferFunctionMatrix objects should use the same"
                    " complex variable of the Laplace transform.")
            arg_list = list(other.args)
            return Parallel(self, *arg_list)

        else:
            raise ValueError("TransferFunctionMatrix cannot be added with {}.".
                format(type(other)))

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        return self + (-other)

    def __rsub__(self, other):
        return -self + other

    def __mul__(self, other):
        if isinstance(other, (TransferFunctionMatrix, Parallel)):
            if isinstance(other, Parallel):
                if other._is_not_matrix:
                    raise ValueError("Only transfer function matrices are allowed in the "
                        "parallel configuration.")
            if not self.num_inputs == other.num_outputs:
                raise ValueError("C = A * B: A has {0} input(s), but B has {1} output(s)."
                    .format(self.num_inputs, other.num_outputs))
            if not self.var == other.var:
                raise ValueError("Both TransferFunctionMatrix objects should use the same"
                    " complex variable of the Laplace transform.")
            return Series(self, other)

        elif isinstance(other, Series):
            if other._is_not_matrix:
                raise ValueError("Only transfer function matrices are allowed in the "
                    "series configuration.")
            if not self.num_inputs == other.num_outputs:
                raise ValueError("C = A * B: A has {0} input(s), but B has {1} output(s)."
                    .format(self.num_inputs, other.num_outputs))
            if not self.var == other.var:
                raise ValueError("All the TransferFunctionMatrix objects should use the same"
                    " complex variable of the Laplace transform.")
            arg_list = list(other.args)

            return Series(self, *arg_list)
        else:
            raise ValueError("TransferFunctionMatrix cannot be multiplied with {}."
                .format(type(other)))

    __rmul__ = __mul__

    def doit(self, **kwargs):
        """
        Returns the resultant transfer function matrix obtained after evaluating
        the transfer functions in series or parallel configurations (if any present)
        for all entries in a transfer function matrix.

        Examples
        ========

        >>> from sympy.abc import s, p, a, b
        >>> from sympy.physics.control.lti import TransferFunction, Series, Parallel, TransferFunctionMatrix
        >>> tf1 = TransferFunction(a*p**2 + b*s, s - p, s)
        >>> tf2 = TransferFunction(s**3 - 2, s**4 + 5*s + 6, s)
        >>> tf3 = TransferFunction(a*s - 4, s**4 + 1, s)
        >>> S1, S2 = Series(tf1, -tf2), Series(tf2, tf3, -tf1)
        >>> P1, P2 = Parallel(tf2, -tf3), Parallel(-tf1, tf3, -tf2)
        >>> # doit() converts S1, S2, P1, P2 into their resultant transfer functions inside a transfer function matrix.
        >>> tfm1 = TransferFunctionMatrix([S1, S2, -P1])
        >>> tfm1.doit()
        TransferFunctionMatrix([TransferFunction((2 - s**3)*(a*p**2 + b*s), (-p + s)*(s**4 + 5*s + 6), s), TransferFunction((s**3 - 2)*(-a*p**2 - b*s)*(a*s - 4), (-p + s)*(s**4 + 1)*(s**4 + 5*s + 6), s), TransferFunction(-(s**3 - 2)*(s**4 + 1) - (-a*s + 4)*(s**4 + 5*s + 6), (s**4 + 1)*(s**4 + 5*s + 6), s)])
        >>> tfm2 = TransferFunctionMatrix([[tf1, -tf3, -P2]], (1, 3), s)
        >>> tfm2.doit()
        TransferFunctionMatrix([[TransferFunction(a*p**2 + b*s, -p + s, s), TransferFunction(-a*s + 4, s**4 + 1, s), TransferFunction(-(2 - s**3)*(-p + s)*(s**4 + 1) - ((-p + s)*(a*s - 4) + (s**4 + 1)*(-a*p**2 - b*s))*(s**4 + 5*s + 6), (-p + s)*(s**4 + 1)*(s**4 + 5*s + 6), s)]])
        >>> tfm3 = TransferFunctionMatrix(((tf2, P1, P2), (S1, S2, -tf3)), (2, 3), s)
        >>> tfm3.doit()
        TransferFunctionMatrix([[TransferFunction(s**3 - 2, s**4 + 5*s + 6, s), TransferFunction((s**3 - 2)*(s**4 + 1) + (-a*s + 4)*(s**4 + 5*s + 6), (s**4 + 1)*(s**4 + 5*s + 6), s), TransferFunction((2 - s**3)*(-p + s)*(s**4 + 1) + ((-p + s)*(a*s - 4) + (s**4 + 1)*(-a*p**2 - b*s))*(s**4 + 5*s + 6), (-p + s)*(s**4 + 1)*(s**4 + 5*s + 6), s)], [TransferFunction((2 - s**3)*(a*p**2 + b*s), (-p + s)*(s**4 + 5*s + 6), s), TransferFunction((s**3 - 2)*(-a*p**2 - b*s)*(a*s - 4), (-p + s)*(s**4 + 1)*(s**4 + 5*s + 6), s), TransferFunction(-a*s + 4, s**4 + 1, s)]])

        """
        if self.num_inputs == 1:
            arg_matrix = list(self.args[0])
            for row in range(self.num_outputs):
                arg_matrix[row] = arg_matrix[row].doit()
        else:
            arg_matrix = []
            for row in range(self.num_outputs):
                arg_matrix.append(list(self.args[0][row]))

            for row in range(self.num_outputs):
                for col in range(self.num_inputs):
                    arg_matrix[row][col] = arg_matrix[row][col].doit()

        return TransferFunctionMatrix(arg_matrix)

    def __neg__(self):
        if self.num_inputs == 1:
            neg_args = [-col for col in self.args[0]]
        else:
            neg_args = [[-col for col in row] for row in self.args[0]]
        return TransferFunctionMatrix(neg_args)

    @property
    def is_proper(self):
        """
        Returns True if degree of the numerator polynomial is less than or equal
        to degree of the denominator polynomial for all the SISO transfer functions
        in a transfer function matrix; else False.

        Examples
        ========

        >>> from sympy.abc import s, p, a, b
        >>> from sympy.physics.control.lti import TransferFunction, TransferFunctionMatrix
        >>> tf1 = TransferFunction(b*s**2 + p**2 - a*p + s, b - p**2, s)
        >>> tf2 = TransferFunction(p**2 - 4*p, p**3 + 3*p + 2, p)
        >>> tf3 = TransferFunction(a*p**2 + b*s, s - p, s)
        >>> tf4 = TransferFunction(1, p**2, p)
        >>> TFM1 = TransferFunctionMatrix((-tf1, tf3), (2, 1), s)
        >>> TFM1.is_proper
        False
        >>> TFM2 = TransferFunctionMatrix([[tf2, tf4, -tf2], [-tf4, tf2, tf4]], (2, 3), p)
        >>> TFM2.is_proper
        True

        """
        if self.num_inputs == 1:
            return all(elem.is_proper for elem in self.args[0])
        else:
            return all(self.args[0][row][col].is_proper
                for col in range(self.num_inputs) for row in range(self.num_outputs))

    @property
    def is_strictly_proper(self):
        """
        Returns True if degree of the numerator polynomial is strictly less than
        degree of the denominator polynomial for all the SISO transfer functions
        in a transfer function matrix; else False.

        Examples
        ========

        >>> from sympy.abc import s, p, a, b
        >>> from sympy.physics.control.lti import TransferFunction, TransferFunctionMatrix
        >>> tf1 = TransferFunction(a*p**2 + b*s, s - p, s)
        >>> tf2 = TransferFunction(s**3 - 2, s**4 + 5*s + 6, s)
        >>> tf3 = TransferFunction(a, s**2 + b, s)
        >>> TFM1 = TransferFunctionMatrix([-tf1, tf2, -tf3])
        >>> TFM1.is_strictly_proper
        False
        >>> TFM2 = TransferFunctionMatrix([[tf2, tf3], [-tf3, -tf2]])
        >>> TFM2.is_strictly_proper
        True

        """
        if self.num_inputs == 1:
            return all(elem.is_strictly_proper for elem in self.args[0])
        else:
            return all(self.args[0][row][col].is_strictly_proper
                for col in range(self.num_inputs) for row in range(self.num_outputs))

    @property
    def is_biproper(self):
        """
        Returns True if degree of the numerator polynomial is equal to
        degree of the denominator polynomial for all the SISO transfer
        functions in a transfer function matrix; else False.

        Examples
        ========

        >>> from sympy.abc import s, p, a, b
        >>> from sympy.physics.control.lti import TransferFunction, TransferFunctionMatrix
        >>> tf1 = TransferFunction(a*p**2 + b*s, s - p, s)
        >>> tf2 = TransferFunction(-b*p**4 - a*s**2, a - s**2, s)
        >>> tf3 = TransferFunction(s**2, s + a, s)
        >>> TFM1 = TransferFunctionMatrix([tf1, -tf2])
        >>> TFM1.is_biproper
        True
        >>> TFM2 = TransferFunctionMatrix(((tf1, tf2), (tf3, -tf2)))
        >>> TFM2.is_biproper
        False

        """
        if self.num_inputs == 1:
            return all(elem.is_biproper for elem in self.args[0])
        else:
            return all(self.args[0][row][col].is_biproper
                for col in range(self.num_inputs) for row in range(self.num_outputs))
