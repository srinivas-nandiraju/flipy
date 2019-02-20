import pytest
from flippy.objective import Objective, Minimize, Maximize


@pytest.fixture
def objective(name='', expression=None, constant=0):

    return Objective(name, expression, constant)


class TestLpExpression(object):
    def test_init(self):
        obj = Objective(name='', expression=None, constant=0)
        assert obj
        assert obj.sense == Minimize
        obj.sense = Maximize
        assert obj.sense == Maximize

    def test_bad_sense(self):
        with pytest.raises(ValueError) as e:
            Objective(name='', expression=None, constant=0, sense='')
        assert "Sense must be one of %s, %s not " % (Minimize, Maximize) in str(e.value)

        obj = Objective(name='', expression=None, constant=0)
        with pytest.raises(ValueError) as e:
            obj.sense = 'maximize'
        assert "Sense must be one of %s, %s not " % (Minimize, Maximize) in str(e.value)