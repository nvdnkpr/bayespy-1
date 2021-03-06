######################################################################
# Copyright (C) 2011,2012,2014 Jaakko Luttinen
#
# This file is licensed under Version 3.0 of the GNU General Public
# License. See LICENSE for a text of the license.
######################################################################

######################################################################
# This file is part of BayesPy.
#
# BayesPy is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# BayesPy is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BayesPy.  If not, see <http://www.gnu.org/licenses/>.
######################################################################

"""
Module for the Dirichlet distribution node.
"""

import numpy as np
import scipy.special as special

from bayespy.utils import random

from .expfamily import ExponentialFamily, ExponentialFamilyDistribution
from .constant import Constant
from .node import Node, Moments, ensureparents


class DirichletPriorMoments(Moments):
    """
    Class for the moments of Dirichlet conjugate-prior variables.
    """

    
    def compute_fixed_moments(self, alpha):
        """
        Compute the moments for a fixed value
        """

        if np.ndim(alpha) < 1:
            raise ValueError("The prior sample sizes must be a vector")
        if np.any(alpha < 0):
            raise ValueError("The prior sample sizes must be positive")
        
        gammaln_sum = special.gammaln(np.sum(alpha, axis=-1))
        sum_gammaln = np.sum(special.gammaln(alpha), axis=-1)
        z = gammaln_sum - sum_gammaln
        return [alpha, z]

    
    def compute_dims_from_values(self, alpha):
        """
        Return the shape of the moments for a fixed value.
        """
        if np.ndim(alpha) < 1:
            raise ValueError("The array must be at least 1-dimensional array.")
        d = np.shape(alpha)[-1]
        return [(d,), ()]

    
class DirichletMoments(Moments):
    """
    Class for the moments of Dirichlet variables.
    """

    
    def compute_fixed_moments(self, p):
        """
        Compute the moments for a fixed value
        """
        # Check that probabilities are non-negative
        p = np.asanyarray(p)
        if np.ndim(p) < 1:
            raise ValueError("Probabilities must be given as a vector")
        if np.any(p < 0) or np.any(p > 1):
            raise ValueError("Probabilities must be in range [0,1]")
        if not np.allclose(np.sum(p, axis=-1), 1.0):
            raise ValueError("Probabilities must sum to one")
        # Normalize probabilities
        p = p / np.sum(p, axis=-1, keepdims=True)
        # Message is log-probabilities
        logp = np.log(p)
        u = [logp]
        return u

    
    def compute_dims_from_values(self, x):
        """
        Return the shape of the moments for a fixed value.
        """
        if np.ndim(x) < 1:
            raise ValueError("Probabilities must be given as a vector")
        D = np.shape(x)[-1]
        return ( (D,), )


class DirichletDistribution(ExponentialFamilyDistribution):
    """
    Class for the VMP formulas of Dirichlet variables.
    """

    
    def compute_message_to_parent(self, parent, index, u_self, u_alpha):
        """
        Compute the message to a parent node.
        """
        raise NotImplementedError()

    
    def compute_phi_from_parents(self, u_alpha, mask=True):
        """
        Compute the natural parameter vector given parent moments.
        """
        return [u_alpha[0]]

    
    def compute_moments_and_cgf(self, phi, mask=True):
        """
        Compute the moments and :math:`g(\phi)`.
        """
        sum_gammaln = np.sum(special.gammaln(phi[0]), axis=-1)
        gammaln_sum = special.gammaln(np.sum(phi[0], axis=-1))
        psi_sum = special.psi(np.sum(phi[0], axis=-1, keepdims=True))
        
        # Moments <log x>
        u0 = special.psi(phi[0]) - psi_sum
        u = [u0]
        # G
        g = gammaln_sum - sum_gammaln

        return (u, g)

    
    def compute_cgf_from_parents(self, u_alpha):
        """
        Compute :math:`\mathrm{E}_{q(p)}[g(p)]`
        """
        return u_alpha[1]

    
    def compute_fixed_moments_and_f(self, x, mask=True):
        """
        Compute the moments and :math:`f(x)` for a fixed value.
        """
        raise NotImplementedError()

    
class Dirichlet(ExponentialFamily):
    """
    Node for Dirichlet random variables.
    """

    _moments = DirichletMoments()
    _parent_moments = (DirichletPriorMoments(),)
    _distribution = DirichletDistribution()
    

    @classmethod
    @ensureparents
    def _constructor(cls, alpha, **kwargs):
        """
        Constructs distribution and moments objects.
        """
        # Number of categories
        D = alpha.dims[0][0]

        parents = [alpha]
        
        return ( parents,
                 kwargs,
                 ( (D,), ),
                 cls._total_plates(kwargs.get('plates'), alpha.plates),
                 cls._distribution, 
                 cls._moments, 
                 cls._parent_moments)

                 
    def random(self):
        """
        Draw a random sample from the distribution.
        """
        return random.dirichlet(self.phi[0], size=self.plates)
        

    def show(self):
        """
        Print the distribution using standard parameterization.
        """
        alpha = self.phi[0]
        print("%s ~ Dirichlet(alpha)" % self.name)
        print("  alpha = ")
        print(alpha)
