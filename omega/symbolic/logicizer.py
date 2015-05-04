"""Conversion of semi-symbolic to symbolic automata.

Re-implementation of `tulip.synth`.
"""
from __future__ import absolute_import
import logging
import warnings
from omega.symbolic.symbolic import Automaton
from omega.logic.syntax import disj, conj, conj_neg


logger = logging.getLogger(__name__)


def graph_to_logic(g, nodevar, ignore_initial, receptive=False):
    """Flatten labeled graph to temporal logic formulae.

    @param g: `TransitionSystem`

    The attribute `g.owner` defines who selects the next node.
    The attribute `g.env_vars` determines who controls each variable.

    @param g: `TransitionSystem`
    @param nodevar: variable that stores current node
    @type nodevar: `str`
    @param ignore_initial: if `False`, then add initial condition
        using `g.initia_nodes`.
    @type ignore_initial: `bool`
    @param receptive: if `True`, then add assumptions to
        ensure receptiveness at each node.

    @return: temporal formulae representing `g`.
    @rtype: `Automaton`
    """
    assert g.is_consistent()
    assert len(g) > 0
    t = _vars_to_symbol_table(g, nodevar)
    # add primed copies -- same `dict` value
    dvars = dict(t)
    p, _ = _prime_dict(dvars)
    dvars.update(p)
    # convert to logic
    init = _init_from_ts(g.initial_nodes, nodevar, dvars, ignore_initial)
    tmp_init, nodepred = _node_var_trans(g, nodevar, dvars)
    if g.owner == 'sys':
        sys_init = init + tmp_init
        sys_tran = _sys_trans(g, nodevar, dvars)
        sys_tran += nodepred
        env_init = list()
        if receptive:
            env_tran = _env_trans_from_sys_ts(g, nodevar, dvars)
        else:
            env_tran = list()
    elif g.owner == 'env':
        sys_init = list()
        sys_tran = list()
        env_init = init + tmp_init
        env_tran = nodepred + _env_trans(g, nodevar, dvars)
    a = Automaton()
    a.vars = t
    a.init['env'] += env_init
    a.init['sys'] += sys_init
    a.action['env'] += env_tran
    a.action['sys'] += sys_tran
    return a


def _vars_to_symbol_table(g, nodevar):
    """Return `dict` of integer and Boolean variables.

    Conforms to `openpromela.bitvector` input:
      - type: 'bool' | 'saturating'
      - dom: (min, max)
      - owner: 'env' | 'sys'
    """
    t = dict()
    for var, dom in g.vars.iteritems():
        # type and domain
        if dom == 'bool':
            dtype = 'bool'
            dom = None
        elif dom == 'boolean':
            raise Exception('replace "boolean" with "bool"')
        else:
            assert isinstance(dom, tuple), (var, dom)
            dtype = 'saturating'
        # owner
        if var in g.env_vars:
            owner = 'env'
        else:
            owner = 'sys'
        t[var] = dict(type=dtype, dom=dom, owner=owner)
    assert all(isinstance(u, int) for u in g)
    dtype = 'saturating'
    dom = (min(g), max(g))
    t[nodevar] = dict(type=dtype, dom=dom, owner=g.owner)
    return t


def _node_var_trans(g, nodevar, dvars):
    """Return data flow constraint on variables labeling nodes."""
    init = list()
    trans = list()
    # no AP labels ?
    if not dvars:
        return (init, trans)
    for u, d in g.nodes_iter(data=True):
        pre = _assign(nodevar, u, dvars)
        r = _to_action(d, dvars)
        if not r:
            continue
        # initial node vars
        init.append('!({pre}) || ({r})'.format(pre=pre, r=r))
        # transitions of node vars
        trans.append('(X (({pre}) -> ({r})))'.format(pre=pre, r=r))
    return (init, trans)


def _init_from_ts(initial_nodes, nodevar, dvars, ignore_initial=False):
    """Return initial condition."""
    if ignore_initial:
        return list()
    if not initial_nodes:
        raise Exception('Transition system without initial states.')
    return [disj(_assign(nodevar, u, dvars) for u in initial_nodes)]


