"""Utilities for manipulating primes (x') and support."""
# Copyright 2015-2017 by California Institute of Technology
# All rights reserved. Licensed under BSD-3.
#
from omega.logic import syntax as stx
from omega.symbolic import bdd as sym_bdd


# functions in transition to here
is_state_predicate = sym_bdd.is_state_predicate
is_proper_action = sym_bdd.is_proper_action
prime = sym_bdd.prime
unprime = sym_bdd.unprime


def is_primed_state_predicate(u, fol):
    """Return `True` if `u` does not depend on unprimed variables.

    Only constant parameters (rigid variables) can appear
    unprimed in `u`. Any flexible variables in `u` should
    be primed.

    An identifier that is declared only unprimed is assumed
    to be a rigid variable. If a primed sibling is declared,
    then the identifier is assumed to be a flexible variable.
    """
    unprimed_vars = (is_variable(k, fol) for k in unprimed_support(u, fol))
    return not any(unprimed_vars)


def is_action_of_player(action, player, aut):
    """Return `True` if `action` constrains only `player`.

    The `player` is represented by the variables in
    `aut.varlist[player]`.
    """
    primed = primed_support(action, aut)
    vrs = aut.vars_of_players([player])
    vrs_p = stx.prime_vars(vrs)
    r = primed.issubset(vrs_p)
    return r


def rigid_support(u, fol):
    """Return constants that `u` depends on."""
    unprimed = unprimed_support(u, fol)
    return {k for k in unprimed if is_constant(k, fol)}


def flexible_support(u, fol):
    """Return unprimed variables that `u` depends on."""
    unprimed = unprimed_support(u, fol)
    return {k for k in unprimed if is_variable(k, fol)}


def split_support(u, fol):
    """Return unprimed, primed identifiers `u` depends on.

    This function exists as an optimization over calling
    separately `unprimed_support` and `primed_support`.
    This function calls `fol.support` once, as opposed to
    twice when performing two separate calls.

    If optimization is irrelevant, then call those other
    functions, because readability counts [PEP 20].
    """
    support = fol.support(u)
    primed = {k for k in support if stx.isprimed(k)}
    unprimed = support - primed
    return unprimed, primed


def unprimed_support(u, fol):
    """Return unprimed identifiers that `u` depends on."""
    return {k for k in fol.support(u) if not stx.isprimed(k)}


def primed_support(u, fol):
    """Return primed identifiers that `u` depends on.

    These identifiers include both variables and constants.
    """
    return {k for k in fol.support(u) if stx.isprimed(k)}


def is_constant(name, fol):
    """Return `True` if `name` is declared as constant."""
    return not is_variable(name, fol)


def is_variable(name, fol):
    """Return `True` if `name` is declared as variable.

    The identifier `name` should be unprimed.
    """
    return stx.prime(name) in fol.vars


def pairwise_disjoint(c):
    """Return whether elements in `c` are pairwise disjoint."""
    union = set().union(*c)
    n = sum(len(u) for u in c)
    return n == len(union)


def pick(c):
    """Return an element from container `c`.

    If `c` is empty, return `None`.
    """
    return next(iter(c), None)