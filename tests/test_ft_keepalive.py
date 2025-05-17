import gc
import sys

from swtest import ft


def test_ft_autokeepalive():
    # semiwrap should keepalive the reference without being told in the YML

    p = ft.PatientRef()

    n = ft.Nurse(p)
    assert p is n.m_p

    del p
    gc.collect()

    assert not n.patientDead()