def _sys_trans(g, nodevar, dvars):
    """Convert transition relation to safety formula."""
    logger.debug('modeling sys transitions in logic')
    sys_trans = list()
    for u in g:
        pre = _assign(nodevar, u, dvars)
        # no successors ?
        if not g.succ.get(u):
            logger.debug('node: {u} is deadend !'.format(u=u))
            sys_trans.append('({pre}) -> (X False)'.format(pre=pre))
            continue
        post = list()
        for u, v, d in g.edges_iter(u, data=True):
            t = dict(d)
            t[_prime(nodevar)] = v
            r = _to_action(t, dvars)
            post.append(r)
        c = '({pre}) -> ({post})'.format(pre=pre, post=disj(post))
        sys_trans.append(c)
    return sys_trans


def _env_trans_from_sys_ts(g, nodevar, dvars):
    """Return safety assumption to prevent env from blocking sys."""
    denv = {k: v for k, v in dvars.iteritems() if k in g.env_vars}
    env_trans = list()
    for u in g:
        # no successor states ?
        if not g.succ.get(u):
            continue
        # collect possible next env actions
        c = set()
        for u, w, d in g.edges_iter(u, data=True):
            t = _to_action(d, denv)
            if not t:
                continue
            c.add(t)
        # no next env actions ?
        if not c:
            continue
        post = disj(c)
        pre = _assign(nodevar, u, dvars)
        env_trans.append('(({pre}) -> ({post}))'.format(pre=pre, post=post))
    return env_trans


def _env_trans(g, nodevar, dvars):
    """Convert environment transitions to safety formula.

    @type g: `networkx.MultiDigraph`
    @param nodevar: name of variable representing current node
    @type nodevar: `str`
    @type dvars: `dict`
    """
    env_trans = list()
    for u in g:
        pre = _assign(nodevar, u, dvars)
        # no successors ?
        if not g.succ.get(u):
            env_trans.append('{pre} -> X(False)'.format(pre=pre))
            warnings.warn(
                'Environment dead-end found.\n'
                'If sys can force env to dead-end,\n'
                'then GR(1) assumption becomes False,\n'
                'and spec trivially True.')
            continue
        post = list()
        sys = list()
        for u, v, d in g.out_edges_iter(u, data=True):
            # action
            t = dict(d)
            t[_prime(nodevar)] = v
            r = _to_action(t, dvars)
            post.append(r)
            # what sys vars ?
            t = {k: v for k, v in d.iteritems()
                 if k not in g.env_vars}
            r = _to_action(t, dvars)
            sys.append(r)
        # avoid sys winning env by blocking all edges
        post.append(conj_neg(sys))
        env_trans.append('({pre}) -> ({post})'.format(
            pre=pre, post=disj(post)))
    return env_trans


def _to_action(d, dvars):
    """Return `str` conjoining assignments and `"formula"` in `d`.

    @param d: (partial) mapping from variables in `dvars`
        to values in their range, defined by `dvars`
    @type d: `dict`
    @type dvars: `dict`
    """
    c = list()
    if 'formula' in d:
        c.append(d['formula'])
    for k, v in d.iteritems():
        if k not in dvars:
            continue
        s = _assign(k, v, dvars)
        c.append(s)
    return conj(c)


def _assign(k, v, dvars):
    """Return `str` of equality of variable `k` to value `v`.

    @type k: `str`
    @type v: `str` or `int`
    @type dvars: `dict`
    """
    dom = dvars[k]['dom']
    if isinstance(dom, tuple):
        s = '{k} = {v}'.format(k=k, v=v)
    elif isinstance(dom, (set, list)):
        s = '{k} = "{v}"'.format(k=k, v=v)
    elif dom in {'bool', 'boolean'}:
        s = '{k} <-> {v}'.format(k=k, v=v)
    else:
        raise Exception('domain is: {dom}'.format(dom=dom))
    return _pstr(s)


def _prime_dict(d):
    """Return `dict` with primed keys and `dict` mapping to them."""
    p = dict((_prime(k), d[k]) for k in d)
    d2p = {k: _prime(k) for k in d}
    return p, d2p


def _prime(s):
    return s + "'"


def _pstr(x):
    return '({x})'.format(x=x)