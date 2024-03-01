import pytest
from BDLOPZK import BDLOPZK
from type.classes import Commit, ProofOfOpenLinear


@pytest.fixture
def r_commit(comm_scheme):
    return comm_scheme.r_commit()


@pytest.fixture
def r_open(comm_scheme):
    return comm_scheme.r_open()


@pytest.fixture
def ZK(comm_scheme):
    return BDLOPZK(comm_scheme)


def test_proof_of_opening_r_commit(ZK, r_commit):
    """
    A proof of opening should not throw an exception
    with an r from a commitment scheme's commit.
    """
    try:
        ZK.proof_of_opening(r_commit)
    except Exception as e:
        pytest.fail("Unhandled exception: {}".format(e))


def test_proof_of_opening_r_open(ZK, r_open):
    """
    A proof of opening should not throw an exception
    with an r from a commitment scheme's open.
    """
    try:
        ZK.proof_of_opening(r_open)
    except Exception as e:
        pytest.fail("Unhandled exception: {}".format(e))


def test_proof_of_open_valid(ZK, commit_object, comm_scheme):
    """
    Verify that a proof of opening returns True for a valid r.
    """
    c = comm_scheme.commit(commit_object)
    proof = ZK.proof_of_opening(commit_object.r)
    assert ZK.verify_proof_of_opening(c[0][0], *proof)


def test_proof_of_open_invalid(ZK, comm_scheme, commit_object, r_open):
    """
    Verify that a proof of opening returns False when sending in a
    different r.
    """
    c = comm_scheme.commit(commit_object)
    proof = ZK.proof_of_opening(r_open)
    assert not ZK.verify_proof_of_opening(c[0][0], *proof)


def test_proof_of_linear(ZK, comm_scheme, poly, cypari):
    num: range = range(2)
    m = poly.uniform_array(comm_scheme.l)
    g = tuple(comm_scheme.get_challenge() for _ in num)
    r = tuple(comm_scheme.r_commit() for _ in num)
    c = tuple(
        comm_scheme.commit(Commit(cypari(g * m), r)) for g, r in zip(g, r)
    )
    *proofs, u, d = ZK.proof_of_linear_relation(*r, *g)
    proofs = tuple[ProofOfOpenLinear, ProofOfOpenLinear](
        ProofOfOpenLinear(c, g, proof=proof)
        for c, g, proof in zip(c, g, proofs)
    )
    assert ZK.verify_proof_of_linear_relation(*proofs, u, d)
