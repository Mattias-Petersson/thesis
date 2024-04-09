from BDLOP16.CommitmentScheme import CommitmentScheme
from Models.Participant import Participant
from SecretSharing.SecretShare2 import SecretShare
from type.classes import Commit, CommitOpen, Pk, SecretSharePoly, Sk
import itertools


class BGVParticipant(Participant):
    def __init__(
        self,
        comm_scheme: CommitmentScheme,
        secret_share: SecretShare,
        p: int,
        x: int,
    ):
        super().__init__(comm_scheme, secret_share, p, x)
        self.a = self.polynomial.uniform_element()
        self.a_hash = self.hash(self.a)

    def make_b(self):
        self.sum_a = self.a + sum([i.data for i in self.others["a"]])
        self.s, self.e = self.gaussian(1), self.gaussian(1)

        self.com_s = self.__commit(self.s)
        self.c_s = self.comm_scheme.commit(self.com_s)

        self.com_e = self.__commit(self.e)
        self.c_e = self.comm_scheme.commit(self.com_e)

        self.b = self.sum_a * self.s + self.p * self.e
        self.b_hash = self.hash(self.b)

    def __commit(self, commitment):
        """
        Returns a commit object of the commitment and a randomness r. Can
        be used to commit with a commitment scheme and return c.
        """
        return Commit(commitment, self.comm_scheme.r_commit())

    def make_secrets(self):
        def make_b(s, e):
            if s.x != e.x:
                raise ValueError()
            return SecretSharePoly(s.x, self.sum_a * s.p + self.p * e.p)

        add_val = lambda name, val: vals.get(name, []) + [val]
        to_tuple = lambda attr: tuple(vals[attr])

        self.s_bar = self.secret_share.share_poly(self.s)
        self.e_bar = self.secret_share.share_poly(self.e)
        vals = dict()
        for s, e in zip(self.s_bar, self.e_bar):
            vals["b_bar"] = add_val("b_bar", make_b(s, e))

            com_s = self.__commit(s.p)
            vals["coms_s_bar"] = add_val("coms_s_bar", com_s)
            vals["c_s_bar"] = add_val("c_s_bar", self.comm_scheme.commit(com_s))
            com_e = self.__commit(e.p)
            vals["coms_e_bar"] = add_val("coms_e_bar", com_e)
            vals["c_e_bar"] = add_val("c_e_bar", self.comm_scheme.commit(com_e))

        self.b_bar = to_tuple("b_bar")
        self.coms_s_bar = to_tuple("coms_s_bar")
        self.c_s_bar = to_tuple("c_s_bar")
        self.coms_e_bar = to_tuple("coms_e_bar")
        self.c_e_bar = to_tuple("c_e_bar")

    def reconstruct(self, data, t):
        """
        Attempts to reconstruct this participant's own b, using the shares
        provided to them from the BGV class in the data param. All possible
        combinations are tried, as all should return true. If any combination
        returns false we print out the user for which the process failed, and
        which key shares were responsible.
        """
        combs = list(itertools.combinations(data, t))
        for c in combs:
            pol = self.secret_share.reconstruct_poly([i.data for i in c])
            if pol != self.b:
                raise ValueError(
                    f"Aborting. Reconstructing b failed for user {self.name}"
                    + f", reconstructing polynomials for users: {[i.name for i in c]}",
                )

    def check_open(self):
        for c, com in zip(self.others["c_s_bar"], self.others["coms_s_bar"]):
            if c.name != com.name:
                raise ValueError(
                    "Aborting. Name mismatch for participants."
                    + f"{self.name}: {c.name, com.name}"
                )
            if not self.comm_scheme.open(CommitOpen(c.data, com.data)):
                raise ValueError(
                    f"Aborting. User {self.name} got an invalid opening for "
                    + f"user {c.name}"
                )

    def generate_final(self):
        self.sum_b = self.b + sum([i.data for i in self.others["b"]])
        new_com = 0
        new_r = 0
        for com in self.others["coms_s_bar"]:
            new_com += com.data.m
            new_r += com.data.r
        self.c_s_k = sum([i.data for i in self.others["c_s_bar"]])
        self.pk = Pk(self.sum_a, self.sum_b, self.c_s_k)
        self.sk = Sk(self.x, Commit(new_com, new_r))
        return self.pk, self.sk
