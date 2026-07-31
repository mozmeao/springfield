# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pinned test vectors and regression fixtures for the referral crypto.

Three independent bodies of evidence, each frozen so any drift in the FF1 port,
the tweak constant, the alphabet ordering, or the key ordering trips a test: the
NIST conformance vectors, an independent Capital One cross-check, and the
per-version regression anchors. Each set's source and how to regenerate it are
documented directly above its definition below.

The FF1 port itself was cross-checked against str4d's Rust `fpe` (main branch,
commit 913e533c9345d5c8e11aac42318fc5743d6f58e9, `src/ff1.rs`). Radix-36
ciphertexts use the lowercase 0-9a-z alphabet, matching the standard numeral
convention.
"""

# NIST_FF1_VECTORS (9): NIST's published FF1 sample values (radix 10 and 36,
# AES-128/192/256). Copied from `FF1samples.pdf`, not generated, and cross-checked
# against Capital One's `ff1/ff1_test.go` (both agree). These prove our FF1
# primitive is bit-exact with the standard.
#   Standard: https://csrc.nist.gov/pubs/sp/800/38/g/upd1/final (SP 800-38G, FF1 in section 5.1)
#   Samples:  https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Standards-and-Guidelines/documents/examples/FF1samples.pdf
#             (linked from the Standard's Appendix D)
# key (hex), tweak (hex), radix, plaintext, expected ciphertext.
NIST_FF1_VECTORS = [
    dict(
        key="2B7E151628AED2A6ABF7158809CF4F3C",
        tweak="",
        radix=10,
        plaintext="0123456789",
        expected="2433477484",
    ),
    dict(
        key="2B7E151628AED2A6ABF7158809CF4F3C",
        tweak="39383736353433323130",
        radix=10,
        plaintext="0123456789",
        expected="6124200773",
    ),
    dict(
        key="2B7E151628AED2A6ABF7158809CF4F3C",
        tweak="3737373770717273373737",
        radix=36,
        plaintext="0123456789abcdefghi",
        expected="a9tv40mll9kdu509eum",
    ),
    dict(
        key="2B7E151628AED2A6ABF7158809CF4F3CEF4359D8D580AA4F",
        tweak="",
        radix=10,
        plaintext="0123456789",
        expected="2830668132",
    ),
    dict(
        key="2B7E151628AED2A6ABF7158809CF4F3CEF4359D8D580AA4F",
        tweak="39383736353433323130",
        radix=10,
        plaintext="0123456789",
        expected="2496655549",
    ),
    dict(
        key="2B7E151628AED2A6ABF7158809CF4F3CEF4359D8D580AA4F",
        tweak="3737373770717273373737",
        radix=36,
        plaintext="0123456789abcdefghi",
        expected="xbj3kv35jrawxv32ysr",
    ),
    dict(
        key="2B7E151628AED2A6ABF7158809CF4F3CEF4359D8D580AA4F7F036D6F04FC6A94",
        tweak="",
        radix=10,
        plaintext="0123456789",
        expected="6657667009",
    ),
    dict(
        key="2B7E151628AED2A6ABF7158809CF4F3CEF4359D8D580AA4F7F036D6F04FC6A94",
        tweak="39383736353433323130",
        radix=10,
        plaintext="0123456789",
        expected="1001623463",
    ),
    dict(
        key="2B7E151628AED2A6ABF7158809CF4F3CEF4359D8D580AA4F7F036D6F04FC6A94",
        tweak="3737373770717273373737",
        radix=36,
        plaintext="0123456789abcdefghi",
        expected="xs8a0azh2avyalyzuwd",
    ),
]

# RANDOM_FF1_VECTORS (20): generated once by a small Go program using Capital One
# `fpe` v1.2.1 (https://github.com/capitalone/fpe, commit
# 80b2f950e5923895c32d589c2df0390e80fba22f) with `math/rand` seeded 20260722, one
# FF1 encryption per row. Widens coverage beyond NIST to radix 32 (our production
# radix, which NIST never publishes), radix 26, all three key sizes, empty and
# non-empty tweaks, odd lengths (unequal Feistel halves), and one long radix-10
# input whose `d` exceeds 16 to exercise the S-expansion path. Each row's shape is
# encoded in its `label`. The Go generator is not committed (Go in a Python repo).
# Reproduce from the labels and seed if ever needed.
# label, key (hex), tweak (hex), radix, plaintext, expected ciphertext.
RANDOM_FF1_VECTORS = [
    dict(
        label="radix32_key256_tweak0_len10",
        key="c6e5e1a9403578dac126fc0711072ce8a6faa192fdbabe20a9c800116154f307",
        tweak="",
        radix=32,
        plaintext="vtba47o78i",
        expected="264565n9dj",
    ),
    dict(
        label="radix32_key256_tweak0_len10",
        key="7d2d12d9204164ec191b3d05b80889c970048e8afe76ba5b963132cf5c381f95",
        tweak="",
        radix=32,
        plaintext="k56gckqmrq",
        expected="qk62v0kvp4",
    ),
    dict(
        label="radix32_key256_tweak0_len10",
        key="9606bcaa73a6d69049d1f4af559017611a7be26fe953960afb215db3d3e6215c",
        tweak="",
        radix=32,
        plaintext="b59h93evhq",
        expected="sngfq7g8p8",
    ),
    dict(
        label="radix32_key256_tweak8_len10",
        key="7fdbc5e873bbe9e05e690aaf17dc7a2ea208e78fbcf86af3a8aaa05c79018924",
        tweak="781675df0d75aad0",
        radix=32,
        plaintext="g4rbk20e9d",
        expected="ptsbrcqd66",
    ),
    dict(
        label="radix32_key256_tweak11_len11",
        key="fc63a4345ad3dbd8c3f2c0dd7d5a2c56ad92f6701a0c3837cdfee21572ee165e",
        tweak="adcb67c8e0028e60e94386",
        radix=32,
        plaintext="m1j6t5vv1ac",
        expected="or01fg38djq",
    ),
    dict(
        label="radix32_key128_tweak0_len16",
        key="7a18347d97e44cd821aa65bf043b6f8f",
        tweak="",
        radix=32,
        plaintext="0f0ia43b6r183nuq",
        expected="lie2tbleklpr0eg3",
    ),
    dict(
        label="radix32_key192_tweak4_len19",
        key="ff3e30ac9152f16218cad3ac88e3fad75474fd3964c97956",
        tweak="9066d103",
        radix=32,
        plaintext="g02tg4cfo491unp93c6",
        expected="3aj7pmkfpg60bi9189k",
    ),
    dict(
        label="radix32_key256_tweak16_len20",
        key="ed67f5f29e4e4a39bcee8b279bf8ec2db0bef8280067ffbd7e4a4d4a2cbc00e4",
        tweak="85d802c87da0fa6123fff029671201eb",
        radix=32,
        plaintext="jgkgae7bug84p7eks7mt",
        expected="v6rps9sfi7em2pvbp7ih",
    ),
    dict(
        label="radix10_key128_tweak0_len10",
        key="32bf7b9c89e9d7fb429de58dd1190713",
        tweak="",
        radix=10,
        plaintext="6728557913",
        expected="9800307162",
    ),
    dict(
        label="radix10_key192_tweak10_len18",
        key="27191f5a5fd935928174fdd972372e124e6920abc64e45a6",
        tweak="48eceaf909925ec7957d",
        radix=10,
        plaintext="476008372277450941",
        expected="978031373446185340",
    ),
    dict(
        label="radix10_key256_tweak7_len24",
        key="8c94c00f9b944c149e616149af41701f2c4415b67f0b2e97268d687d8bd68b46",
        tweak="b03c4cd468b630",
        radix=10,
        plaintext="929560848494622216756372",
        expected="741646002361240055610477",
    ),
    dict(
        label="radix10_key128_tweak0_len64",
        key="57f00401f1629ee3b5e46cc72c41a790",
        tweak="",
        radix=10,
        plaintext="0470339363236406405213084089584169251964484622605816466513614578",
        expected="9039687220770678519511114064811090070533246181736063306536626825",
    ),
    dict(
        label="radix26_key128_tweak0_len12",
        key="89cc9d1cef9533bff2f7c0756330a3f7",
        tweak="",
        radix=26,
        plaintext="fobgnd1bc1c5",
        expected="e5ggck5el3n0",
    ),
    dict(
        label="radix26_key192_tweak5_len15",
        key="acc4a61d116a8e7a5486f579b11d37410627dbebc7e304da",
        tweak="7fc95f80d0",
        radix=26,
        plaintext="3i34ag029g72044",
        expected="2cld49ehemblbdc",
    ),
    dict(
        label="radix26_key256_tweak0_len20",
        key="b85e642b92255700d584915c4f0ba9da903d122d4a8ffba0aacf0632e3690b11",
        tweak="",
        radix=26,
        plaintext="8p503n66ekhgoh4mjnl5",
        expected="e4o1e80poclp4mpi25km",
    ),
    dict(
        label="radix36_key128_tweak0_len10",
        key="6a722fae4299e3d3e168bc52b31e4f0b",
        tweak="",
        radix=36,
        plaintext="rvvfm8npv9",
        expected="df3glx8zrk",
    ),
    dict(
        label="radix36_key192_tweak11_len19",
        key="70763d28747f8de03464d879cb41f3491f6d3fb7611336bb",
        tweak="77648d86cb983e520aec3f",
        radix=36,
        plaintext="yxl4kvnnzj0i26xt150",
        expected="2qhqb71l2rntgrkoebx",
    ),
    dict(
        label="radix36_key256_tweak3_len15",
        key="ae8ec3e76d39be9b120fd798c8555a41d5a98cb52b201fd54ab0ce014a7a07b2",
        tweak="204bff",
        radix=36,
        plaintext="ddgrnmim0rlsvxp",
        expected="ylcpnnsu4shch2h",
    ),
    dict(
        label="radix32_key192_tweak0_len24",
        key="383eb5ec6ae50168e28fdf7cef55ae3807792f67701faad8",
        tweak="",
        radix=32,
        plaintext="6qg86v56kh59l003dj7ik9ju",
        expected="oo9f1ep6ljov7j8be2kj0cr5",
    ),
    dict(
        label="radix32_key128_tweak9_len12",
        key="f4763b63b588dfd002dc1134726fdee9",
        tweak="b465e118742f71c264",
        radix=32,
        plaintext="8c6tq4lit8cq",
        expected="qs17n0o54ktj",
    ),
]

# REGRESSION_FIXTURES (8): pinned (referral_id, code under key v1, code under key
# v2) drift anchors, generated once from this code under the test keyring in
# `springfield/settings/test.py` and frozen. Regenerate with:
#   DJANGO_SETTINGS_MODULE=springfield.settings.test python manage.py regenerate_referral_fixtures
REGRESSION_FIXTURES = [
    ("0000000000000000", "1G6GAF6N3QPQE6MBB", "23GFM47TS4XPT5HDB"),
    ("ZZZZZZZZZZZZZZZZ", "1V93GBJA7C2JKPW84", "27G0BXE1F4B57KQPW"),
    ("FFFFFFFFFFFFFFFF", "1S7G4S847A3ENYMA9", "2NPEVBH90SPMNA94P"),
    ("0123456789ABCDEF", "1SPQM5GXM221BM4SG", "2YM2T9QEJKG0JECYN"),
    ("ZYXWVTSRQPNMKJHG", "14KSRSVKAFYH63NCV", "2BKK1X7066XH813X4"),
    ("A7B9K2M4PXQRSTVW", "1HZ8PEVNKRP63JS5Y", "2XA3RDX1M136XAAPE"),
    ("TEST000000000000", "1GY3KFZV5ZG5ZX2QA", "2ZKH32C154BKGN5YH"),
    ("TESTZZZZZZZZZZZZ", "1DW3AQ9T3W5JM0QG2", "2AKKJE51SHACHVW2G"),
]
