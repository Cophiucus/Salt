"""Test cases for the ``ldap`` state module

This code is gross.  I started out trying to remove some of the
duplicate code in the test cases, and before I knew it the test code
was an ugly second implementation.

I'm leaving it for now, but this should really be gutted and replaced
with something sensible.
"""
import copy

import salt.states.ldap
from salt.utils.oset import OrderedSet
from salt.utils.stringutils import to_bytes
from tests.support.mixins import LoaderModuleMockMixin
from tests.support.unit import TestCase

# emulates the LDAP database.  each key is the DN of an entry and it
# maps to a dict which maps attribute names to sets of values.
db = {}


def _init_db(newdb=None):
    if newdb is None:
        newdb = {}
    global db
    db = newdb


def _complex_db():
    return {
        "dnfoo": {
            "attrfoo1": OrderedSet(
                (
                    b"valfoo1.1",
                    b"valfoo1.2",
                )
            ),
            "attrfoo2": OrderedSet((b"valfoo2.1",)),
        },
        "dnbar": {
            "attrbar1": OrderedSet(
                (
                    b"valbar1.1",
                    b"valbar1.2",
                )
            ),
            "attrbar2": OrderedSet((b"valbar2.1",)),
        },
    }


class _dummy_ctx:
    def __init__(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass


def _dummy_connect(connect_spec):
    return _dummy_ctx()


def _dummy_search(connect_spec, base, scope):
    if base not in db:
        return {}
    return {
        base: {attr: list(db[base][attr]) for attr in db[base] if len(db[base][attr])}
    }


def _dummy_add(connect_spec, dn, attributes):
    assert dn not in db
    assert attributes
    db[dn] = {}
    for attr, vals in attributes.items():
        assert vals
        db[dn][attr] = OrderedSet(vals)
    return True


def _dummy_delete(connect_spec, dn):
    assert dn in db
    del db[dn]
    return True


def _dummy_change(connect_spec, dn, before, after):
    assert before != after
    assert before
    assert after
    assert dn in db
    e = db[dn]
    assert e == before
    all_attrs = OrderedSet()
    all_attrs.update(before)
    all_attrs.update(after)
    directives = []
    for attr in all_attrs:
        if attr not in before:
            assert attr in after
            assert after[attr]
            directives.append(("add", attr, after[attr]))
        elif attr not in after:
            assert attr in before
            assert before[attr]
            directives.append(("delete", attr, ()))
        else:
            assert before[attr]
            assert after[attr]
            to_del = before[attr] - after[attr]
            if to_del:
                directives.append(("delete", attr, to_del))
            to_add = after[attr] - before[attr]
            if to_add:
                directives.append(("add", attr, to_add))
    return _dummy_modify(connect_spec, dn, directives)


def _dummy_modify(connect_spec, dn, directives):
    assert dn in db
    e = db[dn]
    for op, attr, vals in directives:
        if op == "add":
            assert vals
            existing_vals = e.setdefault(attr, OrderedSet())
            for val in vals:
                assert val not in existing_vals
                existing_vals.add(val)
        elif op == "delete":
            assert attr in e
            existing_vals = e[attr]
            assert existing_vals
            if not vals:
                del e[attr]
                continue
            for val in vals:
                assert val in existing_vals
                existing_vals.remove(val)
            if not existing_vals:
                del e[attr]
        elif op == "replace":
            e.pop(attr, None)
            e[attr] = OrderedSet(vals)
        else:
            raise ValueError()
    return True


def _dump_db(d=None):
    if d is None:
        d = db
    return {dn: {attr: list(d[dn][attr]) for attr in d[dn]} for dn in d}


class LDAPTestCase(TestCase, LoaderModuleMockMixin):
    def setup_loader_modules(self):
        salt_dunder = {}
        for fname in ("connect", "search", "add", "delete", "change", "modify"):
            salt_dunder["ldap3.{}".format(fname)] = globals()["_dummy_" + fname]
        return {
            salt.states.ldap: {"__opts__": {"test": False}, "__salt__": salt_dunder}
        }

    def _test_helper(self, init_db, expected_ret, replace, delete_others=False):
        _init_db(copy.deepcopy(init_db))
        old = _dump_db()
        new = _dump_db()
        expected_db = copy.deepcopy(init_db)
        for dn, attrs in replace.items():
            for attr, vals in attrs.items():
                vals = [to_bytes(val) for val in vals]
                if vals:
                    new.setdefault(dn, {})[attr] = list(OrderedSet(vals))
                    expected_db.setdefault(dn, {})[attr] = OrderedSet(vals)
                elif dn in expected_db:
                    new[dn].pop(attr, None)
                    expected_db[dn].pop(attr, None)
            if not expected_db.get(dn, {}):
                new.pop(dn, None)
                expected_db.pop(dn, None)
        if delete_others:
            dn_to_delete = OrderedSet()
            for dn, attrs in expected_db.items():
                if dn in replace:
                    to_delete = OrderedSet()
                    for attr, vals in attrs.items():
                        if attr not in replace[dn]:
                            to_delete.add(attr)
                    for attr in to_delete:
                        del attrs[attr]
                        del new[dn][attr]
                    if not attrs:
                        dn_to_delete.add(dn)
            for dn in dn_to_delete:
                del new[dn]
                del expected_db[dn]
        name = "ldapi:///"
        expected_ret["name"] = name
        expected_ret.setdefault("result", True)
        expected_ret.setdefault("comment", "Successfully updated LDAP entries")
        expected_ret.setdefault(
            "changes",
            {
                dn: {
                    "old": {
                        attr: vals
                        for attr, vals in old[dn].items()
                        if vals != new.get(dn, {}).get(attr, ())
                    }
                    if dn in old
                    else None,
                    "new": {
                        attr: vals
                        for attr, vals in new[dn].items()
                        if vals != old.get(dn, {}).get(attr, ())
                    }
                    if dn in new
                    else None,
                }
                for dn in replace
                if old.get(dn, {}) != new.get(dn, {})
            },
        )
        entries = [
            {dn: [{"replace": attrs}, {"delete_others": delete_others}]}
            for dn, attrs in replace.items()
        ]
        actual = salt.states.ldap.managed(name, entries)
        self.assertDictEqual(expected_ret, actual)
        self.assertDictEqual(expected_db, db)

    def _test_helper_success(self, init_db, replace, delete_others=False):
        self._test_helper(init_db, {}, replace, delete_others)

    def _test_helper_nochange(self, init_db, replace, delete_others=False):
        expected = {
            "changes": {},
            "comment": "LDAP entries already set",
        }
        self._test_helper(init_db, expected, replace, delete_others)

    def test_managed_empty(self):
        _init_db()
        name = "ldapi:///"
        expected = {
            "name": name,
            "changes": {},
            "result": True,
            "comment": "LDAP entries already set",
        }
        actual = salt.states.ldap.managed(name, {})
        self.assertDictEqual(expected, actual)

    def test_managed_add_entry(self):
        self._test_helper_success({}, {"dummydn": {"foo": ["bar", "baz"]}})

    def test_managed_add_attr(self):
        self._test_helper_success(_complex_db(), {"dnfoo": {"attrfoo3": ["valfoo3.1"]}})

    def test_managed_simplereplace(self):
        self._test_helper_success(_complex_db(), {"dnfoo": {"attrfoo1": ["valfoo1.3"]}})

    def test_managed_deleteattr(self):
        self._test_helper_success(_complex_db(), {"dnfoo": {"attrfoo1": []}})

    def test_managed_deletenonexistattr(self):
        self._test_helper_nochange(_complex_db(), {"dnfoo": {"dummyattr": []}})

    def test_managed_deleteentry(self):
        self._test_helper_success(_complex_db(), {"dnfoo": {}}, True)

    def test_managed_deletenonexistentry(self):
        self._test_helper_nochange(_complex_db(), {"dummydn": {}}, True)

    def test_managed_deletenonexistattrinnonexistentry(self):
        self._test_helper_nochange(_complex_db(), {"dummydn": {"dummyattr": []}})

    def test_managed_add_attr_delete_others(self):
        self._test_helper_success(
            _complex_db(), {"dnfoo": {"dummyattr": ["dummyval"]}}, True
        )

    def test_managed_no_net_change(self):
        self._test_helper_nochange(
            _complex_db(), {"dnfoo": {"attrfoo1": ["valfoo1.1", "valfoo1.2"]}}
        )

    def test_managed_repeated_values(self):
        self._test_helper_success(
            {}, {"dummydn": {"dummyattr": ["dummyval", "dummyval"]}}
        )
