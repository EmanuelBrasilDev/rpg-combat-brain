from app.skills.energy_optimizer import EnergyOptimizer
from app.skills.dice_probability import expected_dice, win_probability
from app.skills.action_validator import ActionValidator
from app.skills.combo_forge import ComboForge

def test_energy_discounts_round_up_each_step():
    assert EnergyOptimizer.successive_discounts(100, [0.15, 0.20, 0.30]) == 48

def test_fangs_confirmed_cost_not_guessed():
    cost = EnergyOptimizer().cost("fangs")
    assert cost.value == 25
    assert cost.status == "confirmed"

def test_scaling_dice():
    assert expected_dice("8d5") == 24
    assert expected_dice("5d2") == 7.5
    assert win_probability(0, 0) == 190 / 400

def test_validator_respects_limits():
    sheet = {
        "id":"akira", "ea":100, "main_actions":1,
        "reaction_available":True, "fangs_used":6,
        "maw_used":0, "amaterasu_used":0
    }
    fangs = {"id":"fangs","main":1,"reaction":0,"offensive":1}
    assert not ActionValidator().check(sheet, [fangs])[0]

def test_no_sequencing_with_no_actions():
    sheet = {
        "id":"akira","ea":200,"hp":600,"max_hp":None,
        "main_actions":0,"reaction_available":False,
        "fangs_used":0,"maw_used":0,"amaterasu_used":0
    }
    assert ComboForge().sequences(sheet) == []
